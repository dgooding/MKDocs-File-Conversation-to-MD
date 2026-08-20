import json
from io import BytesIO
from zipfile import ZipFile

from fastapi.testclient import TestClient

from docs_to_markdown import convert_docx, convert_pdf
from docs_to_markdown.api import app
from docs_to_markdown.batch_converter import CONVERTERS, convert_batch
from test_converter import make_docx, make_pdf


client = TestClient(app)


def test_batch_reuses_authoritative_converters() -> None:
    docx = make_docx()
    pdf = make_pdf()
    archive, manifest = convert_batch(
        [("proof.docx", docx), ("proof.pdf", pdf), ("empty.docx", b""), ("notes.txt", b"text")]
    )

    assert manifest["total_files"] == 4
    assert manifest["succeeded"] == 2
    assert manifest["empty"] == 1
    assert manifest["unsupported"] == 1

    with ZipFile(archive) as zip_file:
        assert zip_file.read("proof.md").decode("utf-8") == convert_docx(docx)
        assert zip_file.read("proof-2.md").decode("utf-8") == convert_pdf(pdf)
        stored_manifest = json.loads(zip_file.read("manifest.json"))
        assert stored_manifest == manifest
        assert zip_file.namelist() == ["proof.md", "proof-2.md", "manifest.json"]


def test_batch_page_is_separate_and_linked() -> None:
    single = client.get("/")
    standalone_converter = client.get("/app/converter")
    batch = client.get("/batch")
    script = client.get("/static/batch.js")

    assert single.status_code == 200
    assert 'href="/batch"' in single.text
    assert standalone_converter.status_code == 200
    assert 'id="conversion-form"' in standalone_converter.text
    assert batch.status_code == 200
    assert 'href="/"' in batch.text
    assert 'id="batch-form"' in batch.text
    assert 'id="batch-progress-panel"' in batch.text
    assert 'id="batch-progress"' in batch.text
    assert 'id="batch-download"' in batch.text
    assert 'id="batch-publish"' in batch.text
    assert 'multiple' in batch.text
    assert script.status_code == 200
    assert 'fetch("/api/convert/batch"' in script.text
    assert "startProgress" in script.text
    assert 'fetch("/api/publish/batch"' in script.text


def test_batch_api_returns_zip_with_exact_outputs() -> None:
    docx = make_docx()
    pdf = make_pdf()
    response = client.post(
        "/api/convert/batch",
        files=[
            ("files", ("document.docx", docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
            ("files", ("guide.pdf", pdf, "application/pdf")),
        ],
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "markdown-batch-" in response.headers["content-disposition"]
    with ZipFile(BytesIO(response.content)) as zip_file:
        assert zip_file.read("document.md").decode("utf-8") == convert_docx(docx)
        assert zip_file.read("guide.md").decode("utf-8") == convert_pdf(pdf)
        manifest = json.loads(zip_file.read("manifest.json"))
        assert manifest["succeeded"] == 2
        assert manifest["errors"] == 0


def test_batch_publish_api_publishes_each_document(monkeypatch, tmp_path) -> None:
    import docs_to_markdown.mkdocs_publish as mkdocs_publish

    (tmp_path / "docs" / "markdown").mkdir(parents=True)
    (tmp_path / "docs" / "backups").mkdir(parents=True)
    monkeypatch.setattr(mkdocs_publish, "MKDOCS_SITE_ROOT", tmp_path)
    response = client.post(
        "/api/publish/batch",
        files=[
            ("files", ("one.pdf", make_pdf(), "application/pdf")),
            ("files", ("two.docx", make_docx(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
        ],
    )

    assert response.status_code == 200
    assert response.json()["count"] == 2
    assert len({item["slug"] for item in response.json()["published"]}) == 2


def test_batch_publish_rejects_unsupported_file() -> None:
    response = client.post("/api/publish/batch", files=[("files", ("notes.txt", b"text", "text/plain"))])

    assert response.status_code == 415


def test_batch_api_rejects_more_than_25_files() -> None:
    response = client.post(
        "/api/convert/batch",
        files=[("files", (f"document-{index}.docx", b"", "application/octet-stream")) for index in range(26)],
    )

    assert response.status_code == 400


def test_batch_ocr_image_output_matches_direct_conversion() -> None:
    from docx import Document
    from docx.shared import Inches
    from PIL import Image, ImageDraw

    document = Document()
    image = Image.new("RGB", (240, 60), "white")
    ImageDraw.Draw(image).text((10, 20), "Batch Label", fill="black")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    document.add_picture(BytesIO(buffer.getvalue()), width=Inches(2))
    stream = BytesIO()
    document.save(stream)
    docx = stream.getvalue()

    response = client.post(
        "/api/convert/batch",
        files=[("files", ("labeled.docx", docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
    )

    assert response.status_code == 200
    direct_markdown = convert_docx(docx)
    with ZipFile(BytesIO(response.content)) as zip_file:
        assert zip_file.read("labeled.md").decode("utf-8") == direct_markdown
    assert "Batch" in direct_markdown


def test_batch_isolates_converter_error(monkeypatch) -> None:
    def fail_conversion(content: bytes) -> str:
        raise RuntimeError("forced converter failure")

    monkeypatch.setitem(CONVERTERS, ".docx", fail_conversion)

    archive, manifest = convert_batch(
        [("broken.docx", b"not empty"), ("working.pdf", make_pdf())]
    )

    assert manifest["succeeded"] == 1
    assert manifest["errors"] == 1
    assert [result["status"] for result in manifest["results"]] == ["error", "success"]
    assert manifest["results"][0]["detail"] == "Document could not be converted"
    with ZipFile(archive) as zip_file:
        assert "broken.md" not in zip_file.namelist()
        assert zip_file.read("working.md").decode("utf-8") == convert_pdf(make_pdf())
