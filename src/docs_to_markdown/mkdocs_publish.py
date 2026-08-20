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
MKDOCS_OUTPUT_ROOT = MKDOCS_SITE_ROOT / "site"

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
    elif not index_path.read_text(encoding="utf-8").endswith("\n\n"):
        with index_path.open("a", encoding="utf-8") as handle:
            handle.write("\n" if index_path.read_bytes().endswith(b"\n") else "\n\n")
    with index_path.open("a", encoding="utf-8") as handle:
        handle.write(f"- [{label}]({target_name})\n")


def build_mkdocs_site(*, site_root: Path | None = None) -> None:
    """Build the searchable site when its optional MkDocs dependency is available."""
    root = site_root or MKDOCS_SITE_ROOT
    config_path = root / "mkdocs.yml"
    if not config_path.is_file():
        return

    from mkdocs.commands.build import build
    from mkdocs.config import load_config

    build(load_config(config_file=str(config_path)))


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
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    slug = f"{stem}-{timestamp}"

    markdown_name = f"{slug}.md"
    backup_name = f"{slug}{extension}"
    (markdown_dir / markdown_name).write_text(markdown, encoding="utf-8")
    (backups_dir / backup_name).write_bytes(content)

    _append_index_link(markdown_dir / "index.md", markdown_name, slug)
    _append_index_link(backups_dir / "index.md", backup_name, slug)

    return {"slug": slug, "markdown_file": markdown_name, "backup_file": backup_name}


def delete_published_documents(filenames: list[str], *, site_root: Path | None = None) -> int:
    """Delete selected library Markdown files and their matching original backups."""
    root = site_root or MKDOCS_SITE_ROOT
    markdown_dir = (root / "docs" / "markdown").resolve()
    backups_dir = (root / "docs" / "backups").resolve()
    removed = 0
    markdown_index = markdown_dir / "index.md"
    backups_index = backups_dir / "index.md"

    for filename in dict.fromkeys(filenames):
        source_path = Path(filename)
        if source_path.name != filename or source_path.suffix.lower() not in ({".md"} | _ALLOWED_EXTENSIONS) or source_path.stem == "index":
            raise ValueError("Only published document filenames can be deleted")
        slug = source_path.stem
        markdown_path = (markdown_dir / f"{slug}.md").resolve()
        if markdown_path.parent != markdown_dir:
            raise ValueError("Only published document filenames can be deleted")
        backup_candidates = [backup for backup in backups_dir.glob(f"{slug}.*") if backup.suffix.lower() in _ALLOWED_EXTENSIONS]
        if not markdown_path.is_file() and not backup_candidates:
            continue
        if markdown_path.is_file():
            markdown_path.unlink()
        for backup in backups_dir.glob(f"{slug}.*"):
            if backup.suffix.lower() in _ALLOWED_EXTENSIONS and backup.is_file():
                backup.unlink()
        _remove_index_link(markdown_index, f"{slug}.md")
        for extension in _ALLOWED_EXTENSIONS:
            _remove_index_link(backups_index, f"{slug}{extension}")
        removed += 1

    return removed


def _remove_index_link(index_path: Path, target_name: str) -> None:
    if not index_path.is_file():
        return
    lines = index_path.read_text(encoding="utf-8").splitlines()
    filtered = [line for line in lines if not re.search(rf"\]\({re.escape(target_name)}\)\s*$", line)]
    index_path.write_text("\n".join(filtered).rstrip() + "\n", encoding="utf-8")
