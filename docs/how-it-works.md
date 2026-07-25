---
title: How it works
---

# How conversion works

## Architecture

```text
Browser drag-and-drop  →  FastAPI POST /api/convert
                                │
                                ▼
                     PDF? ──yes──► PyMuPDF high-fidelity engine
                                │     • text dict (fonts, flags, colors)
                                │     • extract embedded images
                                │     • reading-order merge
                                │     • write Markdown + images/
                                ▼
                     docs/converted/<slug>/<slug>.md
                     docs/converted/<slug>/images/*
                                │
                                ▼
                     MkDocs Material builds / serves pages
```

`serve.py` runs **Uvicorn** with `app.main:app`, which:

- Exposes the converter UI at `/convert/`
- Writes into `docs/converted/`
- Serves the built MkDocs `site/` when present

## PDF pipeline details

### Text & formatting

Each page is read with PyMuPDF `get_text("dict")`. Every **span** carries:

- Font size → heading level vs median body size  
- Flags → bold / italic / mono  
- RGB color → HTML span when not near black/white  
- Font name → extra bold/italic/mono heuristics  

Spans are serialized as HTML inline tags so **MkDocs Material** can show color and weight (standard Markdown has no color syntax).

### Images

Embedded images are pulled via `extract_image`, saved as:

```text
images/p001_<xref>_<hash>.png
```

Markdown:

```markdown
![Page 1 image](images/p001_....png){ loading=lazy }
```

`mkdocs-glightbox` enables click-to-zoom on the built site.

### Reading order

Text blocks and images are sorted by vertical position (then horizontal) so figures land near the surrounding copy when the PDF’s structure allows it.

## Project layout

```text
MKDocs-File-Conversation-to-MD/
  app/
    main.py              # FastAPI API + static convert UI
    static/convert.html  # Drag-and-drop page
  converter/
    pdf_to_md.py         # High-fidelity PDF engine
    cli.py               # Command-line entry
  docs/                  # MkDocs content
  docs/converted/        # Conversion output (gitignored contents)
  mkdocs.yml
  serve.py
  requirements.txt
```

## Why not “100% identical to the PDF”?

| PDF feature | Markdown reality |
|-------------|------------------|
| Fixed page coordinates | Flow layout only |
| Multi-column / text boxes | Best-effort Y/X sort |
| Vector logos / drawings | Not always images |
| Scanned pages (image-only) | Need OCR (not enabled by default) |
| Exact fonts | Browser / theme fonts |

The goal is a **faithful MkDocs article**, not a PDF viewer.

## Optional: MarkItDown for Office files

```powershell
pip install "markitdown[all]"
```

Non-PDF uploads then use MarkItDown when available.
