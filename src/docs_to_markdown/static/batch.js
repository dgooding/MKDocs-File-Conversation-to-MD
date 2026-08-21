const form = document.querySelector("#batch-form");
const fileInput = document.querySelector("#documents");
const fileList = document.querySelector("#selected-files");
const status = document.querySelector("#batch-status");
const submit = form.querySelector('button[type="submit"]');
const download = document.querySelector("#batch-download");
const publish = document.querySelector("#batch-publish");
const progressPanel = document.querySelector("#batch-progress-panel");
const progress = document.querySelector("#batch-progress");
const progressLabel = document.querySelector("#batch-progress-label");
const progressTime = document.querySelector("#batch-progress-time");
let progressTimer;
let startedAt;
let batchArchive;
let batchFilename = "markdown-batch.zip";

function formatSeconds(seconds) {
  return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

function startProgress(files) {
  startedAt = Date.now();
  const totalMegabytes = files.reduce((total, file) => total + file.size, 0) / (1024 * 1024);
  const estimate = Math.max(8, Math.min(300, Math.round(8 + totalMegabytes * 10 + files.length * 2)));
  progressPanel.hidden = false;
  progress.removeAttribute("value");
  progressLabel.textContent = "Batch conversion in progress";
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
  progressLabel.textContent = success ? "Batch conversion complete" : "Batch conversion stopped";
  progressTime.textContent = `Elapsed ${formatSeconds(Math.floor((Date.now() - startedAt) / 1000))}`;
}

function showFiles() {
  fileList.replaceChildren();
  const files = Array.from(fileInput.files);
  if (!files.length) {
    const item = document.createElement("li");
    item.textContent = "No files selected.";
    fileList.append(item);
    return;
  }
  for (const file of files) {
    const item = document.createElement("li");
    item.textContent = `${file.name} (${Math.ceil(file.size / 1024)} KB)`;
    fileList.append(item);
  }
}

fileInput.addEventListener("change", () => {
  batchArchive = null;
  download.disabled = true;
  publish.disabled = true;
  showFiles();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const files = Array.from(fileInput.files);
  if (!files.length) {
    status.textContent = "Choose at least one DOCX or PDF file.";
    return;
  }

  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  status.textContent = `Converting ${files.length} file${files.length === 1 ? "" : "s"}...`;
  startProgress(files);
  submit.disabled = true;

  try {
    const response = await fetch("/api/convert/batch", { method: "POST", body: formData });
    if (!response.ok) {
      const result = await response.json();
      throw new Error(result.detail || "Batch conversion failed.");
    }
    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="([^"]+)"/);
    const filename = match ? match[1] : "markdown-batch.zip";
    batchArchive = blob;
    batchFilename = filename;
    download.disabled = false;
    publish.disabled = false;
    finishProgress(true);
    status.textContent = "Batch conversion complete. Choose Download ZIP or Upload documents to MkDocs.";
  } catch (error) {
    finishProgress(false);
    status.textContent = error instanceof Error ? error.message : "Batch conversion failed.";
  } finally {
    submit.disabled = false;
  }
});

download.addEventListener("click", () => {
  if (!batchArchive) {
    return;
  }
  const url = URL.createObjectURL(batchArchive);
  const link = document.createElement("a");
  link.href = url;
  link.download = batchFilename;
  link.click();
  URL.revokeObjectURL(url);
  status.textContent = "ZIP download started.";
});

publish.addEventListener("click", async () => {
  const files = Array.from(fileInput.files);
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  publish.disabled = true;
  status.textContent = "Uploading documents to MkDocs...";
  try {
    const response = await fetch("/api/publish/batch", { method: "POST", body: formData });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = result.detail;
      const message = typeof detail === "string" ? detail
        : Array.isArray(detail) ? detail.map((item) => (item && item.msg) || "").filter(Boolean).join(" ")
        : "";
      throw new Error(message || "Batch upload failed.");
    }
    status.textContent = `Uploaded ${result.count} document${result.count === 1 ? "" : "s"}. Opening MkDocs...`;
    window.location.href = "/mkdocs/markdown/";
  } catch (error) {
    publish.disabled = false;
    status.textContent = error instanceof Error ? error.message : "Batch upload failed.";
  }
});