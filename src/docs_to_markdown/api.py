from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .batch_converter import convert_batch
from .converter import convert_docx
from .mkdocs_publish import publish_to_mkdocs
from .pdf_converter import convert_pdf
from .renderer import render_markdown


app = FastAPI(title="Documents to Markdown")
STATIC_DIR = Path(__file__).with_name("static")
MAX_BATCH_FILES = 25
MAX_BATCH_BYTES = 100 * 1024 * 1024
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=FileResponse)
async def upload_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/batch", response_class=FileResponse)
async def batch_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "batch.html")


class PreviewRequest(BaseModel):
    markdown: str


@app.post("/api/render")
async def render_preview(request: PreviewRequest) -> dict[str, str]:
    return {"html": render_markdown(request.markdown)}


@app.post("/api/convert")
async def convert(file: UploadFile = File(...)) -> dict[str, str]:
    filename = file.filename or ""
    extension = Path(filename).suffix.lower()
    converters = {".docx": convert_docx, ".pdf": convert_pdf}
    if extension not in converters:
        raise HTTPException(status_code=415, detail="Only DOCX and PDF files are supported")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Document cannot be empty")

    try:
        markdown = converters[extension](content)
    except Exception as error:
        raise HTTPException(status_code=422, detail="Document could not be converted") from error

    return {"filename": f"{Path(filename).stem}.md", "markdown": markdown}


@app.post("/api/publish")
async def publish(file: UploadFile = File(...), markdown: str = Form(...)) -> dict[str, str]:
    # Test-only: publishes a conversion + its source file into the local mkdocs-site search sandbox.
    content = await file.read()
    try:
        result = publish_to_mkdocs(file.filename or "document", content, markdown)
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return result


@app.post("/api/convert/batch")
async def convert_files(files: list[UploadFile] = File(...)) -> StreamingResponse:
    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(status_code=400, detail=f"A batch can contain at most {MAX_BATCH_FILES} files")

    inputs = []
    total_bytes = 0
    for index, file in enumerate(files, start=1):
        content = await file.read()
        total_bytes += len(content)
        if total_bytes > MAX_BATCH_BYTES:
            raise HTTPException(status_code=413, detail="Batch size cannot exceed 100 MB")
        inputs.append((file.filename or f"document-{index}", content))

    archive, manifest = convert_batch(inputs)
    filename = f"markdown-batch-{manifest['batch_id']}.zip"
    return StreamingResponse(
        archive,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )