# Project Working Rules

## Execution

- Complete exactly one approved checkpoint at a time.
- Before editing, state the checkpoint purpose, expected files, and focused validation.
- After validation, report results and stop for approval before starting the next checkpoint.
- Prefer the smallest functional implementation. Do not add styling, abstractions, formats, deployment, or batch behavior early.
- Do not start builds, watchers, or servers unless the current checkpoint requires them. Stop them when requested.

## Conversion Architecture

- Keep one authoritative conversion function per format. APIs, CLIs, batch jobs, and UIs must call the same function.
- Add exact direct/API parity tests for Markdown and later for assets and quality metadata.
- Keep conversion diagnostics out of published Markdown. Put them in structured metadata when that checkpoint is approved.
- Treat optional converters and OCR providers as adapters. A missing optional provider must not break unrelated formats.
- Prefer native semantic extraction. Use targeted OCR or region fallback only when measured quality is weak; use full-page visual fallback last.

## Quality Gates

- Separate technical success from fidelity. A successful conversion does not prove that content matches the source.
- Use structural assertions instead of whole-file snapshots where generated document metadata is volatile.
- Do not call automated ratings human review. Fidelity claims require a person to compare source and output.
- The historical pilot corpus and evaluation artifacts are outside the lean project backup; restore them only when a future fidelity review is explicitly approved.

## Current Boundaries

- MarkItDown is the validated DOCX engine.
- pdfplumber and pypdfium2 own native PDF extraction; MarkItDown is the PDF fallback.
- Tesseract is an optional OCR adapter. Its absence must not break DOCX or born-digital PDF conversion.
- The removed evaluation, Marker, MkDocs, and checkpoint artifacts are preserved at `C:\MKDocsbackup\Docs-to-MK-safe-lean-20260817-203034`.

## Validation Commands

- Sync: `.\.tools\uv\uv.exe sync --extra test --python .\.venv\Scripts\python.exe`
- Focused tests: `.\.tools\uv\uv.exe run --python .\.venv\Scripts\python.exe pytest -q tests\test_converter.py tests\test_api.py tests\test_docx_fidelity.py tests\test_pdf_fidelity.py tests\test_pdf_scanned.py tests\test_batch.py tests\test_container.py`