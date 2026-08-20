# Cool Ass MkDocs page

This is a future-facing product and design brief for a genuinely excellent IT documentation
experience. It is intentionally aspirational: the current library remains the baseline, while
this page describes what a progressive documentation system should feel like for the people who
use and maintain it.

## Product intent

The page should feel like an operational tool, not a folder full of converted files. An IT reader
should be able to find an answer, understand its confidence and age, compare it with the source,
and take the next safe action without losing context.

The experience should be:

- **Fast:** the answer and the relevant document appear quickly.
- **Calm:** dense information is organized for scanning instead of decorated for its own sake.
- **Traceable:** every converted document can be related back to its original source and conversion
  details.
- **Searchable:** native text, OCR text, titles, metadata, and code examples are discoverable.
- **Honest:** stale, low-confidence, or review-required content is visibly labeled.
- **Progressive:** the interface improves the workflow without forcing users to learn a new system.

## Information architecture

### Home: operations dashboard

The home page should answer three questions immediately:

1. What documents are available?
2. What changed recently?
3. What can I do next?

Suggested regions:

- A prominent search field with recent searches and useful suggestions.
- Recently added or recently updated documents.
- Review-required documents, such as low-confidence OCR results.
- Quick actions for converting a file, browsing the library, or comparing a source.
- A small system status strip showing converter availability, OCR provider, and last site build.

### Documents: a real library

The document library should support filtering and sorting without hiding the source relationship.
Each result should show:

- Human-readable title.
- Original filename and file type.
- Created or published date.
- Conversion mode and OCR provider, when applicable.
- Fidelity or review status.
- Last updated timestamp.
- Actions for reading Markdown, opening the original, comparing versions, and viewing metadata.

The generated slug should remain available as technical metadata, but it should not be the main
label users have to read.

### Document view: answer first, evidence close by

A document page should put the converted content first and keep evidence one click away:

- A compact document header with title, source type, date, and status.
- A table of contents that follows the document headings.
- Search-in-document highlighting.
- OCR text marked as searchable evidence without overwhelming the main reading flow.
- Page or image references where the source supports them.
- A source panel or compare action for checking the original file.
- A visible conversion details link for provider, mode, warnings, and review state.

### Future enhancements: design and engineering record

This page remains the place for deferred capabilities, architectural decisions, and handoff notes.
It should link to prototypes and decision records without turning the primary document navigation into
a project-management backlog.

## Search experience

Search should work as a documentation search engine and a library finder:

- Search titles, headings, body text, OCR footnotes, filenames, and structured metadata.
- Show result type, source format, date, and matching section.
- Highlight the exact match in the result and when the document opens.
- Offer filters for PDF/DOCX, OCR/native extraction, review status, and date.
- Keep search state when navigating back from a document.
- Provide a useful empty state with spelling suggestions and nearby categories.
- Make OCR matches explicit, for example: `Match found in OCR text from image 3`.

For larger libraries, title filtering should happen immediately on the library page, while full-text
search should continue to use the generated search index or a future dedicated index.

## Progressive IT features

### Operational context

Documents should be able to carry lightweight operational context without changing the Markdown
source format:

- Service or application area.
- Environment: development, test, or production.
- Owner or team.
- Review cadence.
- Support severity.
- Related runbooks and known issues.

These fields belong in structured metadata or a manifest, not scattered into the published body.

### Safe actions

A runbook can expose clear next actions while preserving a read-only default:

- Copy a command with one click.
- Show the command's required permissions and expected risk.
- Link to prerequisites and rollback steps.
- Require confirmation before any future action integration executes.
- Record that a user viewed or acknowledged a high-risk procedure only when an audit system exists.

The first version should remain documentation-only. Execution integrations should be a later,
explicitly governed capability.

### Version and source comparison

Readers should be able to compare:

- Current Markdown versus a previous published version.
- Converted Markdown versus the original source.
- Native extraction versus OCR fallback when both are available.
- A runbook revision versus the last reviewed revision.

The comparison view should identify changed headings, commands, tables, links, and OCR sections rather
than presenting an unreadable raw text diff alone.

### Review and trust signals

A progressive page should make uncertainty visible:

- `Verified` when a human review has been recorded.
- `Review required` when OCR confidence or structural checks are weak.
- `Stale` when the review date or source age exceeds policy.
- `Native text` or `OCR text` for provenance.
- `Technical validation passed` separately from `Fidelity review complete`.

These statuses must not be collapsed into a single misleading quality score.

## Visual language

The design should be restrained, technical, and memorable without becoming a dashboard full of
cards. Recommended direction:

- Desktop-first left navigation with search kept in the sidebar.
- Wide reading column with a stable line length and a secondary evidence rail when useful.
- Strong typography hierarchy for titles, headings, commands, and metadata.
- Neutral paper-like reading surface with teal action color and coral review accents.
- Small, square-cornered panels for actual tools, not decorative containers around every section.
- Icons for familiar actions such as search, copy, compare, source, and external link.
- Tooltips for unfamiliar icons and accessible text labels for all important actions.
- Motion limited to page-load reveals, search result transitions, and status changes.

The page should remain useful in a plain browser, on a narrow screen, and with keyboard navigation.
The visual treatment must never hide document text or make a control look like a decorative badge.

## Technical direction

A future implementation should preserve the current authoritative conversion boundary:

```text
Upload
  -> authoritative converter
  -> Markdown + assets + manifest
  -> validation
  -> MkDocs or search index
  -> document library and reader
```

Recommended evolution points:

- Keep one converter function per input format.
- Replace fragile list-page decoration with a document manifest that drives library rows.
- Store stable document IDs separately from display titles and filenames.
- Move extracted images into managed package assets instead of data URIs for larger documents.
- Keep OCR diagnostics in structured metadata and searchable OCR text in a deliberate content block.
- Make site builds incremental or asynchronous when rebuild latency becomes visible.
- Add an explicit provider interface for local OCR and optional Azure Document Intelligence.
- Preserve direct/API/batch parity tests for Markdown, assets, manifests, and quality metadata.
- Keep path validation, source-file pairing, and deletion protection at the publishing boundary.

## Definition of done for a first progressive version

A first meaningful version should not attempt every idea above. It should deliver this narrow slice:

- Library title filter with newest-first sorting.
- Human-readable document metadata and file-type labels.
- Search results that identify OCR matches.
- A document header with source, conversion mode, and review status.
- A stable package manifest with document ID, source file, assets, and OCR diagnostics.
- A compare link between Markdown and the original source.
- Keyboard-accessible actions and mobile-safe layouts.
- Tests for direct/API/batch parity and a fixture with embedded OCR text.

## What should wait

These should remain outside the first pass:

- Automatic command execution from a document page.
- Semantic or generative answers that obscure the source document.
- A complex multi-user permission model before the storage boundary is designed.
- A single opaque quality rating that mixes technical success with human fidelity.
- Mandatory Azure services that would break local and offline conversion.

The guiding principle is simple: make the next useful answer easier to find, easier to trust, and
safer to act on while keeping the source and conversion evidence close at hand.
