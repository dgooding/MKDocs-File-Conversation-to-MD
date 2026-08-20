# Future enhancements

These ideas are intentionally deferred while the current library remains small and easy to use.

<aside class="development-history-callout">
<strong>Development history</strong>
<p>See the chronological record of how the converter and library evolved.</p>
<a href="#development-history">Jump to the development history</a>
</aside>

## Larger libraries

- Add a library-only filter for narrowing documents by title without leaving the page.
- Show 25 documents per page, with clear previous and next controls.
- Sort newest documents first and expose readable titles, file types, and dates.
- Clarify whether bulk selection applies to the current page or the entire library.
- Add a stronger deletion summary before removing selected Markdown and source files.

## Performance

- Measure MkDocs rebuild time with 50, 100, and 250 documents.
- Move full-site rebuild work out of the request path if publishing becomes slow.
- Add coverage for large-library rendering, filtering, selection, deletion, and rebuild timing.

## OCR image search workaround

One important part of the current OCR work was making text inside embedded images searchable
without breaking the relationship between the OCR result and the image.

### Why the obvious approach failed

The first approach placed the OCR result in the image's Markdown `alt` text. That made the text
available in the raw Markdown, but it did not make it searchable in the generated MkDocs site.
The MkDocs search index reads visible text nodes from the rendered page; an HTML `alt` attribute
is metadata, not visible page text.

### The workaround

The converter now uses a temporary marker while it moves an image through the DOCX/PDF to
Markdown pipeline:

1. Run the configured OCR adapter against the embedded image or PDF image region.
2. Skip very small images, currently those below 40 pixels on their shortest side, to avoid
	turning icons and logos into noisy search results.
3. Preprocess the OCR copy by grayscaling, autocontrasting, upscaling, and sharpening it. The
	published image itself is left unchanged.
4. Record the OCR text and put a private marker in the image description so the result stays
	associated with the correct image while converters transform the document.
5. Replace that marker with an image followed by a Markdown footnote reference:

	The image becomes `![Image](image-source)[^ocr-1]`.

6. Append the OCR result as visible Markdown text at the end of the document:

	The footer contains `[^ocr-1]: OCR text: Text detected inside the image.`.

The footnote is the searchable part. The reference attached to the image is what keeps the OCR
result linked to the image it came from, even though the searchable text is rendered in the
document footer.

### Packaging and preview behavior

The converted image remains embedded in the generated Markdown, so the Markdown and its OCR
footnote travel together when a batch conversion is downloaded as a ZIP. There is no separate
OCR sidecar file that can become detached from the image. The live preview uses the same footnote
extension as the MkDocs site, so users see a rendered footnote rather than raw `[^ocr-1]` syntax.

This was verified by checking the generated MkDocs search index for OCR text from an image. It is
a deliberate compatibility workaround: visible Markdown text is used for search, while the
footnote reference preserves the image-to-OCR association.

### Suggested improvements

- **Keep the searchable footer, but make it quieter visually.** Render OCR text in a collapsible
	details block or a clearly labeled accessibility/search section so it remains indexed without
	overwhelming readers who only want the document body.
- **Move from data URIs to managed assets when documents grow.** Give each extracted image a stable
	filename and store it beside the Markdown in an `assets/` directory. Keep the footnote reference
	pointed at that asset and include the asset directory in every ZIP or published package.
- **Record confidence and provenance.** Store the OCR provider, page or image identifier, confidence
	when available, and a review-needed flag in structured manifest metadata rather than adding noisy
	diagnostics to the published Markdown.
- **Make OCR routing configurable.** Support local-only, automatic fallback, and explicit Azure
	Document Intelligence modes, with the current 40px threshold and provider choice exposed as
	documented settings.
- **Improve difficult-image handling.** Add measured deskew, rotation detection, region cropping,
	and layout-aware OCR for screenshots, diagrams, columns, and tables before attempting full-page
	OCR.
- **Avoid repeat work.** Cache OCR results by image content hash so repeated images, repeated
	conversions, and batch jobs do not invoke the OCR engine more than necessary.
- **Test the contract end to end.** Assert that the image reference, OCR footnote, ZIP contents,
	live preview, direct conversion, API conversion, and MkDocs search index all agree for the same
	image. Keep a human fidelity review for claims about reading quality.

## Optional Azure Document Intelligence reader

For scanned PDFs, photographed pages, and image-heavy documents, a future Azure Document
Intelligence reader could provide a managed OCR and layout-analysis option. It would be an
enhancement for difficult source material, not a replacement for the current local conversion
path.

### What a user would get

- A clearer reading of scanned pages, including printed text and supported handwritten text.
- Better preservation of page structure when the source contains columns, tables, or form-like
	layouts.
- Searchable Markdown when the original document has little or no extractable text.
- A conversion result that still includes the original source file for visual comparison.
- Diagnostics indicating which pages used Azure reading and whether the result needs review.

