"""
All-in-one MkDocs + conversion API (production-ready for Railway/Render/Fly).

- Serves MkDocs Material site (built into site/)
- POST /api/convert — drag-drop uploads
- Multi-engine PDF path: styles + images + OCR + pymupdf4llm + MarkItDown
"""

from __future__ import annotations

import os
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CONVERTED = DOCS / "converted"
ASSETS_CONVERTED = DOCS / "assets" / "converted"
UPLOADS = ROOT / ".uploads"
SITE = ROOT / "site"

sys.path.insert(0, str(ROOT))

from converter.engines import convert_upload, engine_status  # noqa: E402
from converter.pdf_to_md import slugify  # noqa: E402

SUPPORTED = {
    ".pdf",
    ".docx",
    ".pptx",
    ".xlsx",
    ".xls",
    ".html",
    ".htm",
    ".csv",
    ".txt",
    ".md",
    ".json",
    ".xml",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".wav",
    ".mp3",
}

app = FastAPI(
    title="MkDocs File → Markdown Converter",
    description="Drag-and-drop conversion with high-fidelity PDF support for MkDocs",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for d in (CONVERTED, ASSETS_CONVERTED, UPLOADS):
    d.mkdir(parents=True, exist_ok=True)


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "mkdocs-file-to-md",
        "version": "1.1.0",
        "engines": engine_status(),
    }


@app.get("/api/engines")
def engines() -> dict[str, Any]:
    return engine_status()


@app.get("/api/conversions")
def list_conversions() -> dict[str, Any]:
    items = []
    if CONVERTED.exists():
        for p in sorted(CONVERTED.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if p.is_dir() and (p / f"{p.name}.md").exists():
                md = p / f"{p.name}.md"
                imgs = p / "images"
                items.append(
                    {
                        "slug": p.name,
                        "title": p.name.replace("-", " "),
                        "markdown_url": f"/converted/{p.name}/{p.name}.md",
                        "site_path": f"converted/{p.name}/{p.name}.md",
                        "image_count": len(list(imgs.glob("*"))) if imgs.exists() else 0,
                        "modified": datetime.fromtimestamp(
                            md.stat().st_mtime, tz=timezone.utc
                        ).isoformat(),
                    }
                )
    return {"conversions": items}


@app.post("/api/convert")
async def convert(file: UploadFile = File(...)) -> JSONResponse:
    if not file.filename:
        raise HTTPException(400, "Missing filename")

    original = Path(file.filename).name
    ext = Path(original).suffix.lower()
    if ext not in SUPPORTED:
        raise HTTPException(
            400,
            f"Unsupported type '{ext}'. Supported: {', '.join(sorted(SUPPORTED))}",
        )

    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    max_mb = int(os.environ.get("MAX_UPLOAD_MB", "80"))
    if len(data) > max_mb * 1024 * 1024:
        raise HTTPException(400, f"File too large (max {max_mb} MB)")

    slug = f"{slugify(Path(original).stem)}-{_stamp()}"
    out_dir = CONVERTED / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = convert_upload(data, original, out_dir, doc_slug=slug)

        # Mirror images into assets for optional absolute paths
        img_src = out_dir / "images"
        if img_src.exists() and any(img_src.iterdir()):
            dest_assets = ASSETS_CONVERTED / slug
            if dest_assets.exists():
                shutil.rmtree(dest_assets)
            shutil.copytree(img_src, dest_assets)

        title = result.get("title") or Path(original).stem
        payload = {
            "ok": True,
            "mode": result.get("mode", "converted"),
            "engines": result.get("engines", []),
            "slug": slug,
            "title": title,
            "source": original,
            "page_count": result.get("page_count", 1),
            "image_count": result.get("image_count", 0),
            "markdown_path": f"docs/converted/{slug}/{slug}.md",
            "images_path": f"docs/converted/{slug}/images/",
            "preview_url": f"/api/preview/{slug}",
            "download_md_url": f"/api/download/{slug}/md",
            "download_zip_url": f"/api/download/{slug}/zip",
            "mkdocs_nav_hint": f"      - {title}: converted/{slug}/{slug}.md",
            "preview": (result.get("markdown_preview") or "")[:2500],
            "tesseract": result.get("tesseract"),
        }
        return JSONResponse(payload)
    except HTTPException:
        raise
    except Exception as exc:
        shutil.rmtree(out_dir, ignore_errors=True)
        raise HTTPException(500, f"Conversion failed: {exc}") from exc


@app.get("/api/preview/{slug}")
def preview(slug: str) -> HTMLResponse:
    md_path = CONVERTED / slug / f"{slug}.md"
    if not md_path.is_file():
        raise HTTPException(404, "Conversion not found")
    text = md_path.read_text(encoding="utf-8")
    body = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>Preview — {slug}</title>"
        "<style>body{font-family:system-ui,Segoe UI,sans-serif;max-width:900px;"
        "margin:2rem auto;padding:0 1rem;line-height:1.5}"
        "pre{white-space:pre-wrap;background:#f6f8fa;padding:1rem;border-radius:8px}"
        "img{max-width:100%}</style></head><body>"
        f"<p><a href='/convert/'>← Back to converter</a> · "
        f"<a href='/api/download/{slug}/md'>Download .md</a> · "
        f"<a href='/api/download/{slug}/zip'>Download zip</a></p>"
        f"<h1>Raw Markdown preview</h1><pre>{_html_escape(text)}</pre>"
        "</body></html>"
    )
    return HTMLResponse(body)


