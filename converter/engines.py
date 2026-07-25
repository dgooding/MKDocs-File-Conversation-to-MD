"""
Multi-engine conversion orchestration for maximum fidelity.

Engines (best → fallback):
  1. styled  — custom PyMuPDF (colors, bold, images, headings)
  2. ocr     — Tesseract via PyMuPDF for image-only / sparse pages
  3. llm_md  — pymupdf4llm structured Markdown
  4. markitdown — Microsoft MarkItDown for Office + extra formats
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .pdf_to_md import convert_bytes_pdf, convert_pdf_to_markdown, slugify


def tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def convert_pdf_best_effort(
    pdf_path: Path,
    output_dir: Path,
    *,
    doc_slug: str | None = None,
    title: str | None = None,
    use_ocr: bool = True,
) -> dict[str, Any]:
    """
    Convert PDF with styled engine + OCR backfill + optional pymupdf4llm supplement.
    """
    import fitz

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = doc_slug or slugify(pdf_path.stem)

    # 1) Primary high-fidelity styled extraction (images + formatting)
    result = convert_pdf_to_markdown(
        pdf_path,
        output_dir,
        doc_slug=slug,
        title=title,
        images_subdir="images",
        page_break_markers=True,
        use_ocr=use_ocr and tesseract_available(),
    )
    engines_used = ["styled-pymupdf"]
    if use_ocr and tesseract_available():
        engines_used.append("tesseract-ocr")

    # 2) If almost no text, force full OCR pass and re-merge
    md_path = Path(result["markdown_path"])
    body = md_path.read_text(encoding="utf-8") if md_path.is_file() else ""
    textish = _strip_front_matter(body)
    if len(textish.strip()) < 80 and tesseract_available():
        ocr_md = _ocr_whole_pdf(pdf_path)
        if ocr_md.strip():
            images_note = ""
            imgs = output_dir / "images"
            if imgs.exists() and any(imgs.iterdir()):
                images_note = "\n\n## Extracted images\n\n" + "\n".join(
                    f"![image](images/{p.name})" for p in sorted(imgs.iterdir()) if p.is_file()
                )
            md_path.write_text(
                _wrap_frontmatter(
                    title or pdf_path.stem,
                    pdf_path.name,
                    ocr_md + images_note,
                    extra_tags=["ocr"],
                ),
                encoding="utf-8",
            )
            result["markdown_preview"] = md_path.read_text(encoding="utf-8")[:4000]
            engines_used.append("full-page-ocr")

    # 3) Append pymupdf4llm alternate section when it adds meaningful structure
    try:
        import pymupdf4llm

        llm_md = pymupdf4llm.to_markdown(
            str(pdf_path),
            write_images=False,
            page_chunks=False,
        )
        if isinstance(llm_md, str) and len(llm_md.strip()) > 100:
            # Keep primary body; store alternate for reference file
            alt = output_dir / f"{slug}.structure.md"
            alt.write_text(
                _wrap_frontmatter(
                    f"{title or pdf_path.stem} (structure pass)",
                    pdf_path.name,
                    llm_md,
                    extra_tags=["pymupdf4llm"],
                ),
                encoding="utf-8",
            )
            result["structure_md"] = str(alt)
            engines_used.append("pymupdf4llm")
    except Exception:
        pass

    result["engines"] = engines_used
    result["tesseract"] = tesseract_available()
    # Re-count images
    img_dir = output_dir / "images"
    if img_dir.exists():
        result["image_count"] = len([p for p in img_dir.iterdir() if p.is_file()])
    return result


def convert_upload(
    data: bytes,
    filename: str,
    output_dir: Path,
    *,
    doc_slug: str | None = None,
) -> dict[str, Any]:
    """Route by extension: PDF multi-engine, else MarkItDown."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(filename).suffix.lower()
    slug = doc_slug or slugify(Path(filename).stem)
    title = Path(filename).stem.replace("-", " ").replace("_", " ")

    if ext == ".pdf":
        safe = slugify(Path(filename).stem) + ".pdf"
        tmp = output_dir / safe
        tmp.write_bytes(data)
        try:
            result = convert_pdf_best_effort(
                tmp,
                output_dir,
                doc_slug=slug,
                title=title,
                use_ocr=True,
            )
            # Fix source name in front matter
            md_path = Path(result["markdown_path"])
            if md_path.is_file():
                text = md_path.read_text(encoding="utf-8")
                text = text.replace(f"Converted from {safe}", f"Converted from {Path(filename).name}")
                text = text.replace(f"Source: `{safe}`", f"Source: `{Path(filename).name}`")
                md_path.write_text(text, encoding="utf-8")
                result["markdown_preview"] = text[:4000]
        finally:
            tmp.unlink(missing_ok=True)
        result["mode"] = "pdf-multi-engine"
        result["source_filename"] = filename
        return result

    # Office / web / text via MarkItDown
    src = output_dir / f"_src_{slug}{ext}"
    src.write_bytes(data)
    out_md = output_dir / f"{slug}.md"
    try:
        ok = _markitdown_convert(src, out_md, title=title)
        if not ok and ext in {".txt", ".md", ".csv", ".html", ".htm"}:
            text = data.decode("utf-8", errors="replace")
            out_md.write_text(
                _wrap_frontmatter(title, filename, text, extra_tags=["text"]),
                encoding="utf-8",
            )
            ok = True
        if not ok:
            raise RuntimeError(
                "Could not convert this file. For Office formats the container "
                "includes markitdown; ensure the file is not password-protected."
            )
        return {
            "mode": "markitdown",
            "slug": slug,
            "title": title,
            "source_filename": filename,
            "markdown_path": str(out_md.resolve()),
            "markdown_rel": out_md.name,
            "images_dir": str((output_dir / "images").resolve()),
            "image_count": 0,
            "page_count": 1,
            "image_paths": [],
            "markdown_preview": out_md.read_text(encoding="utf-8")[:4000],
            "engines": ["markitdown"],
            "tesseract": tesseract_available(),
        }
    finally:
        src.unlink(missing_ok=True)


