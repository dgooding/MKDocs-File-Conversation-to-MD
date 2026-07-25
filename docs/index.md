---
title: Home
hide:
  - toc
---

# MkDocs File → Markdown

All-in-one **MkDocs Material** site with a **drag-and-drop converter** that turns documents into Markdown ready for this knowledge base.

## PDF fidelity (primary focus)

When you convert a **PDF**, the engine:

| Feature | What you get |
|---------|----------------|
| **Images** | Extracted into `images/` next to the Markdown and linked with `![](...)` |
| **Bold / italic** | From PDF font flags → `<strong>` / `<em>` |
| **Colored text** | Non-black colors → `<span style="color:#rrggbb">` |
| **Monospace** | Courier-like fonts → `<code>` |
| **Headings** | Larger type sizes → `#` / `##` / … |
| **Pages** | Multi-page PDFs get “Page N” sections |

!!! tip "Open the converter"
    With the all-in-one server running, go to **[Convert files](convert.md)** or open **`/convert/`** for the full drag-and-drop UI.

<div class="grid cards" markdown>

-   :material-file-pdf-box:{ .lg .middle } **Convert**

    ---

    Drag & drop PDF (and other docs) to Markdown

    [:octicons-arrow-right-24: Converter](convert.md)

-   :material-cog:{ .lg .middle } **How it works**

    ---

    Pipeline, limits, and MkDocs wiring

    [:octicons-arrow-right-24: Details](how-it-works.md)

-   :material-folder-open:{ .lg .middle } **Converted**

    ---

    Output landing page under `docs/converted/`

    [:octicons-arrow-right-24: Converted docs](converted/index.md)

</div>

## Quick start

```powershell
cd ~\MKDocs-File-Conversation-to-MD
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Build docs + start API + converter UI
python serve.py --build
```

Then open:

- Site: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- Converter: [http://127.0.0.1:8000/convert/](http://127.0.0.1:8000/convert/)

## Honest limits

Markdown **cannot** be a pixel-perfect clone of every PDF (multi-column floats, vector art, forms). This project optimizes for **content fidelity** on MkDocs pages: typography signals, colors, and images in reading order.
