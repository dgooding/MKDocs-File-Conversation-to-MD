"""
High-fidelity PDF → Markdown converter for MkDocs.

Preserves:
  - Bold / italic / mono (from PDF font flags)
  - Text color (HTML <span style="color:..."> for MkDocs)
  - Font-size driven headings
  - Embedded images (extracted to an images/ folder, linked from MD)
  - Approximate reading order and line structure

True pixel-perfect PDF layout is not possible in Markdown; this aims for
visual fidelity of content (typography + images) suitable for MkDocs Material.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF


# PDF font flags (PyMuPDF)
FLAG_SUPERSCRIPT = 1
FLAG_ITALIC = 2
FLAG_SERIFED = 4
FLAG_MONO = 8
FLAG_BOLD = 16


@dataclass
class Span:
    text: str
    size: float
    flags: int
    color: int  # RGB as int 0xRRGGBB
    font: str = ""
    origin_x: float = 0.0
    origin_y: float = 0.0


@dataclass
class Line:
    spans: list[Span] = field(default_factory=list)
    y0: float = 0.0
    y1: float = 0.0
    x0: float = 0.0


@dataclass
class TextBlock:
    lines: list[Line] = field(default_factory=list)
    y0: float = 0.0
    x0: float = 0.0
    bbox: tuple[float, float, float, float] = (0, 0, 0, 0)


@dataclass
class ImageBlock:
    path: str  # relative path for markdown (images/xxx.png)
    bbox: tuple[float, float, float, float]
    width: int
    height: int
    alt: str = "image"


def slugify(value: str, max_len: int = 48) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[-\s]+", "-", value)
    return (value[:max_len] or "document").strip("-")


def rgb_int_to_hex(color: int) -> str:
    color &= 0xFFFFFF
    return f"#{color:06x}"


def is_near_black(color: int, threshold: int = 40) -> bool:
    r = (color >> 16) & 0xFF
    g = (color >> 8) & 0xFF
    b = color & 0xFF
    return r <= threshold and g <= threshold and b <= threshold


def is_near_white(color: int, threshold: int = 240) -> bool:
    r = (color >> 16) & 0xFF
    g = (color >> 8) & 0xFF
    b = color & 0xFF
    return r >= threshold and g >= threshold and b >= threshold


def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def format_span_html(span: Span) -> str:
    """Render one span with bold/italic/mono/color as HTML (MkDocs allows raw HTML)."""
    text = span.text
    if not text:
        return ""

    # Preserve intentional spaces; collapse only pure whitespace-only noise later
    escaped = escape_html(text)
    # Keep single newlines inside span as spaces
    escaped = escaped.replace("\r\n", "\n").replace("\r", "\n")
    if "\n" in escaped:
        escaped = escaped.replace("\n", "<br>\n")

    flags = span.flags
    is_bold = bool(flags & FLAG_BOLD) or "bold" in span.font.lower()
    is_italic = bool(flags & FLAG_ITALIC) or "italic" in span.font.lower() or "oblique" in span.font.lower()
    is_mono = bool(flags & FLAG_MONO) or any(
        m in span.font.lower() for m in ("mono", "courier", "consolas", "menlo", "code")
    )

    inner = escaped
    if is_mono:
        inner = f"<code>{inner}</code>"
    if is_bold and is_italic:
        inner = f"<strong><em>{inner}</em></strong>"
    elif is_bold:
        inner = f"<strong>{inner}</strong>"
    elif is_italic:
        inner = f"<em>{inner}</em>"

    color = span.color & 0xFFFFFF
    if not is_near_black(color) and not is_near_white(color):
        hex_color = rgb_int_to_hex(color)
        inner = f'<span style="color:{hex_color}">{inner}</span>'

    return inner


def median_body_size(blocks: list[TextBlock]) -> float:
    sizes: list[float] = []
    for b in blocks:
        for line in b.lines:
            for sp in line.spans:
                if sp.text.strip():
                    sizes.append(sp.size)
    if not sizes:
        return 11.0
    sizes.sort()
    return sizes[len(sizes) // 2]


def heading_level(size: float, body: float) -> int | None:
    """Map font size relative to body text → markdown heading level."""
    if body <= 0:
        body = 11.0
    ratio = size / body
    if ratio >= 1.85:
        return 1
    if ratio >= 1.55:
        return 2
    if ratio >= 1.35:
        return 3
    if ratio >= 1.2:
        return 4
    return None


def line_plain_text(line: Line) -> str:
    return "".join(s.text for s in line.spans)


def line_max_size(line: Line) -> float:
    sizes = [s.size for s in line.spans if s.text.strip()]
    return max(sizes) if sizes else 0.0


def line_is_bold_majority(line: Line) -> bool:
    chars = 0
    bold_chars = 0
    for s in line.spans:
        n = len(s.text.strip())
        if not n:
            continue
        chars += n
        if (s.flags & FLAG_BOLD) or "bold" in s.font.lower():
            bold_chars += n
    return chars > 0 and bold_chars / chars >= 0.7


def render_line_inline(line: Line) -> str:
    parts = [format_span_html(s) for s in line.spans]
    return "".join(parts).strip()


def parse_page_dict(page: fitz.Page) -> list[TextBlock]:
    data = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
    blocks: list[TextBlock] = []
    for b in data.get("blocks", []):
        if b.get("type") != 0:  # 0 = text
            continue
        tblock = TextBlock(
            y0=b["bbox"][1],
            x0=b["bbox"][0],
            bbox=tuple(b["bbox"]),
        )
        for line in b.get("lines", []):
            ln = Line(
                y0=line["bbox"][1],
                y1=line["bbox"][3],
                x0=line["bbox"][0],
            )
            for sp in line.get("spans", []):
                text = sp.get("text") or ""
                if text == "":
                    continue
                ln.spans.append(
                    Span(
                        text=text,
                        size=float(sp.get("size") or 0),
                        flags=int(sp.get("flags") or 0),
                        color=int(sp.get("color") or 0),
                        font=str(sp.get("font") or ""),
                        origin_x=float(sp.get("origin", [0, 0])[0]),
                        origin_y=float(sp.get("origin", [0, 0])[1]),
                    )
                )
            if ln.spans:
                tblock.lines.append(ln)
        if tblock.lines:
            blocks.append(tblock)
    return blocks


def extract_images(
    doc: fitz.Document,
    page: fitz.Page,
    page_index: int,
    images_dir: Path,
    rel_prefix: str,
) -> list[ImageBlock]:
    """Extract unique images from a page; return markdown-relative paths + bboxes."""
    results: list[ImageBlock] = []
    seen_xrefs: set[int] = set()

    # get_image_info gives bboxes; get_images gives xrefs
    image_list = page.get_images(full=True)
    # Map xref -> list of rects where drawn
    try:
        img_info = page.get_image_info(xrefs=True)
    except Exception:
        img_info = []

    xref_to_rects: dict[int, list[tuple[float, float, float, float]]] = {}
    for info in img_info:
        xref = info.get("xref")
        if not xref:
            continue
        bbox = info.get("bbox")
        if bbox:
            xref_to_rects.setdefault(xref, []).append(tuple(bbox))

    for img in image_list:
        xref = img[0]
        if xref in seen_xrefs or xref == 0:
            continue
        seen_xrefs.add(xref)

        try:
            extracted = doc.extract_image(xref)
        except Exception:
            continue
        if not extracted:
            continue

        img_bytes = extracted.get("image")
        if not img_bytes:
            continue
        ext = (extracted.get("ext") or "png").lower()
        if ext == "jpeg":
            ext = "jpg"
        # Prefer png/jpg/webp for browsers
        if ext not in ("png", "jpg", "jpeg", "gif", "webp", "bmp"):
            # convert via pixmap
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.n - pix.alpha > 3:  # CMYK
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                img_bytes = pix.tobytes("png")
                ext = "png"
                width, height = pix.width, pix.height
            except Exception:
                continue
        else:
            width = int(extracted.get("width") or 0)
            height = int(extracted.get("height") or 0)

        digest = hashlib.md5(img_bytes).hexdigest()[:10]
        filename = f"p{page_index + 1:03d}_{xref}_{digest}.{ext}"
        out_path = images_dir / filename
        out_path.write_bytes(img_bytes)

        rects = xref_to_rects.get(xref) or [(0, 0, float(width or 0), float(height or 0))]
        for rect in rects:
            results.append(
                ImageBlock(
                    path=f"{rel_prefix}/{filename}".replace("\\", "/"),
                    bbox=rect,
                    width=width or 0,
                    height=height or 0,
                    alt=f"Page {page_index + 1} image",
                )
            )

    return results


def merge_reading_order(
    text_blocks: list[TextBlock],
    images: list[ImageBlock],
) -> list[tuple[str, Any]]:
    """
    Interleave text blocks and images by vertical position (top → bottom).
    Returns list of ("text", TextBlock) | ("image", ImageBlock).
    """
    items: list[tuple[float, float, int, str, Any]] = []
    for i, tb in enumerate(text_blocks):
        items.append((tb.y0, tb.x0, i, "text", tb))
    for j, im in enumerate(images):
        items.append((im.bbox[1], im.bbox[0], 10_000 + j, "image", im))
    items.sort(key=lambda t: (round(t[0], 1), round(t[1], 1), t[2]))
    return [(kind, obj) for _, _, _, kind, obj in items]


def render_text_block(block: TextBlock, body_size: float) -> str:
    chunks: list[str] = []
    for line in block.lines:
        plain = line_plain_text(line).strip()
        if not plain:
            chunks.append("")
            continue

        max_size = line_max_size(line)
        level = heading_level(max_size, body_size)
        inline = render_line_inline(line)

        # Single-line short bold large text → heading
        if level and len(plain) < 120 and "\n" not in plain:
            # Strip outer tags for cleaner headings when whole line is one style
            heading_text = plain  # plain for heading hash line
            # Prefer rich HTML heading content when colors present
            has_color = any(
                not is_near_black(s.color) and not is_near_white(s.color)
                for s in line.spans
                if s.text.strip()
            )
            if has_color or any(
                (s.flags & FLAG_ITALIC) for s in line.spans if s.text.strip()
            ):
                chunks.append(f"{'#' * level} {inline}")
            else:
                # bold already implied by heading
                chunks.append(f"{'#' * level} {escape_html(heading_text)}")
            continue

        chunks.append(inline)

    # Join lines: blank line between paragraphs (gap heuristic via empty lines)
    md_lines: list[str] = []
    for i, c in enumerate(chunks):
        if c == "":
            if md_lines and md_lines[-1] != "":
                md_lines.append("")
            continue
        md_lines.append(c)
        # soft line break between consecutive non-empty lines in same block
        # (PDF often uses hard line wraps)
        if i + 1 < len(chunks) and chunks[i + 1] != "":
            # use two trailing spaces for MD soft break, or <br>
            if not md_lines[-1].startswith("#"):
                md_lines[-1] = md_lines[-1] + "  "

    return "\n".join(md_lines).strip()


def render_image(im: ImageBlock) -> str:
    # width hint helps MkDocs layout; glightbox can zoom
    return f'![{escape_html(im.alt)}]({im.path}){{ loading=lazy }}'


def build_markdown(
    title: str,
    pages_md: list[str],
    source_name: str,
    page_count: int,
    image_count: int,
) -> str:
    front = (
        "---\n"
        f'title: "{title.replace(chr(34), chr(39))}"\n'
        f'description: "Converted from {source_name}"\n'
        "tags:\n"
        "  - converted\n"
        "  - pdf\n"
        "---\n\n"
    )
    meta = (
        f'# {escape_html(title)}\n\n'
        f'!!! info "Conversion metadata"\n'
        f"    Source: `{escape_html(source_name)}` · "
        f"Pages: **{page_count}** · Images extracted: **{image_count}**\n\n"
        "---\n\n"
    )
    body = "\n\n".join(pages_md)
    return front + meta + body + "\n"


def _page_text_via_ocr(page: fitz.Page) -> str:
    """OCR a single page when Tesseract is available (scanned PDFs)."""
    try:
        tp = page.get_textpage_ocr(flags=0, language="eng", dpi=200)
        return (page.get_text(textpage=tp) or "").strip()
    except Exception:
        return ""


def convert_pdf_to_markdown(
    pdf_path: Path | str,
    output_dir: Path | str,
    *,
    doc_slug: str | None = None,
    title: str | None = None,
    images_subdir: str = "images",
    page_break_markers: bool = True,
    use_ocr: bool = False,
) -> dict[str, Any]:
    """
    Convert a PDF to Markdown + extracted images.

    Layout written to:
        output_dir/
          {slug}.md
          images/
            p001_....png
            ...

    Returns dict with paths and stats.
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    slug = doc_slug or slugify(pdf_path.stem)
    doc_title = title or pdf_path.stem.replace("-", " ").replace("_", " ").strip()
    images_dir = output_dir / images_subdir
    images_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    page_sections: list[str] = []
    total_images = 0
    all_image_paths: list[str] = []

    try:
        for page_index in range(len(doc)):
            page = doc[page_index]
            text_blocks = parse_page_dict(page)
            body_size = median_body_size(text_blocks)

            images = extract_images(
                doc,
                page,
                page_index,
                images_dir,
                rel_prefix=images_subdir,
            )
            total_images += len(images)
            all_image_paths.extend(im.path for im in images)

            ordered = merge_reading_order(text_blocks, images)
            parts: list[str] = []

            if page_break_markers and len(doc) > 1:
                parts.append(f"### Page {page_index + 1}\n")

            for kind, obj in ordered:
                if kind == "text":
                    rendered = render_text_block(obj, body_size)
                    if rendered:
                        parts.append(rendered)
                else:
                    parts.append(render_image(obj))

            # Sparse / empty text pages → OCR (scanned PDFs)
            plain_len = sum(
                len(line_plain_text(ln).strip())
                for tb in text_blocks
                for ln in tb.lines
            )
            if plain_len < 40:
                if use_ocr:
                    ocr_text = _page_text_via_ocr(page)
                    if ocr_text:
                        parts.append(escape_html(ocr_text))
                elif not text_blocks:
                    raw = page.get_text("text").strip()
                    if raw:
                        parts.append(escape_html(raw))

            page_sections.append("\n\n".join(parts).strip())
    finally:
        doc.close()

    md_name = f"{slug}.md"
    md_path = output_dir / md_name
    md_content = build_markdown(
        title=doc_title,
        pages_md=page_sections,
        source_name=pdf_path.name,
        page_count=len(page_sections),
        image_count=len(set(all_image_paths)),
    )
    md_path.write_text(md_content, encoding="utf-8")

    return {
        "slug": slug,
        "title": doc_title,
        "markdown_path": str(md_path.resolve()),
        "markdown_rel": md_name,
        "images_dir": str(images_dir.resolve()),
        "image_count": len(set(all_image_paths)),
        "page_count": len(page_sections),
        "image_paths": sorted(set(all_image_paths)),
        "markdown_preview": md_content[:4000],
    }


def convert_bytes_pdf(
    data: bytes,
    output_dir: Path | str,
    filename: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Write bytes to a temp PDF under output_dir then convert."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    # Use the original display name for metadata, but a safe temp path for IO
    safe = slugify(Path(filename).stem) + ".pdf"
    tmp_pdf = output_dir / safe
    tmp_pdf.write_bytes(data)
    try:
        # Prefer original stem for title if not overridden
        kwargs.setdefault("title", Path(filename).stem.replace("-", " ").replace("_", " "))
        result = convert_pdf_to_markdown(tmp_pdf, output_dir, **kwargs)
        # Rewrite metadata source name to original upload name
        md_path = Path(result["markdown_path"])
        if md_path.is_file():
            text = md_path.read_text(encoding="utf-8")
            text = text.replace(f"Converted from {safe}", f"Converted from {Path(filename).name}")
            text = text.replace(f"Source: `{safe}`", f"Source: `{Path(filename).name}`")
            md_path.write_text(text, encoding="utf-8")
            result["markdown_preview"] = text[:4000]
    finally:
        if tmp_pdf.exists():
            tmp_pdf.unlink(missing_ok=True)
    result["source_filename"] = filename
    return result