def _markitdown_convert(src: Path, out_md: Path, title: str) -> bool:
    try:
        from markitdown import MarkItDown
    except ImportError:
        return False
    md = MarkItDown()
    result = md.convert(str(src))
    text = (result.text_content or "").strip()
    if not text:
        return False
    out_md.write_text(
        _wrap_frontmatter(title, src.name, text, extra_tags=["markitdown"]),
        encoding="utf-8",
    )
    return True


def _ocr_whole_pdf(pdf_path: Path) -> str:
    import fitz

    doc = fitz.open(pdf_path)
    parts: list[str] = []
    try:
        for i, page in enumerate(doc):
            try:
                tp = page.get_textpage_ocr(flags=0, language="eng", dpi=200)
                text = page.get_text(textpage=tp) or ""
            except Exception:
                text = page.get_text("text") or ""
            text = text.strip()
            if text:
                parts.append(f"### Page {i + 1}\n\n{text}")
    finally:
        doc.close()
    return "\n\n".join(parts)


def _strip_front_matter(md: str) -> str:
    if not md.startswith("---"):
        return md
    end = md.find("\n---", 3)
    if end == -1:
        return md
    return md[end + 4 :]


def _wrap_frontmatter(title: str, source: str, body: str, extra_tags: list[str] | None = None) -> str:
    tags = ["converted"] + (extra_tags or [])
    tag_lines = "\n".join(f"  - {t}" for t in tags)
    safe_title = title.replace('"', "'")
    return (
        f"---\n"
        f'title: "{safe_title}"\n'
        f'description: "Converted from {source}"\n'
        f"tags:\n{tag_lines}\n"
        f"---\n\n"
        f"# {safe_title}\n\n"
        f'!!! info "Conversion metadata"\n'
        f"    Source: `{source}`\n\n"
        f"---\n\n"
        f"{body.strip()}\n"
    )


def engine_status() -> dict[str, Any]:
    status: dict[str, Any] = {
        "pymupdf": False,
        "pymupdf4llm": False,
        "markitdown": False,
        "tesseract": tesseract_available(),
        "tesseract_path": shutil.which("tesseract"),
    }
    try:
        import fitz  # noqa: F401

        status["pymupdf"] = True
        status["pymupdf_version"] = getattr(__import__("fitz"), "VersionBind", "ok")
    except Exception as e:
        status["pymupdf_error"] = str(e)
    try:
        import pymupdf4llm  # noqa: F401

        status["pymupdf4llm"] = True
    except Exception:
        pass
    try:
        import markitdown  # noqa: F401

        status["markitdown"] = True
    except Exception:
        pass
    return status
