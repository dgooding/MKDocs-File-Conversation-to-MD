import base64
from io import BytesIO
import re
from typing import Any, Optional
from urllib.parse import quote, unquote, urlparse, urlunparse

from docx import Document
import mammoth
import markdownify
from PIL import Image

from .docx_math import preprocess_docx_equations
from .ocr_adapter import OCRAdapter, detect_ocr_adapter

MIN_OCR_IMAGE_DIMENSION = 40


class _DocxMarkdownConverter(markdownify.MarkdownConverter):
    def __init__(self, **options: Any):
        options["heading_style"] = options.get("heading_style", markdownify.ATX)
        options["keep_data_uris"] = options.get("keep_data_uris", False)
        super().__init__(**options)

    def convert_hn(
        self,
        n: int,
        el: Any,
        text: str,
        convert_as_inline: Optional[bool] = False,
        **kwargs,
    ) -> str:
        if not convert_as_inline and not re.search(r"^\n", text):
            return "\n" + super().convert_hn(n, el, text, convert_as_inline)
        return super().convert_hn(n, el, text, convert_as_inline)

    def convert_a(
        self,
        el: Any,
        text: str,
        convert_as_inline: Optional[bool] = False,
        **kwargs,
    ) -> str:
        prefix, suffix, text = markdownify.chomp(text)
        if not text:
            return ""
        if el.find_parent("pre") is not None:
            return text

        href = el.get("href")
        title = el.get("title")
        if href:
            try:
                parsed_url = urlparse(href)
                if parsed_url.scheme and parsed_url.scheme.lower() not in ["http", "https", "file"]:
                    return f"{prefix}{text}{suffix}"
                href = urlunparse(parsed_url._replace(path=quote(unquote(parsed_url.path))))
            except ValueError:
                return f"{prefix}{text}{suffix}"

        if self.options["autolinks"] and text.replace(r"\_", "_") == href and not title and not self.options["default_title"]:
            return f"<{href}>"
        if self.options["default_title"] and not title:
            title = href
        title_part = f' "{title.replace(chr(34), r"\"")}"' if title else ""
        return f"{prefix}[{text}]({href}{title_part}){suffix}" if href else text

    def convert_img(
        self,
        el: Any,
        text: str,
        convert_as_inline: Optional[bool] = False,
        **kwargs,
    ) -> str:
        alt = (el.attrs.get("alt") or "").replace("\n", " ")
        src = el.attrs.get("src") or el.attrs.get("data-src") or ""
        title = el.attrs.get("title") or ""
        title_part = f' "{title.replace(chr(34), r"\"")}"' if title else ""
        if convert_as_inline and el.parent.name not in self.options["keep_inline_images_in"]:
            return alt
        if src.startswith("data:") and not self.options["keep_data_uris"]:
            src = src.split(",")[0] + "..."
        return f"![{alt}]({src}{title_part})"

    def convert_input(
        self,
        el: Any,
        text: str,
        convert_as_inline: Optional[bool] = False,
        **kwargs,
    ) -> str:
        if el.get("type") == "checkbox":
            return "[x] " if el.has_attr("checked") else "[ ] "
        return ""


def _has_numbering(paragraph) -> bool:
    properties = paragraph._p.pPr
    return properties is not None and properties.numPr is not None


def _fully_bold(paragraph) -> bool:
    runs = [run for run in paragraph.runs if run.text.strip()]
    return bool(runs) and all(run.bold is True for run in runs)


def _max_font_size(paragraph) -> float:
    sizes = [run.font.size.pt for run in paragraph.runs if run.text.strip() and run.font.size]
    return max(sizes, default=0.0)


def _infer_heading_level(paragraph) -> int | None:
    text = paragraph.text.strip()
    style_name = paragraph.style.name.lower()
    if not text or style_name.startswith(("heading", "title")):
        return None
    if style_name.startswith("list") or _has_numbering(paragraph) or not _fully_bold(paragraph):
        return None

    font_size = _max_font_size(paragraph)
    if font_size >= 17:
        return 1
    if font_size >= 15:
        return 2
    if len(text) <= 60 and not text.endswith((":", ".", ";", "!", "?")):
        return 3
    return None


def _prepare_docx(content: bytes) -> BytesIO:
    document = Document(BytesIO(content))
    changed = False
    for paragraph in document.paragraphs:
        level = _infer_heading_level(paragraph)
        if level is not None:
            paragraph.style = f"Heading {level}"
            for run in paragraph.runs:
                run.bold = None
                run.font.size = None
                run.font.color.rgb = None
            changed = True

    if not changed:
        return BytesIO(content)

    stream = BytesIO()
    document.save(stream)
    stream.seek(0)
    return stream


def _docx_image_attributes(image, ocr_adapter: OCRAdapter | None) -> dict[str, str]:
    with image.open() as image_bytes:
        raw = image_bytes.read()
    encoded = base64.b64encode(raw).decode("ascii")
    attributes = {"src": f"data:{image.content_type};base64,{encoded}"}
    if not ocr_adapter:
        return attributes
    try:
        with Image.open(BytesIO(raw)) as pil_image:
            if min(pil_image.size) < MIN_OCR_IMAGE_DIMENSION:
                return attributes
            ocr_text = ocr_adapter.extract_text(pil_image.convert("RGB"))
    except Exception:
        ocr_text = None
    if ocr_text:
        base_alt = image.alt_text or ""
        attributes["alt"] = f"{base_alt} {ocr_text}".strip()
    return attributes


def convert_docx(content: bytes) -> str:
    if not content:
        raise ValueError("DOCX content cannot be empty")

    prepared = preprocess_docx_equations(_prepare_docx(content))
    ocr_adapter = detect_ocr_adapter()
    convert_image = mammoth.images.img_element(lambda image: _docx_image_attributes(image, ocr_adapter))
    html = mammoth.convert_to_html(prepared, convert_image=convert_image).value
    return _DocxMarkdownConverter(keep_data_uris=True).convert(html).strip()
