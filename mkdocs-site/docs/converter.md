# Convert a document

<div id="library-converter" class="library-converter">
  <div class="converter-top-link"><a href="/batch">Experimental batch convert</a></div>
  <p class="converter-intro">Convert a DOCX or PDF, review the Markdown, then publish it to this library.</p>

  <form id="library-converter-form" class="converter-form">
    <input id="library-document" type="file" accept=".docx,.pdf" hidden>
    <button id="library-drop-zone" class="drop-zone" type="button">
      <strong>Drop a DOCX or PDF here</strong>
      <span>or click to choose a file</span>
    </button>
    <p id="library-selected-file" class="converter-hint">No file selected.</p>
    <button id="library-convert" class="library-action library-action-primary" type="submit">Convert document</button>
  </form>

  <p id="library-status" class="converter-status" role="status" aria-live="polite">Ready.</p>
  <div id="library-progress-panel" class="library-progress" hidden>
    <div class="progress-heading"><strong id="library-progress-label">Conversion in progress</strong><span id="library-progress-time"></span></div>
    <progress id="library-progress" max="100" aria-label="Conversion progress"></progress>
    <p class="converter-hint">Approximate timing only; image-heavy PDFs may take longer.</p>
  </div>

  <div class="converter-actions">
    <button id="library-download" type="button" disabled>Download Markdown</button>
    <button id="library-publish" type="button" disabled>Upload to library</button>
  </div>

  <div class="converter-workspace">
    <section>
      <h2>Markdown</h2>
      <textarea id="library-markdown" rows="22" aria-label="Markdown output"></textarea>
    </section>
    <section>
      <h2>Preview</h2>
      <div id="library-preview" class="library-preview" aria-live="polite"></div>
    </section>
  </div>
</div>