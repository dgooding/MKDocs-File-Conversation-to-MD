const form = document.querySelector("#conversion-form");
const fileInput = document.querySelector("#document");
const status = document.querySelector("#status");
const markdown = document.querySelector("#markdown");
const preview = document.querySelector("#preview");
const download = document.querySelector("#download");

let outputFilename = "document.md";
let previewTimer;

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
    status.textContent = "Choose a DOCX file.";
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  status.textContent = "Converting...";
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
    status.textContent = "Conversion complete.";
    download.disabled = false;
  } catch (error) {
    markdown.value = "";
    preview.replaceChildren();
    status.textContent = error instanceof Error ? error.message : "Conversion failed.";
  }
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