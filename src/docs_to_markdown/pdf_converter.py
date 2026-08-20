import base64
import hashlib
import re
from collections import Counter
from io import BytesIO
from statistics import median
from urllib.parse import quote

from markitdown import MarkItDown, StreamInfo
import pdfplumber
import pypdfium2 as pdfium
from PIL import Image

from .ocr_adapter import OCRAdapter, detect_ocr_adapter


PDF_MIME_TYPE = "application/pdf"
PDF_TO_CSS_PIXELS = 96 / 72
MIN_OCR_IMAGE_DIMENSION = 40
BULLET_PATTERN = re.compile(r"^(?:[•◦▪●○■□\uf0b7]|[+*-])\s+(.*)")
ORDERED_PATTERN = re.compile(r"^(\d+)[.)]\s+(.*)")


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("*", "\\*").replace("_", "\\_")


def _wrap_link(text: str, uri: str | None) -> str:
    if not uri:
        return text
    if uri.startswith("mailto:") and text == f"<{uri.removeprefix('mailto:')}>":
        text = uri.removeprefix("mailto:")
    return f"[{text}]({quote(uri, safe=':/?&=#%+@;,.-_~')})"


def _rects_overlap(first: tuple[float, float, float, float], second: tuple[float, float, float, float]) -> bool:
    return not (first[2] < second[0] or first[0] > second[2] or first[3] < second[1] or first[1] > second[3])


def _character_link(character: dict, links: list[dict]) -> str | None:
    character_box = (
        float(character.get("x0", 0)),
        float(character.get("top", 0)),
        float(character.get("x1", 0)),
        float(character.get("bottom", 0)),
    )
    for link in links:
        if not link.get("uri"):
            continue
        link_box = (float(link["x0"]), float(link["top"]), float(link["x1"]), float(link["bottom"]))
        if _rects_overlap(character_box, link_box):
            return str(link["uri"])
    return None


def _styled_line(line: dict, links: list[dict] | None = None) -> str:
    links = links or []
    groups: list[tuple[bool, bool, str | None, str]] = []
    previous_character = None
    for character in line.get("chars", []):
        text = str(character.get("text", ""))
        font = str(character.get("fontname", "")).lower()
        style = ("bold" in font, "italic" in font or "oblique" in font, _character_link(character, links))
        if previous_character and not text.isspace():
            gap = float(character.get("x0", 0)) - float(previous_character.get("x1", 0))
            threshold = max(0.8, float(character.get("size", 0)) * 0.08)
            if gap > threshold:
                text = " " + text
        if groups and groups[-1][:3] == style:
            bold, italic, uri, value = groups[-1]
            groups[-1] = (bold, italic, uri, value + text)
        else:
            groups.append((*style, text))
        previous_character = character

    if len(groups) == 1:
        bold, italic, uri, _ = groups[0]
        core = _escape(str(line.get("text", "")).strip())
        if bold and italic:
            core = f"***{core}***"
        elif bold:
            core = f"**{core}**"
        elif italic:
            core = f"*{core}*"
        return _wrap_link(core, uri)

    parts = []
    for bold, italic, uri, value in groups:
        leading = value[: len(value) - len(value.lstrip())]
        trailing = value[len(value.rstrip()) :]
        core = _escape(value.strip())
        if core:
            if bold and italic:
                core = f"***{core}***"
            elif bold:
                core = f"**{core}**"
            elif italic:
                core = f"*{core}*"
            core = _wrap_link(core, uri)
        parts.append(leading + core + trailing)
    return "".join(parts).strip()


