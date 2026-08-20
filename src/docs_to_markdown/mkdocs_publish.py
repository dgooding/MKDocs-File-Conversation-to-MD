"""Test-only bridge that publishes conversions into the local mkdocs-site/ search sandbox.

This intentionally breaks the app's stateless/no-persistence design and exists solely to
validate MkDocs full-text search against OCR'd Markdown output during the pilot. To fully
retract this feature: delete this module, the `/api/publish` route in api.py, the
"Publish to search site" UI in static/index.html + app.js, and the mkdocs-site/ folder.
"""

import re
from datetime import datetime, timezone
from pathlib import Path

MKDOCS_SITE_ROOT = Path(__file__).resolve().parents[2] / "mkdocs-site"

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")
_ALLOWED_EXTENSIONS = {".docx", ".pdf"}


def _safe_stem(filename: str) -> str:
    stem = Path(filename).stem or "document"
    cleaned = _UNSAFE_CHARS.sub("_", stem).strip("._") or "document"
    return cleaned[:80]


def _append_index_link(index_path: Path, target_name: str, label: str) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    if not index_path.exists():
        index_path.write_text("# Published\n\n", encoding="utf-8")
    with index_path.open("a", encoding="utf-8") as handle:
        handle.write(f"- [{label}]({target_name})\n")


def publish_to_mkdocs(filename: str, content: bytes, markdown: str, *, site_root: Path | None = None) -> dict[str, str]:
    """Write the converted Markdown and the original file into the search sandbox."""
    root = site_root or MKDOCS_SITE_ROOT
    if not root.is_dir():
        raise FileNotFoundError("mkdocs-site is not present; publish is unavailable")

    extension = Path(filename).suffix.lower()
    if extension not in _ALLOWED_EXTENSIONS:
        raise ValueError("Only DOCX and PDF backups can be published")
    if not content or not markdown.strip():
        raise ValueError("Both the original file and converted Markdown are required")

    markdown_dir = root / "docs" / "markdown"
    backups_dir = root / "docs" / "backups"
    markdown_dir.mkdir(parents=True, exist_ok=True)
    backups_dir.mkdir(parents=True, exist_ok=True)

    stem = _safe_stem(filename)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = f"{stem}-{timestamp}"

    markdown_name = f"{slug}.md"
    backup_name = f"{slug}{extension}"
    (markdown_dir / markdown_name).write_text(markdown, encoding="utf-8")
    (backups_dir / backup_name).write_bytes(content)

    _append_index_link(markdown_dir / "index.md", markdown_name, slug)
    _append_index_link(backups_dir / "index.md", backup_name, slug)

    return {"slug": slug, "markdown_file": markdown_name, "backup_file": backup_name}
