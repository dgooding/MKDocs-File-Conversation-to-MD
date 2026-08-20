# Docs to Markdown

Convert DOCX and PDF documents into Markdown with a browser UI.

The app includes:
- A single-file converter with live preview and a Download Markdown button.
- A batch conversion page that returns a ZIP.
- A searchable MkDocs document library on the same port.
- A library converter page with drag-and-drop upload, preview, download, and publish.

## Quick Start (Windows, Beginner Friendly)

If you only want to run the app locally, follow these steps:

1. Install Python 3.12:
   https://www.python.org/downloads/
2. Install uv:
   https://docs.astral.sh/uv/getting-started/installation/
3. Download or clone this repository.
4. Double-click [LAUNCH.bat](LAUNCH.bat).

On Windows systems with [winget](https://learn.microsoft.com/windows/package-manager/winget/)
available, testers can run [INSTALL_AND_LAUNCH.ps1](INSTALL_AND_LAUNCH.ps1) instead. It
installs Python 3.12 and uv when missing, then runs [LAUNCH.bat](LAUNCH.bat), which installs
the project dependencies.

What happens when you run [LAUNCH.bat](LAUNCH.bat):
- It automatically creates or updates the local environment and installs every locked project dependency, including test and MkDocs dependencies.
- It opens your browser at http://127.0.0.1:8000/, the MkDocs document library home page.
- It starts the app server in the launcher window.
- The themed converter is available at http://127.0.0.1:8000/converter.
- The legacy standalone converter remains available at http://127.0.0.1:8000/app/converter.

To stop the app, close the launcher window or press `Ctrl+C` in that window.

## Use the App

Single-file page:
1. Open http://127.0.0.1:8000/converter.
2. Select a `.docx` or `.pdf` file.
3. Select Convert.
4. Review or edit the Markdown.
5. Select Download Markdown.

Batch page:
1. Open http://127.0.0.1:8000/batch.
2. Add multiple `.docx` and `.pdf` files.
3. Start batch conversion.
4. Download the ZIP file.

MkDocs document library:
1. Open http://127.0.0.1:8000/.
2. Select **Converter** in the left sidebar.
3. Drop a DOCX or PDF onto the upload area, or select it by clicking the area.
4. Select **Convert document**, then review the Markdown and preview.
5. Select **Upload to library** to publish the Markdown and original file.
6. Use the sidebar search to find the converted document or OCR text.

Each document is shown with its converted Markdown and matching original file. PDF files
open in the browser PDF viewer; DOCX files download because browsers do not render DOCX
directly. The separate `/mkdocs/backups/` route remains available for source-file browsing.

## Manual Local Run (Terminal)

If you prefer commands instead of [LAUNCH.bat](LAUNCH.bat):

```powershell
uv sync --locked --extra test --extra site --system-certs
uv run uvicorn docs_to_markdown.api:app --app-dir src --host 127.0.0.1 --port 8000
```

## Run Tests

```powershell
uv run --locked pytest -q
```

To validate the MkDocs site separately:

```powershell
uv run --extra site mkdocs build -f mkdocs-site\mkdocs.yml --strict
```

## Troubleshooting

### "uv" is not recognized
- Install uv, then run [LAUNCH.bat](LAUNCH.bat) again. The launcher installs the rest of the project dependencies automatically:
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

### The browser still shows an old page
- Stop the existing Uvicorn process and run [LAUNCH.bat](LAUNCH.bat) again.
- The application and MkDocs library share port 8000; no separate port 8001 is required.

### OCR quality
- Native PDF text is preferred when available.
- Local OCR uses RapidOCR with grayscale, contrast, upscaling, and sharpening preprocessing.
- Tesseract is optional and takes priority when installed and detected.
- Azure Document Intelligence is reserved as a future optional provider for Azure-hosted deployments.

## Project Boundaries

- DOCX conversion uses MarkItDown.
- PDF conversion uses native extraction with a MarkItDown fallback.
- Tesseract OCR is optional; when absent, the app uses the bundled `rapidocr-onnxruntime` engine automatically. Without either, DOCX and born-digital PDFs still work.
- This repository is for controlled tester evaluation. Do not commit real pilot documents, credentials, or generated conversion output.
- Uploaded documents and published library pages are local test data and are ignored by Git.
- Review documents for sensitive content before sharing them with testers or publishing the repository.