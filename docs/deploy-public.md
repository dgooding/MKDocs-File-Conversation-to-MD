---
title: Deploy the live converter
---

# Deploy a live converter (public website)

GitHub Pages only serves static HTML. **Conversion needs a container host.**

## Best free options

1. **[Railway](https://railway.com)** — Dockerfile in this repo  
2. **[Render](https://render.com)** — `render.yaml` blueprint  
3. **[Fly.io](https://fly.io)** — `fly launch`  
4. **Hugging Face Spaces (Docker)** — public demo URL  

## What the public server includes

- Tesseract OCR  
- Poppler  
- PyMuPDF + pymupdf4llm  
- MarkItDown (Office, images, …)  
- FastAPI + MkDocs UI  

## Railway (fastest)

```powershell
# Install Railway CLI, then:
cd ~\MKDocs-File-Conversation-to-MD
railway login
railway up -y
railway domain
```

Open `https://<your-app>.up.railway.app/convert/`

## After deploy

| URL | Purpose |
|-----|---------|
| `/` | MkDocs docs |
| `/convert/` | Drag-and-drop |
| `/api/health` | Health + engines |
| `/api/engines` | Dependency status |

Full guide: see `DEPLOY.md` in the repository root.
