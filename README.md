# Docs to Markdown

Convert DOCX and PDF documents to Markdown in a local browser interface. The app supports a single-document page with an editable Markdown preview and download button, plus a batch-conversion page.

## Try it in GitHub Codespaces

1. Select **Code**, then **Create codespace on main**.
2. Wait for the environment setup to finish.
3. Run:

   ```sh
   uv run uvicorn docs_to_markdown.api:app --app-dir src --host 0.0.0.0 --port 8000
   ```

4. Open the forwarded port `8000` in the browser.
5. Upload a DOCX or PDF, review the Markdown preview, and select **Download Markdown**.

Do not upload confidential documents to a public Codespace or public issue.

## Run locally

Prerequisites: Python 3.12 and [uv](https://docs.astral.sh/uv/).

```powershell
uv sync --extra test
.\LAUNCH.bat
```

Or start the application directly:

```powershell
uv run uvicorn docs_to_markdown.api:app --app-dir src --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`. Stop the application with `Ctrl+C`.

## Test

```powershell
uv run pytest -q
```

## Boundaries

- DOCX conversion uses MarkItDown.
- PDF conversion uses native extraction with a MarkItDown fallback.
- Tesseract OCR is optional. Its absence does not prevent DOCX or born-digital PDF conversion.
- This repository is intended for controlled tester evaluation. Do not commit real pilot documents, credentials, or generated conversion output.