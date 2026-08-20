const form = document.querySelector("#conversion-form");
const fileInput = document.querySelector("#document");
const selectedFile = document.querySelector("#selected-file");
const status = document.querySelector("#status");
const markdown = document.querySelector("#markdown");
const preview = document.querySelector("#preview");
const download = document.querySelector("#download");

let outputFilename = "document.md";
let previewTimer;

function setStatus(message, tone) {
  status.textContent = message;
  status.className = `status-${tone}`;
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
  download.disabled = true;

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
    await renderPreview();
    outputFilename = result.filename;
    setStatus("Conversion complete.", "success");
    download.disabled = false;
  } catch (error) {
    markdown.value = "";
    preview.replaceChildren();
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