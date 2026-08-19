const form = document.querySelector("#batch-form");
const fileInput = document.querySelector("#documents");
const fileList = document.querySelector("#selected-files");
const status = document.querySelector("#batch-status");
const submit = form.querySelector('button[type="submit"]');

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

fileInput.addEventListener("change", showFiles);

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
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
    status.textContent = "Batch conversion complete. ZIP download started.";
  } catch (error) {
    status.textContent = error instanceof Error ? error.message : "Batch conversion failed.";
  } finally {
    submit.disabled = false;
  }
});