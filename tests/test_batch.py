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
    batch = client.get("/batch")
    script = client.get("/static/batch.js")

    assert single.status_code == 200
    assert 'href="/batch"' in single.text
    assert 'id="conversion-form"' in single.text
    assert batch.status_code == 200
    assert 'href="/"' in batch.text
    assert 'id="batch-form"' in batch.text
    assert 'multiple' in batch.text
    assert script.status_code == 200
    assert 'fetch("/api/convert/batch"' in script.text


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


def test_batch_api_rejects_more_than_25_files() -> None:
    response = client.post(
        "/api/convert/batch",
        files=[("files", (f"document-{index}.docx", b"", "application/octet-stream")) for index in range(26)],
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "A batch can contain at most 25 files"}


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