def _table_markdown(rows: list[list[str | None]]) -> str:
    width = max((len(row) for row in rows), default=0)
    if not width:
        return ""
    normalized = [[" ".join(str(cell or "").split()).replace("|", "\\|") for cell in row] + [""] * (width - len(row)) for row in rows]
    populated_columns = [index for index in range(width) if any(row[index] for row in normalized)]
    normalized = [[row[index] for index in populated_columns] for row in normalized]
    width = len(populated_columns)
    if width >= 4 and all(sum(bool(cell) for cell in row) <= 2 for row in normalized):
        midpoint = width // 2
        normalized = [
            [" ".join(cell for cell in row[:midpoint] if cell), " ".join(cell for cell in row[midpoint:] if cell)]
            for row in normalized
        ]
        width = 2
    if width == 1:
        return "\n>\n".join(f"> {row[0]}" for row in normalized if row[0])

    blocks: list[str] = []
    segment: list[list[str]] = []

    def flush_segment() -> None:
        if not segment:
            return
        header = segment[0] if len(segment) > 1 else [""] * width
        data_rows = segment[1:] if len(segment) > 1 else segment
        lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join("---" for _ in range(width)) + " |",
        ]
        lines.extend("| " + " | ".join(row) + " |" for row in data_rows)
        blocks.append("\n".join(lines))
        segment.clear()

    for row in normalized:
        values = [cell for cell in row if cell]
        if len(values) == 1:
            flush_segment()
            blocks.append(f"**{values[0]}**")
        elif values:
            segment.append(row)
    flush_segment()
    return "\n\n".join(blocks)


def _overlaps(top: float, bottom: float, bbox: tuple[float, float, float, float]) -> bool:
    return not (bottom < bbox[1] or top > bbox[3])


def _normalize_furniture(text: str) -> str:
    return re.sub(r"\d+", "#", " ".join(text.lower().split()))


def _page_covering_image_ratio(page) -> float:
    page_area = float(page.width) * float(page.height)
    if not page_area:
        return 0.0
    return max((float(image["width"]) * float(image["height"]) / page_area for image in page.images), default=0.0)


def _page_needs_ocr(page) -> bool:
    native_characters = sum(1 for character in page.chars if str(character.get("text", "")).strip())
    return native_characters < 40 and _page_covering_image_ratio(page) > 0.55


def _ocr_markdown(text: str) -> str:
    paragraphs = re.split(r"\n\s*\n", text.strip())
    return "\n\n".join(_escape(" ".join(paragraph.split())) for paragraph in paragraphs if paragraph.strip())


def _list_match(text: str, x0: float, body_left: float) -> tuple[str, str] | None:
    ordered = ORDERED_PATTERN.match(text)
    if ordered:
        return f"{ordered.group(1)}.", ordered.group(2)
    bullet = BULLET_PATTERN.match(text)
    if bullet:
        return "*", bullet.group(1)
    if x0 >= body_left + 8 and re.match(r"^o\s+\S", text):
        return "*", re.sub(r"^o\s+", "", text)
    return None


