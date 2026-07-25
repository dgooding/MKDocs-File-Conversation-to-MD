---
title: Convert files
description: Drag-and-drop PDF and document conversion to Markdown
---

# Convert files to Markdown

## Use the drag-and-drop UI

1. Start the all-in-one server:

   ```powershell
   python serve.py --build
   ```

2. Open **[http://127.0.0.1:8000/convert/](http://127.0.0.1:8000/convert/)**  
   (or click below if this site is served by `serve.py`)

<p>
  <a class="md-button md-button--primary" href="/convert/" target="_blank" rel="noopener">
    Open drag-and-drop converter
  </a>
</p>

3. Drop a **PDF** (best path) or another supported file.
4. Download the `.md` + `images/` zip, or leave files under `docs/converted/<slug>/`.
5. Optionally add a nav entry (the UI shows a ready-made line for `mkdocs.yml`).
6. Rebuild: `mkdocs build` or restart with `python serve.py --build`.

!!! warning "Static GitHub Pages cannot convert"
    Conversion needs a **running Python/Docker server** (`serve.py` or the production `Dockerfile`).

!!! tip "Public hosting"
    Deploy on **Railway**, **Render**, or **Fly.io** with the included Dockerfile so the converter has Tesseract, Poppler, and MarkItDown. Full steps: [DEPLOY.md](https://github.com/dgooding/MKDocs-File-Conversation-to-MD/blob/main/DEPLOY.md) in the repo.

---

## CLI (no browser)

```powershell
.\.venv\Scripts\Activate.ps1
python -m converter.cli path\to\file.pdf --out docs\converted\my-doc
```

Output:

```text
docs/converted/my-doc/
  my-doc.md
  images/
    p001_….png
    …
```

---

## Supported formats

| Format | Engine | Fidelity notes |
|--------|--------|----------------|
| **PDF** | Built-in PyMuPDF pipeline | Images + bold/italic/color/headings |
| DOCX, PPTX, XLSX, … | Optional `markitdown` | Install `pip install "markitdown[all]"` |
| TXT / MD / HTML / CSV | Text passthrough | Minimal wrapping |

---

## After conversion

| Step | Action |
|------|--------|
| Review | Open the raw preview or `mkdocs serve` |
| Images | Already linked as `images/…` relative to the `.md` file |
| Nav | Add under `nav:` → `Converted docs` in `mkdocs.yml` |
| Polish | Fix rare OCR-less text order issues on complex layouts |
