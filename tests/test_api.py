from fastapi.testclient import TestClient

from docs_to_markdown import convert_docx, convert_pdf
from docs_to_markdown.api import app
from test_converter import make_docx, make_pdf


client = TestClient(app)


def test_serves_upload_page() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert 'id="conversion-form"' in response.text
    assert 'accept=".docx,.pdf"' in response.text
    assert 'id="markdown"' in response.text
    assert 'id="preview"' in response.text
    assert 'id="download"' in response.text
    assert 'id="selected-file"' in response.text
    assert "How to use" in response.text
    assert "Download Markdown" in response.text


def test_serves_upload_page_script() -> None:
    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert 'fetch("/api/convert"' in response.text
    assert 'fetch("/api/render"' in response.text
    assert "text/markdown" in response.text
    assert "function setStatus" in response.text
    assert "outputFilename = result.filename" in response.text
    assert "download.disabled = false" in response.text


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