### Proposed conversion flow

1. Try native PDF or DOCX extraction first because it is local, fast, and avoids sending data to
	 an external service.
2. Detect pages with low text coverage, suspicious OCR output, or strong scan/image signals.
3. Use Azure Document Intelligence only when the provider is enabled and the page meets the
	 configured fallback threshold.
4. Merge the returned text and layout hints into the same Markdown output used by the local
	 converter.
5. Fall back to RapidOCR or the native converter if Azure is unavailable, disabled, or times out.

### Operating boundaries

- Keep the feature optional so local and offline conversion continues to work without Azure.
- Prefer Microsoft Entra managed identity in Azure-hosted deployments; use Key Vault-backed
	configuration where a secret is required.
- Do not place service keys in the browser, generated Markdown, or published document metadata.
- Make the Azure provider explicit in settings and diagnostics so users know when document data
	leaves the local machine.
- Add request timeouts, retry limits, file-size checks, and a clear error state before enabling it
	for production workloads.
- Document regional processing, retention, and estimated per-page costs before making it an
	automatic default.

See the [Azure Document Intelligence overview](https://learn.microsoft.com/azure/ai-services/document-intelligence/overview)
for the service background and supported analysis capabilities.

## Development history

This is the engineering handoff for the current implementation. It records the chronological
milestones, the controlling modules, the contracts that must not drift, and the evidence available
for the next engineer.

### Handoff status

| Area | Status | Owner / source of truth |
| --- | --- | --- |
| DOCX conversion | Implemented | `src/docs_to_markdown/converter.py` |
| PDF conversion | Implemented | `src/docs_to_markdown/pdf_converter.py` |
| OCR provider selection | Implemented, optional | `src/docs_to_markdown/ocr_adapter.py` |
| Browser conversion UI | Implemented | `src/docs_to_markdown/static/` and `mkdocs-site/docs/converter.md` |
| MkDocs publishing bridge | Implemented, local/test-oriented | `src/docs_to_markdown/mkdocs_publish.py` |
| Published document management | Implemented | `src/docs_to_markdown/api.py` and `mkdocs-site/docs/javascripts/manage-documents.js` |
| Large-library optimization | Deferred | This page, Larger libraries and Performance |
| Azure Document Intelligence | Deferred optional provider | This page, Optional Azure Document Intelligence reader |

### System topology

```text
Browser
	|
	v
FastAPI application (src/docs_to_markdown/api.py)
	|-- /api/convert ----------> DOCX/PDF converter -> Markdown
	|-- /api/render ----------- > Markdown renderer -> HTML preview
	|-- /api/publish ---------- > publish_to_mkdocs -> docs/markdown + docs/backups
	|-- /api/published/delete -> delete_published_documents -> rebuild
	|
	`-- /, /converter, /markdown, /future-enhancements
			 Static MkDocs output mounted from mkdocs-site/site

MkDocs build
	|-- docs/markdown/*.md ---- searchable converted documents
	|-- docs/backups/* -------- original DOCX/PDF files
	`-- search/search_index.json
```

The application is intentionally local and file-backed at this stage. Publishing is the explicit
exception to the otherwise stateless conversion path: it writes converted Markdown and original
files into the local `mkdocs-site` sandbox, then rebuilds the generated site.

### Chronological change record

#### Milestone 1: converter prototype and initial release

The first release combined a browser upload experience, DOCX/PDF-to-Markdown conversion, and a
themed MkDocs site. The baseline workflow was upload, convert, preview, and download.

**Established contracts:** DOCX and PDF are the supported input types; Markdown is the primary
output; the browser preview must represent the same conversion result that is downloadable.

#### Milestone 2: FastAPI application foundation

The converter was separated into an application entry point and format-specific modules. The
FastAPI layer became the HTTP boundary while converter modules remained the behavior-owning layer.

**Important boundary:** API routes validate inputs and translate failures into HTTP responses;
they should not grow a second conversion implementation. Direct conversion, API conversion, and
batch conversion should continue to call the same converter functions.

#### Milestone 3: tester onboarding and preview UX

The launcher, README, converter page, status messaging, and Markdown/preview workspace were
refined for Windows testers. The supported local path is `LAUNCH.bat` or the documented `uv`
command, with the themed converter and document library sharing port 8000.

#### Milestone 4: OCR adapter and image routing

OCR became an adapter contract with `extract_text(image) -> str | None`. Provider detection prefers
Tesseract and falls back to bundled RapidOCR. Both providers share preprocessing in
`ocr_adapter.py`: grayscale, autocontrast, 2x upscale, and sharpening.

Image OCR is deliberately selective. Images whose shortest dimension is below 40 pixels are
skipped to avoid indexing icons and logos. OCR failures return no text and must not break DOCX or
born-digital PDF conversion.

#### Milestone 5: searchable OCR footnotes

The initial OCR implementation placed text in image `alt` metadata. MkDocs search did not index
that metadata, so the implementation changed to visible Markdown footnotes:

```text
![Image](image-source)[^ocr-1]

[^ocr-1]: OCR text: Text detected inside the image.
```

In DOCX conversion, `converter.py` records OCR entries while Mammoth creates HTML, uses a private
marker to preserve image identity, then `_apply_ocr_footnotes()` converts markers into image-plus-
footnote references. In PDF conversion, `_ocr_markdown()` attaches the footnote reference to the
image block and appends the footnote definitions after page content.

The image remains embedded in the Markdown output. Therefore the image, its footnote reference,
and searchable OCR text remain in the same conversion artifact and survive batch ZIP packaging.
The Markdown renderer enables `mdit_py_plugins.footnote`, and MkDocs enables its `footnotes`
extension, keeping preview and published rendering aligned.

#### Milestone 6: lean project and offline constraints

Unneeded container/deployment artifacts were removed from the focused project path. Tester setup
was documented in `README.md`, `INSTALL_AND_LAUNCH.ps1`, and `LAUNCH.bat`.

The workstation's corporate proxy blocked the Tesseract binary download. That constraint drove the
RapidOCR fallback decision: it is pip-installable, bundles its model runtime, and preserves
offline/local operation. Do not make Tesseract or Azure a hard dependency for ordinary conversion.

#### Milestone 7: MkDocs publishing and paired source files

`publish_to_mkdocs()` creates a timestamped safe slug, writes the Markdown conversion under
`docs/markdown`, writes the original `.docx` or `.pdf` under `docs/backups`, and appends index
links. The API rebuilds MkDocs after publish and batch publish.

`delete_published_documents()` accepts a published Markdown filename or matching original backup
filename, validates that it is a flat allowed filename, removes both artifacts, removes their index
links, and triggers a rebuild through the API route.

**Safety invariants:** only `.md`, `.docx`, and `.pdf` published filenames are accepted; `index`
cannot be deleted; path traversal is rejected; duplicate filenames are de-duplicated per request.

#### Milestone 8: library UX and navigation validation

The Documents page evolved from a raw list into document rows with title, searchable-Markdown
metadata, Markdown/original-file actions, selection count, Select all/Clear all, and bulk deletion.
The management behavior is client-side over the generated MkDocs list and calls
`POST /api/published/delete` for mutation.

Navigation was tested through the browser. Root-level mounts were added for generated content so
Home, Converter, Documents, and Future enhancements work from both `/` and `/mkdocs/`. The batch
route remains available from workflow links but is intentionally absent from the primary sidebar.

### Current runtime contracts

**Conversion:** `POST /api/convert` accepts one DOCX/PDF upload and returns `filename` plus
`markdown`. Empty files are rejected; unsupported extensions return 415; conversion failures
return 422.

**Preview:** `POST /api/render` accepts `{ "markdown": "..." }` and returns rendered HTML. The
footnote plugin is part of the renderer contract.

**Publish:** `POST /api/publish` accepts the original file and Markdown form field, persists paired
artifacts, rebuilds MkDocs, and returns the generated slug and filenames.

**Delete:** `POST /api/published/delete` accepts `{ "filenames": ["..."] }`. Empty selections
return 400. Successful deletion returns `{ "removed": n }`.

**Batch:** the standalone `/batch` page supports up to 25 files and 100 MB total input. It returns
a ZIP containing converted Markdown and a manifest; batch publishing uses the same converter and
publishing primitives.

### Validation evidence

- Focused regression suite: `27 passed` for `tests/test_mkdocs_publish.py` and `tests/test_api.py`.
- MkDocs build: `python -m mkdocs build -f mkdocs-site/mkdocs.yml --clean` succeeds.
- Browser checks: Home, Converter, Documents, Future enhancements, in-page anchors, publishing
	management controls, and the Azure reference were exercised.
- OCR search proof: OCR text was verified in the generated MkDocs `search/search_index.json`.
- Latest pushed checkpoint: `e5d9ae4`, **Improve library navigation and OCR documentation**.

### Known risks and deferred work

- MkDocs rebuilds synchronously after publishing and deletion; latency should be measured before
	scaling beyond the current small library.
- The library renders all document rows at once and has no title filter, pagination, or sorting.
- Embedded image data URIs make large packages heavier; managed assets are a future change.
- OCR quality remains source-dependent and requires human fidelity review for high-stakes claims.
- Azure Document Intelligence is not implemented; any future provider must remain optional, explicit,
	identity-protected, timeout-bounded, and cost-documented.

### Resume checklist

1. Read `AGENTS.md` before editing; complete one approved checkpoint at a time.
2. Preserve one authoritative converter per format and direct/API/batch parity.
3. Run the focused tests before widening validation.
4. Rebuild MkDocs after documentation or generated-site changes.
5. Treat OCR searchability and visual fidelity as separate acceptance criteria.
6. Do not commit pilot documents, credentials, or generated conversion output.