def _page_items(
    page,
    rendered_page,
    page_number: int,
    body_size: float,
    repeated_furniture: set[str],
    seen_images: set[str],
    ocr_adapter: OCRAdapter | None = None,
) -> list[dict[str, object]]:
    tables = []
    table_boxes = []
    for table in page.find_tables():
        rows = table.extract() or []
        markdown = _table_markdown(rows)
        if markdown:
            bbox = tuple(float(value) for value in table.bbox)
            table_boxes.append(bbox)
            tables.append({"top": bbox[1], "kind": "block", "content": markdown})

    links = page.hyperlinks or []
    lines = []
    for line in page.extract_text_lines(return_chars=True, strip=True):
        top, bottom = float(line["top"]), float(line["bottom"])
        text = str(line.get("text", "")).strip()
        is_furniture = top < float(page.height) * 0.1 or bottom > float(page.height) * 0.92
        if is_furniture and _normalize_furniture(text) in repeated_furniture:
            continue
        if any(_overlaps(top, bottom, bbox) for bbox in table_boxes):
            continue
        sizes = [float(character.get("size", 0)) for character in line.get("chars", [])]
        visible_characters = [character for character in line.get("chars", []) if str(character.get("text", "")).strip()]
        lines.append(
            {
                "top": top,
                "bottom": bottom,
                "x0": float(line["x0"]),
                "plain": text,
                "styled": _styled_line(line, links),
                "size": max(sizes, default=body_size),
                "bold": bool(visible_characters) and all("bold" in str(character.get("fontname", "")).lower() for character in visible_characters),
            }
        )

    body_left = min((float(line["x0"]) for line in lines if float(line["size"]) <= body_size * 1.1), default=72.0)
    items: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    active_list_positions: list[int] = []
    last_list_bottom: float | None = None

    def flush() -> None:
        nonlocal current
        if current and str(current["content"]).strip():
            items.append(current)
        current = None

    for line_index, line in enumerate(lines):
        plain = str(line["plain"])
        styled = str(line["styled"])
        size = float(line["size"])
        list_match = _list_match(plain, float(line["x0"]), body_left)
        if not plain or plain in {"•", "◦", "▪", "●", "○", "■", "□", "\uf0b7"}:
            continue
        if list_match:
            flush()
            marker, content = list_match
            styled_content = re.sub(r"^(?:[•◦▪●○■□\uf0b7]|\\?[+*-]|o|\d+[.)])\s+", "", styled)
            if not styled_content.strip():
                styled_content = _escape(content)
            x0 = round(float(line["x0"]))
            if last_list_bottom is None or float(line["top"]) - last_list_bottom > body_size * 1.25:
                active_list_positions.clear()
            matching_position = next((index for index, position in enumerate(active_list_positions) if abs(position - x0) <= 3), None)
            if matching_position is None:
                while active_list_positions and x0 < active_list_positions[-1] - 3:
                    active_list_positions.pop()
                if not active_list_positions or x0 > active_list_positions[-1] + 3:
                    active_list_positions.append(x0)
                matching_position = len(active_list_positions) - 1
            indent = matching_position
            current = {
                "top": line["top"],
                "kind": "list",
                "marker": marker,
                "indent": indent,
                "x0": line["x0"],
                "bottom": line["bottom"],
                "content": styled_content,
            }
            last_list_bottom = float(line["bottom"])
            continue
        if size >= max(18.0, body_size * 1.55):
            flush()
            level = 1 if page_number == 1 and not any(item.get("kind") == "heading" for item in items) else 2
            items.append({"top": line["top"], "kind": "heading", "content": f"{'#' * level} {plain}"})
            continue
        is_left_heading = float(line["x0"]) <= body_left + 3 and len(plain) <= 90 and not re.search(r"[.;!?]$", plain)
        if is_left_heading and (size >= body_size * 1.15 or bool(line["bold"]) and size >= body_size * 0.95):
            flush()
            level = 2 if size >= body_size * 1.15 else 3
            items.append({"top": line["top"], "kind": "heading", "content": f"{'#' * level} {plain}"})
            continue
        if current and current["kind"] == "list" and float(line["x0"]) >= float(current["x0"]) + 3:
            current["content"] = f"{current['content']} {styled}".strip()
            current["bottom"] = line["bottom"]
            last_list_bottom = float(line["bottom"])
            continue

        active_list_positions.clear()
        last_list_bottom = None

        is_field = bool(re.match(r"^[^:]{1,35}:\s*", plain)) and bool(line["bold"])
        if is_field:
            flush()
            items.append({"top": line["top"], "kind": "block", "content": styled})
            continue

        if current and current["kind"] == "paragraph" and float(line["top"]) - float(current["bottom"]) <= max(7, body_size * 0.8) and abs(float(line["x0"]) - float(current["x0"])) <= max(3, body_size * 0.25):
            current["content"] = f"{current['content']} {styled}".strip()
            current["bottom"] = line["bottom"]
        else:
            flush()
            current = {"top": line["top"], "kind": "paragraph", "x0": line["x0"], "bottom": line["bottom"], "content": styled}
    flush()

    page_image = rendered_page.to_pil().convert("RGB")
    scale_x = page_image.width / float(page.width)
    scale_y = page_image.height / float(page.height)
    for image in page.images:
        x0 = max(0, round(float(image["x0"]) * scale_x))
        y0 = max(0, round(float(image["top"]) * scale_y))
        x1 = min(page_image.width, round(float(image["x1"]) * scale_x))
        y1 = min(page_image.height, round(float(image["bottom"]) * scale_y))
        if x1 <= x0 or y1 <= y0:
            continue
        crop = page_image.crop((x0, y0, x1, y1))
        target_size = (
            max(1, round(float(image["width"]) * PDF_TO_CSS_PIXELS)),
            max(1, round(float(image["height"]) * PDF_TO_CSS_PIXELS)),
        )
        if crop.size != target_size:
            crop = crop.resize(target_size, Image.Resampling.LANCZOS)
        buffer = BytesIO()
        crop.save(buffer, format="PNG", optimize=True)
        image_bytes = buffer.getvalue()
        image_hash = hashlib.sha256(image_bytes).hexdigest()
        if image_hash in seen_images:
            continue
        seen_images.add(image_hash)
        encoded = base64.b64encode(image_bytes).decode("ascii")
        alt = "Image"
        if ocr_adapter and min(target_size) >= MIN_OCR_IMAGE_DIMENSION:
            try:
                image_text = ocr_adapter.extract_text(crop)
            except Exception:
                image_text = None
            if image_text:
                alt = " ".join(image_text.split())
        items.append({"top": float(image["top"]), "kind": "block", "content": f"![{alt} from page {page_number}](data:image/png;base64,{encoded})"})

    items.extend(tables)
    return sorted(items, key=lambda item: float(item["top"]))


