# Future enhancements

These ideas are intentionally deferred while the current library remains small and easy to use.

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