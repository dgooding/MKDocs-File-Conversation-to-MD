# Docs to Markdown

Convert DOCX and PDF documents into Markdown with a browser UI.

The app includes:
- A single-file converter with live preview and a Download Markdown button.
- A batch conversion page that returns a ZIP.

## Quick Start (Windows, Beginner Friendly)

If you only want to run the app locally, follow these steps:

1. Install Python 3.12:
   https://www.python.org/downloads/
2. Install uv:
   https://docs.astral.sh/uv/getting-started/installation/
3. Download or clone this repository.
4. Double-click [LAUNCH.bat](LAUNCH.bat).

What happens when you run [LAUNCH.bat](LAUNCH.bat):
- On first run, it automatically creates the local environment and installs dependencies.
- It opens your browser at http://127.0.0.1:8000/.
- It starts the app server in the launcher window.

To stop the app, close the launcher window or press `Ctrl+C` in that window.

## Use the App

Single-file page:
1. Open http://127.0.0.1:8000/.
2. Select a `.docx` or `.pdf` file.
3. Select Convert.
4. Review or edit the Markdown.
5. Select Download Markdown.

Batch page:
1. Open http://127.0.0.1:8000/batch.
2. Add multiple `.docx` and `.pdf` files.
3. Start batch conversion.
4. Download the ZIP file.

## Run in GitHub Codespaces

Use this when you do not want to install Python locally.

1. Select **Code** in GitHub.
2. Select **Create codespace on main**.
3. Wait for setup to complete.
4. Run:

   ```sh
   uv run uvicorn docs_to_markdown.api:app --app-dir src --host 0.0.0.0 --port 8000
   ```

5. Open forwarded port `8000`.

Do not upload confidential documents to a public Codespace.

## Manual Local Run (Terminal)

If you prefer commands instead of [LAUNCH.bat](LAUNCH.bat):

```powershell
uv sync --extra test
uv run uvicorn docs_to_markdown.api:app --app-dir src --host 127.0.0.1 --port 8000
```

## Run Tests

```powershell
uv run pytest -q
```

## Troubleshooting

### "uv" is not recognized
- Install uv, then restart your terminal:
  https://docs.astral.sh/uv/getting-started/installation/

### Python version errors
- This project requires Python 3.12.
- Check with:

  ```powershell
  python --version
  ```

### Port 8000 already in use
- Stop the process using port 8000, then start the launcher again.

### Conversion failed for a file
- Confirm the file extension is `.docx` or `.pdf`.
- Retry with a small sample document.

## Project Boundaries

- DOCX conversion uses MarkItDown.
- PDF conversion uses native extraction with a MarkItDown fallback.
- Tesseract OCR is optional. Without it, DOCX and born-digital PDFs still work.
- This repository is for controlled tester evaluation. Do not commit real pilot documents, credentials, or generated conversion output.