def _native_pdf_markdown(content: bytes, ocr_adapter: OCRAdapter | None = None) -> str:
    chunks = []
    with pdfplumber.open(BytesIO(content)) as document:
        pdfium_document = pdfium.PdfDocument(content)
        furniture_counts: Counter[str] = Counter()
        for page in document.pages:
            for line in page.extract_text_lines(return_chars=False, strip=True):
                if float(line["top"]) < float(page.height) * 0.1 or float(line["bottom"]) > float(page.height) * 0.92:
                    furniture_counts[_normalize_furniture(str(line.get("text", "")))] += 1
        repeated_furniture = {text for text, count in furniture_counts.items() if text and count >= 2}
        seen_images: set[str] = set()
        for page_index, page in enumerate(document.pages):
            lines = page.extract_text_lines(return_chars=True, strip=True)
            sizes = [float(character.get("size", 0)) for line in lines for character in line.get("chars", []) if character.get("size")]
            body_size = median(sizes) if sizes else 12.0
            rendered = pdfium_document[page_index].render(scale=2)
            needs_full_page_ocr = ocr_adapter is not None and _page_needs_ocr(page)
            items = _page_items(
                page,
                rendered,
                page_index + 1,
                body_size,
                repeated_furniture,
                seen_images,
                None if needs_full_page_ocr else ocr_adapter,
            )
            if page_index:
                chunks.append(f"<!-- page {page_index + 1} -->")
            if needs_full_page_ocr:
                try:
                    ocr_text = ocr_adapter.extract_text(rendered.to_pil().convert("RGB"))
                except Exception:
                    ocr_text = None
                if ocr_text:
                    chunks.append(_ocr_markdown(ocr_text))
            for item in items:
                if item.get("kind") == "list":
                    chunks.append(f"{'    ' * int(item.get('indent', 0))}{item['marker']} {item['content']}")
                else:
                    chunks.append(str(item["content"]))
    return "\n\n".join(chunk for chunk in chunks if chunk.strip()).strip()


def convert_pdf(content: bytes) -> str:
    if not content:
        raise ValueError("PDF content cannot be empty")

    try:
        markdown = _native_pdf_markdown(content, detect_ocr_adapter())
        if markdown.strip():
            return markdown
    except Exception:
        pass

    result = MarkItDown(enable_plugins=False).convert_stream(
        BytesIO(content),
        stream_info=StreamInfo(extension=".pdf", mimetype=PDF_MIME_TYPE),
    )
    return result.markdown