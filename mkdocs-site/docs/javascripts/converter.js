(function () {
  const root = document.querySelector("#library-converter");
  if (!root) {
    return;
  }

  const form = root.querySelector("#library-converter-form");
  const fileInput = root.querySelector("#library-document");
  const dropZone = root.querySelector("#library-drop-zone");
  const selectedFile = root.querySelector("#library-selected-file");
  const convert = root.querySelector("#library-convert");
  const status = root.querySelector("#library-status");
  const progressPanel = root.querySelector("#library-progress-panel");
  const progress = root.querySelector("#library-progress");
  const progressLabel = root.querySelector("#library-progress-label");
  const progressTime = root.querySelector("#library-progress-time");
  const markdown = root.querySelector("#library-markdown");
  const preview = root.querySelector("#library-preview");
  const download = root.querySelector("#library-download");
  const publish = root.querySelector("#library-publish");

  let selectedDocument;
  let outputFilename = "document.md";
  let progressTimer;
  let startedAt;

  function setStatus(message, tone) {
    status.textContent = message;
    status.className = `converter-status status-${tone}`;
  }

  function estimateSeconds(file) {
    return Math.max(8, Math.min(180, Math.round(10 + (file.size / (1024 * 1024)) * 10)));
  }

  function formatSeconds(seconds) {
    return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  }

  function setSelectedFile(file) {
    selectedDocument = file;
    selectedFile.textContent = file ? `Selected: ${file.name}` : "No file selected.";
  }

  function startProgress(file) {
    startedAt = Date.now();
    const estimate = estimateSeconds(file);
    progressPanel.hidden = false;
    progress.removeAttribute("value");
    progressLabel.textContent = "Conversion in progress";
    const update = () => {
      const elapsed = Math.floor((Date.now() - startedAt) / 1000);
      progressTime.textContent = `Elapsed ${formatSeconds(elapsed)} · Approx. ${formatSeconds(estimate)}`;
    };
    update();
    window.clearInterval(progressTimer);
    progressTimer = window.setInterval(update, 1000);
  }

  function finishProgress(success) {
    window.clearInterval(progressTimer);
    progress.value = 100;
    progressLabel.textContent = success ? "Conversion complete" : "Conversion stopped";
    progressTime.textContent = `Elapsed ${formatSeconds(Math.floor((Date.now() - startedAt) / 1000))}`;
  }

  async function renderPreview() {
    const response = await fetch("/api/render", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ markdown: markdown.value }),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error("Preview failed.");
    }
    preview.innerHTML = result.html;
  }

  dropZone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => setSelectedFile(fileInput.files[0]));
  ["dragenter", "dragover"].forEach((eventName) => dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("drop-zone-active");
  }));
  ["dragleave", "drop"].forEach((eventName) => dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("drop-zone-active");
  }));
  dropZone.addEventListener("drop", (event) => setSelectedFile(event.dataTransfer.files[0]));

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!selectedDocument) {
      setStatus("Choose a DOCX or PDF file.", "error");
      return;
    }
    const formData = new FormData();
    formData.append("file", selectedDocument);
    setStatus("Converting...", "info");
    startProgress(selectedDocument);
    convert.disabled = true;
    download.disabled = true;
    publish.disabled = true;
    try {
      const response = await fetch("/api/convert", { method: "POST", body: formData });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Conversion failed.");
      }
      markdown.value = result.markdown;
      outputFilename = result.filename;
      setStatus("Conversion complete.", "success");
      download.disabled = false;
      publish.disabled = false;
      finishProgress(true);
      renderPreview().catch(() => { preview.textContent = "Preview failed."; });
    } catch (error) {
      finishProgress(false);
      setStatus(error instanceof Error ? error.message : "Conversion failed.", "error");
    } finally {
      convert.disabled = false;
    }
  });

  download.addEventListener("click", () => {
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([markdown.value], { type: "text/markdown;charset=utf-8" }));
    link.download = outputFilename;
    link.click();
    URL.revokeObjectURL(link.href);
  });

  publish.addEventListener("click", async () => {
    const formData = new FormData();
    formData.append("file", selectedDocument);
    formData.append("markdown", markdown.value);
    setStatus("Uploading to library...", "info");
    try {
      const response = await fetch("/api/publish", { method: "POST", body: formData });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Upload failed.");
      }
      setStatus(`Uploaded as "${result.slug}". Opening document...`, "success");
      window.location.href = `/mkdocs/markdown/${encodeURIComponent(result.slug)}/`;
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Upload failed.", "error");
    }
  });
}());