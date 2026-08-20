from io import BytesIO

import pdfplumber
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from docs_to_markdown import convert_pdf
from docs_to_markdown.api import app
from docs_to_markdown.ocr_adapter import TesseractOCR
from docs_to_markdown.pdf_converter import _native_pdf_markdown, _page_needs_ocr
from test_converter import make_pdf
from test_pdf_fidelity import make_fidelity_pdf


def make_scanned_pdf() -> bytes:
    image = Image.new("RGB", (900, 1200), "white")
    draw = ImageDraw.Draw(image)
    draw.text((80, 80), "Scanned Installation Guide", fill="black")
    draw.text((80, 150), "Prerequisites", fill="black")
    draw.text((100, 210), "- Administrator access", fill="black")
    draw.text((100, 260), "- Network connection", fill="black")
    draw.rectangle((80, 340, 820, 520), outline="black", width=3)
    draw.line((80, 400, 820, 400), fill="black", width=3)
    draw.line((450, 340, 450, 520), fill="black", width=3)
    draw.text((110, 360), "Requirement", fill="black")
    draw.text((480, 360), "Status", fill="black")
    draw.text((110, 440), "VPN", fill="black")
    draw.text((480, 440), "Ready", fill="black")
    stream = BytesIO()
    image.save(stream, format="PDF", resolution=150)
    return stream.getvalue()


class FakeOCR:
    def __init__(self) -> None:
        self.calls = 0

    def extract_text(self, image: Image.Image) -> str:
        self.calls += 1
        return "Scanned Installation Guide\n\nPrerequisites\nAdministrator access\nNetwork connection"


def test_detects_image_only_page_and_preserves_visual() -> None:
    pdf = make_scanned_pdf()
    with pdfplumber.open(BytesIO(pdf)) as document:
        assert _page_needs_ocr(document.pages[0]) is True

    markdown = _native_pdf_markdown(pdf)

    assert "data:image/" in markdown
    assert "Scanned Installation Guide" not in markdown


def test_uses_optional_ocr_only_for_scanned_pages() -> None:
    scanned_provider = FakeOCR()
    scanned_markdown = _native_pdf_markdown(make_scanned_pdf(), scanned_provider)
    native_provider = FakeOCR()
    native_markdown = _native_pdf_markdown(make_pdf(), native_provider)

    assert scanned_provider.calls == 1
    assert "Scanned Installation Guide" in scanned_markdown
    assert "data:image/" in scanned_markdown
    assert native_provider.calls == 0
    assert "PDF Conversion Proof" in native_markdown


def test_missing_tesseract_is_nonfatal(monkeypatch) -> None:
    monkeypatch.setenv("TESSERACT_CMD", r"C:\missing\tesseract.exe")

    assert TesseractOCR.detect() is None
    assert "PDF Conversion Proof" in convert_pdf(make_pdf())


def test_ocr_text_embedded_for_images_on_native_text_pages() -> None:
    provider = FakeOCR()
    markdown = _native_pdf_markdown(make_fidelity_pdf(), provider)

    assert provider.calls == 1
    assert "[^ocr-1]" in markdown
    assert "[^ocr-1]: OCR text: Scanned Installation Guide" in markdown
    assert "data:image/png;base64," in markdown


def test_scanned_pdf_api_matches_direct_conversion() -> None:
    pdf = make_scanned_pdf()
    response = TestClient(app).post(
        "/api/convert",
        files={"file": ("scanned.pdf", pdf, "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json()["markdown"] == convert_pdf(pdf)
    assert "data:image/" in response.json()["markdown"]