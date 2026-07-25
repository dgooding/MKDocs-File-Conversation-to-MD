# MkDocs File → Markdown

**Live web converter + MkDocs Material docs.**  
Drag-and-drop **PDF** (and Office/HTML/images) → Markdown with **images extracted**, **bold/italic/color** preserved, and **OCR** for scanned pages.

> Static hosts (GitHub Pages alone) cannot run conversion.  
> Deploy the **Docker** app on **Railway / Render / Fly** — see [DEPLOY.md](DEPLOY.md).

## Features

| Capability | How |
|------------|-----|
| Drag & drop UI | `/convert/` |
| PDF styles | PyMuPDF span flags + HTML color spans |
| Images | Extracted to `images/` and linked in MD |
| Scanned PDFs | Tesseract OCR (in Docker / when installed) |
| Structure pass | pymupdf4llm sidecar `.structure.md` |
| Office & more | Microsoft MarkItDown |
| MkDocs site | Material theme, glightbox for images |

## Quick start (local)

```powershell
cd ~\MKDocs-File-Conversation-to-MD
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m mkdocs build
python serve.py
```

- Site: http://127.0.0.1:8000/  
- Converter: http://127.0.0.1:8000/convert/  
- Health: http://127.0.0.1:8000/api/health  

## Production (Docker)

```bash
docker build -t mkdocs-file-to-md .
docker run --rm -p 8000:8000 mkdocs-file-to-md
```

The image installs **Tesseract, Poppler, ffmpeg, MarkItDown, PyMuPDF, pymupdf4llm**.

## Deploy publicly

See **[DEPLOY.md](DEPLOY.md)** for Railway, Render, Fly.io, and Hugging Face Spaces.

```powershell
# Railway (after winget install Railway.Railway)
railway login
railway up -y
railway domain
```

## Repo

https://github.com/dgooding/MKDocs-File-Conversation-to-MD

## License

MIT-style: free to use and modify for your docs workflows.
