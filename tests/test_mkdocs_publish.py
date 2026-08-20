from pathlib import Path

from fastapi.testclient import TestClient

from docs_to_markdown.api import app
from docs_to_markdown.mkdocs_publish import _safe_stem, publish_to_mkdocs


client = TestClient(app)


def test_publish_writes_markdown_and_backup_into_site(tmp_path: Path) -> None:
    (tmp_path / "docs" / "markdown").mkdir(parents=True)
    (tmp_path / "docs" / "backups").mkdir(parents=True)

    result = publish_to_mkdocs("Report v1.docx", b"fake docx bytes", "# Report\n\nBody text.", site_root=tmp_path)

    markdown_path = tmp_path / "docs" / "markdown" / result["markdown_file"]
    backup_path = tmp_path / "docs" / "backups" / result["backup_file"]
    assert markdown_path.read_text(encoding="utf-8") == "# Report\n\nBody text."
    assert backup_path.read_bytes() == b"fake docx bytes"
    assert result["backup_file"].endswith(".docx")
    assert "Report_v1" in result["slug"]


def test_publish_appends_index_links(tmp_path: Path) -> None:
    (tmp_path / "docs" / "markdown").mkdir(parents=True)
    (tmp_path / "docs" / "backups").mkdir(parents=True)

    first = publish_to_mkdocs("a.pdf", b"one", "# A", site_root=tmp_path)
    second = publish_to_mkdocs("b.pdf", b"two", "# B", site_root=tmp_path)

    markdown_index = (tmp_path / "docs" / "markdown" / "index.md").read_text(encoding="utf-8")
    backups_index = (tmp_path / "docs" / "backups" / "index.md").read_text(encoding="utf-8")
    assert first["markdown_file"] in markdown_index
    assert second["markdown_file"] in markdown_index
    assert first["backup_file"] in backups_index
    assert second["backup_file"] in backups_index


def test_publish_separates_appended_links_from_index_text(tmp_path: Path) -> None:
    (tmp_path / "docs" / "markdown").mkdir(parents=True)
    (tmp_path / "docs" / "backups").mkdir(parents=True)
    (tmp_path / "docs" / "markdown" / "index.md").write_text("# Documents\n\nSummary.", encoding="utf-8")

    result = publish_to_mkdocs("report.pdf", b"pdf", "# Report", site_root=tmp_path)

    index = (tmp_path / "docs" / "markdown" / "index.md").read_text(encoding="utf-8")
    assert f"Summary.\n\n- [{result['slug']}]" in index


def test_publish_rejects_unsupported_extension(tmp_path: Path) -> None:
    (tmp_path / "docs" / "markdown").mkdir(parents=True)
    (tmp_path / "docs" / "backups").mkdir(parents=True)

    try:
        publish_to_mkdocs("notes.txt", b"data", "# Notes", site_root=tmp_path)
    except ValueError as error:
        assert "Only DOCX and PDF" in str(error)
    else:
        raise AssertionError("Expected unsupported extension to be rejected")


def test_publish_rejects_missing_site_root(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"

    try:
        publish_to_mkdocs("a.pdf", b"one", "# A", site_root=missing)
    except FileNotFoundError as error:
        assert "mkdocs-site" in str(error)
    else:
        raise AssertionError("Expected missing site root to be rejected")


def test_safe_stem_strips_unsafe_characters() -> None:
    assert _safe_stem("../../evil name!.docx") == "evil_name"
    assert _safe_stem("") == "document"


def test_api_publish_endpoint_writes_files(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "docs" / "markdown").mkdir(parents=True)
    (tmp_path / "docs" / "backups").mkdir(parents=True)

    import docs_to_markdown.mkdocs_publish as mkdocs_publish

    monkeypatch.setattr(mkdocs_publish, "MKDOCS_SITE_ROOT", tmp_path)

    response = client.post(
        "/api/publish",
        files={"file": ("proof.docx", b"docx bytes", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"markdown": "# Proof\n\nHello."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["backup_file"].endswith(".docx")
    assert (tmp_path / "docs" / "markdown" / body["markdown_file"]).exists()
    assert (tmp_path / "docs" / "backups" / body["backup_file"]).exists()


def test_api_publish_rejects_unsupported_extension(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "docs" / "markdown").mkdir(parents=True)
    (tmp_path / "docs" / "backups").mkdir(parents=True)

    import docs_to_markdown.mkdocs_publish as mkdocs_publish

    monkeypatch.setattr(mkdocs_publish, "MKDOCS_SITE_ROOT", tmp_path)

    response = client.post(
        "/api/publish",
        files={"file": ("notes.txt", b"data", "text/plain")},
        data={"markdown": "# Notes"},
    )

    assert response.status_code == 400
