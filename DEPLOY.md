# Deploy MkDocs File → Markdown (live converter)

This app is **not** static-only. It needs a host that runs **Docker + Python** so PDF conversion, OCR, and MarkItDown work.

## Recommended free / open hosts

| Platform | Why | Steps |
|----------|-----|--------|
| **[Railway](https://railway.com)** | Dockerfile deploy, public URL, easy | See below |
| **[Render](https://render.com)** | Free web service + Docker | Connect repo, use `render.yaml` |
| **[Fly.io](https://fly.io)** | Containers worldwide | `fly launch` + Dockerfile |
| **[Hugging Face Spaces](https://huggingface.co/spaces)** (Docker) | Public demo | New Space → Docker → push this repo |

GitHub Pages **cannot** run the converter (no server, no PyMuPDF/Tesseract).

---

## What the container includes

- Python 3.12 + FastAPI + Uvicorn  
- MkDocs Material (pre-built into `site/`)  
- **PyMuPDF** + **pymupdf4llm** (PDF text, styles, images, structure)  
- **Tesseract OCR** (scanned / image-only PDFs)  
- **Poppler** utilities  
- **MarkItDown** (DOCX, PPTX, XLSX, HTML, images, audio, …)  
- **Pillow**, fonts, ffmpeg  

---

## Deploy on Railway (recommended)

1. Create a free account at [railway.com](https://railway.com).
2. **New Project → Deploy from GitHub** (this repo) **or** install CLI and from this folder:

   ```powershell
   # Install CLI (Windows)
   winget install Railway.Railway
   # or: iwr https://railway.com/install.ps1 | iex

   cd ~\MKDocs-File-Conversation-to-MD
   railway login
   railway up -y
   railway domain
   ```

3. Open the generated URL → **`/convert/`** for drag-and-drop.

Health check: `https://YOUR-APP.up.railway.app/api/health`  
Engines: `https://YOUR-APP.up.railway.app/api/engines`

---

## Deploy on Render

1. Push this repo to GitHub.  
2. [Render Dashboard](https://dashboard.render.com) → **New → Blueprint** → select the repo (`render.yaml`).  
3. Or **New Web Service** → Docker → root Dockerfile → health path `/api/health`.

---

## Local production-style run (with Docker Desktop)

```powershell
docker build -t mkdocs-file-to-md .
docker run --rm -p 8000:8000 mkdocs-file-to-md
```

Open http://127.0.0.1:8000/convert/

Without Docker (dev):

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m mkdocs build
python serve.py
```

---

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Liveness + engine flags |
| GET | `/api/engines` | pymupdf / markitdown / tesseract status |
| POST | `/api/convert` | `multipart/form-data` field `file` |
| GET | `/convert/` | Drag-and-drop UI |

---

## Limits on free tiers

- Ephemeral disk: converted files may disappear on redeploy (add a volume on Railway/Render if you need persistence).  
- Cold starts / sleep on free plans.  
- Large PDFs: keep under ~80 MB (`MAX_UPLOAD_MB`).  
- OCR is slower than text extraction.
