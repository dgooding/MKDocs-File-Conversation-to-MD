const form = document.querySelector("#conversion-form");
const fileInput = document.querySelector("#document");
const selectedFile = document.querySelector("#selected-file");
const status = document.querySelector("#status");
const markdown = document.querySelector("#markdown");
const preview = document.querySelector("#preview");
const download = document.querySelector("#download");
const publish = document.querySelector("#publish");
const progressPanel = document.querySelector("#conversion-progress-panel");
const conversionProgress = document.querySelector("#conversion-progress");
const progressLabel = document.querySelector("#progress-label");
const progressTime = document.querySelector("#progress-time");

let outputFilename = "document.md";
let lastConvertedFile = null;
let previewTimer;
let progressTimer;
let conversionStartedAt;

function setStatus(message, tone) {
  status.textContent = message;
  status.className = `status-${tone}`;
}

function estimateSeconds(file) {
  const megabytes = file.size / (1024 * 1024);
  return Math.max(8, Math.min(180, Math.round(10 + megabytes * 10)));
}

function formatSeconds(seconds) {
  return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

function startProgress(file) {
  conversionStartedAt = Date.now();
  const estimate = estimateSeconds(file);
  progressPanel.hidden = false;
  conversionProgress.removeAttribute("value");
  progressLabel.textContent = "Conversion in progress";

  const updateProgressText = () => {
    const elapsed = Math.floor((Date.now() - conversionStartedAt) / 1000);
    progressTime.textContent = `Elapsed ${formatSeconds(elapsed)} · Approx. ${formatSeconds(estimate)}`;
  };
  updateProgressText();
  window.clearInterval(progressTimer);
  progressTimer = window.setInterval(updateProgressText, 1000);
}

function finishProgress(success) {
  window.clearInterval(progressTimer);
  const elapsed = Math.floor((Date.now() - conversionStartedAt) / 1000);
  conversionProgress.value = 100;
  progressLabel.textContent = success ? "Conversion complete" : "Conversion stopped";
  progressTime.textContent = `Elapsed ${formatSeconds(elapsed)}`;
}

async function renderPreview() {
  try {
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
  } catch (error) {
    preview.textContent = error instanceof Error ? error.message : "Preview failed.";
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = fileInput.files[0];
  if (!file) {
    setStatus("Choose a DOCX or PDF file.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  setStatus("Converting...", "info");
  startProgress(file);
  download.disabled = true;
  publish.disabled = true;

  try {
    const response = await fetch("/api/convert", {
      method: "POST",
      body: formData,
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || "Conversion failed.");
    }

    markdown.value = result.markdown;
    outputFilename = result.filename;
    lastConvertedFile = file;
    setStatus("Conversion complete.", "success");
    download.disabled = false;
    publish.disabled = false;
    finishProgress(true);
    renderPreview();
  } catch (error) {
    markdown.value = "";
    preview.replaceChildren();
    finishProgress(false);
    setStatus(error instanceof Error ? error.message : "Conversion failed.", "error");
  }
});

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  selectedFile.textContent = file ? `Selected: ${file.name}` : "No file selected.";
});

markdown.addEventListener("input", () => {
  window.clearTimeout(previewTimer);
  previewTimer = window.setTimeout(renderPreview, 200);
});

download.addEventListener("click", () => {
  const blob = new Blob([markdown.value], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = outputFilename;
  link.click();
  URL.revokeObjectURL(url);
});

publish.addEventListener("click", async () => {
  if (!lastConvertedFile) {
    setStatus("Convert a file before publishing.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", lastConvertedFile);
  formData.append("markdown", markdown.value);
  setStatus("Uploading to MkDocs...", "info");

  try {
    const response = await fetch("/api/publish", {
      method: "POST",
      body: formData,
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || "Publish failed.");
    }
    const publishedUrl = `/mkdocs/markdown/${encodeURIComponent(result.slug)}/`;
    setStatus(`Uploaded as "${result.slug}". Opening MkDocs...`, "success");
    window.open(publishedUrl, "_blank", "noopener");
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "Publish failed.", "error");
  }
});