def _html_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


@app.get("/api/download/{slug}/md")
def download_md(slug: str) -> FileResponse:
    md_path = CONVERTED / slug / f"{slug}.md"
    if not md_path.is_file():
        raise HTTPException(404, "Not found")
    return FileResponse(md_path, filename=f"{slug}.md", media_type="text/markdown")


@app.get("/api/download/{slug}/zip")
def download_zip(slug: str) -> FileResponse:
    folder = CONVERTED / slug
    if not folder.is_dir():
        raise HTTPException(404, "Not found")
    zip_path = UPLOADS / f"{slug}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in folder.rglob("*"):
            if f.is_file():
                zf.write(f, arcname=str(f.relative_to(folder)))
    return FileResponse(zip_path, filename=f"{slug}.zip", media_type="application/zip")


if CONVERTED.exists():
    app.mount("/converted", StaticFiles(directory=str(CONVERTED), html=False), name="converted")


@app.get("/convert/", response_class=HTMLResponse)
@app.get("/convert", response_class=HTMLResponse)
def convert_ui() -> HTMLResponse:
    ui = (ROOT / "app" / "static" / "convert.html").read_text(encoding="utf-8")
    return HTMLResponse(ui)


# Built MkDocs site (Dockerfile runs mkdocs build)
if SITE.exists() and (SITE / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(SITE), html=True), name="site")
else:

    @app.get("/", response_class=HTMLResponse)
    def root() -> HTMLResponse:
        return HTMLResponse(
            """
            <!DOCTYPE html><html><head><meta charset="utf-8">
            <title>MkDocs File → MD</title>
            <style>body{font-family:system-ui;max-width:40rem;margin:3rem auto;padding:0 1rem}
            a.btn{display:inline-block;background:#4051b5;color:#fff;padding:.75rem 1.25rem;
            border-radius:8px;text-decoration:none;font-weight:600}</style></head>
            <body>
            <h1>MkDocs File → Markdown</h1>
            <p>Docs site not built yet. Converter is available.</p>
            <p><a class="btn" href="/convert/">Open drag-and-drop converter</a></p>
            <p>API: <a href="/api/health">/api/health</a> · <a href="/api/engines">/api/engines</a></p>
            </body></html>
            """
        )
