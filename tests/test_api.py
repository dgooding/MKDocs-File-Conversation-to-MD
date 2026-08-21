from fastapi.testclient import TestClient

from docs_to_markdown import convert_docx, convert_pdf
from docs_to_markdown.api import app
from test_converter import make_docx, make_pdf


client = TestClient(app)


def test_serves_mkdocs_home_page() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Document library" in response.text
    assert "Converter" in response.text


def test_serves_standalone_converter_page() -> None:
    response = client.get("/app/converter")

    assert response.status_code == 200
    assert 'id="conversion-form"' in response.text
    assert 'accept=".docx,.pdf"' in response.text
    assert 'id="markdown"' in response.text
    assert 'id="preview"' in response.text
    assert 'id="download"' in response.text
    assert 'id="selected-file"' in response.text
    assert 'id="conversion-progress-panel"' in response.text
    assert 'id="conversion-progress"' in response.text
    assert "How to use" in response.text
    assert "Download Markdown" in response.text
    assert 'href="/mkdocs/"' in response.text
    assert "Upload to MkDocs" in response.text


def test_serves_themed_converter_page() -> None:
    with TestClient(app) as lifespan_client:
        response = lifespan_client.get("/converter")

    assert response.status_code == 200
    assert "Convert a document" in response.text
    assert "Drop a DOCX or PDF here" in response.text


def test_serves_mkdocs_site_during_app_lifespan() -> None:
    with TestClient(app) as lifespan_client:
        response = lifespan_client.get("/mkdocs/")

    assert response.status_code == 200
    assert "Docs to Markdown" in response.text


def test_serves_mkdocs_root_assets() -> None:
    with TestClient(app) as lifespan_client:
        response = lifespan_client.get("/css/theme.css")

    assert response.status_code == 200
    assert "wy-nav-side" in response.text


def test_serves_upload_page_script() -> None:
    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert 'fetch("/api/convert"' in response.text
    assert 'fetch("/api/render"' in response.text
    assert "text/markdown" in response.text
    assert "function setStatus" in response.text
    assert "outputFilename = result.filename" in response.text
    assert "download.disabled = false" in response.text
    assert "Approximate timing only" not in response.text
    assert "estimateSeconds" in response.text
    assert "/mkdocs/markdown/" in response.text
    assert "Convert a file before publishing." in response.text
    assert "item.msg" in response.text
    assert "Building library page" in response.text


def test_library_converter_script_explains_upload_failures() -> None:
    from pathlib import Path

    script = (
        Path(__file__).resolve().parents[1] / "mkdocs-site" / "docs" / "javascripts" / "converter.js"
    ).read_text(encoding="utf-8")
    converter_page = (
        Path(__file__).resolve().parents[1] / "mkdocs-site" / "docs" / "converter.md"
    ).read_text(encoding="utf-8")

    assert "Convert a document before uploading it to the library." in script
    assert "item.msg" in script
    assert "Building library page" in script
    assert 'id="library-publish" type="button" disabled>' not in converter_page


def test_serves_responsive_preview_styles() -> None:
    response = client.get("/static/app.css")

    assert response.status_code == 200
    assert ".preview img" in response.text
    assert "max-width: 100%" in response.text


def test_renders_markdown_preview() -> None:
    response = client.post(
        "/api/render",
        json={"markdown": "# Preview\n\n| Name | Status |\n| --- | --- |\n| Alpha | Ready |"},
    )

    assert response.status_code == 200
    assert "<h1>Preview</h1>" in response.json()["html"]
    assert "<table>" in response.json()["html"]


def test_renders_embedded_raster_image() -> None:
    response = client.post(
        "/api/render",
        json={"markdown": "![image](data:image/png;base64,iVBORw0KGgo=)"},
    )

    assert response.status_code == 200
    assert '<img src="data:image/png;base64,iVBORw0KGgo="' in response.json()["html"]


def test_preview_blocks_raw_html_and_unsafe_link() -> None:
    response = client.post(
        "/api/render",
        json={"markdown": '<script>alert("unsafe")</script>\n\n[bad](javascript:alert(1))'},
    )

    assert response.status_code == 200
    assert "<script>" not in response.json()["html"]
    assert 'href="javascript:' not in response.json()["html"]
    assert "data:image/svg+xml" not in response.json()["html"]


def test_uploads_docx_and_returns_markdown() -> None:
    docx = make_docx()
    response = client.post(
        "/api/convert",
        files={
            "file": (
                "conversion-proof.docx",
                docx,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["filename"] == "conversion-proof.md"
    assert response.json()["markdown"] == convert_docx(docx)


def test_uploads_pdf_and_returns_exact_direct_markdown() -> None:
    pdf = make_pdf()
    response = client.post(
        "/api/convert",
        files={"file": ("conversion-proof.pdf", pdf, "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json()["filename"] == "conversion-proof.md"
    assert response.json()["markdown"] == convert_pdf(pdf)


def test_uploads_docx_with_ocr_image_and_matches_direct_markdown() -> None:
    from io import BytesIO

    from docx import Document
    from docx.shared import Inches
    from PIL import Image, ImageDraw

    document = Document()
    image = Image.new("RGB", (240, 60), "white")
    ImageDraw.Draw(image).text((10, 20), "Parity Label", fill="black")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    document.add_picture(BytesIO(buffer.getvalue()), width=Inches(2))
    stream = BytesIO()
    document.save(stream)
    docx = stream.getvalue()

    response = client.post(
        "/api/convert",
        files={
            "file": (
                "ocr-proof.docx",
                docx,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    direct_markdown = convert_docx(docx)
    assert response.json()["markdown"] == direct_markdown
    assert "Parity" in direct_markdown


def test_rejects_non_docx_upload() -> None:
    response = client.post(
        "/api/convert",
        files={"file": ("notes.txt", b"Not a DOCX", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json() == {"detail": "Only DOCX and PDF files are supported"}


def test_rejects_empty_docx_upload() -> None:
    response = client.post(
        "/api/convert",
        files={"file": ("empty.docx", b"", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Document cannot be empty"}


def test_returns_422_when_converter_fails(monkeypatch) -> None:
    def fail_conversion(content: bytes) -> str:
        raise RuntimeError("forced converter failure")

    monkeypatch.setattr("docs_to_markdown.api.convert_pdf", fail_conversion)

    response = client.post(
        "/api/convert",
        files={"file": ("broken.pdf", make_pdf(), "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Document could not be converted"}