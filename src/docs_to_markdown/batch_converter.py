import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from .converter import convert_docx
from .pdf_converter import convert_pdf


CONVERTERS = {".docx": convert_docx, ".pdf": convert_pdf}


@dataclass
class BatchResult:
    input_filename: str
    output_filename: str | None
    status: str
    duration_ms: float | None = None
    markdown_bytes: int | None = None
    detail: str | None = None


def _output_filename(filename: str, used_names: set[str]) -> str:
    stem = Path(filename).stem or "document"
    candidate = f"{stem}.md"
    suffix = 2
    while candidate.casefold() in used_names:
        candidate = f"{stem}-{suffix}.md"
        suffix += 1
    used_names.add(candidate.casefold())
    return candidate


def convert_batch(files: list[tuple[str, bytes]]) -> tuple[BytesIO, dict[str, object]]:
    results: list[BatchResult] = []
    outputs: list[tuple[str, str]] = []
    used_names: set[str] = set()

    for filename, content in files:
        extension = Path(filename).suffix.lower()
        if extension not in CONVERTERS:
            results.append(BatchResult(filename, None, "unsupported", detail="Only DOCX and PDF files are supported"))
            continue
        if not content:
            results.append(BatchResult(filename, None, "empty", detail="Document cannot be empty"))
            continue

        started = time.perf_counter()
        try:
            markdown = CONVERTERS[extension](content)
        except Exception:
            results.append(BatchResult(filename, None, "error", detail="Document could not be converted"))
            continue

        output_filename = _output_filename(filename, used_names)
        duration_ms = round((time.perf_counter() - started) * 1000, 1)
        markdown_bytes = len(markdown.encode("utf-8"))
        outputs.append((output_filename, markdown))
        results.append(BatchResult(filename, output_filename, "success", duration_ms, markdown_bytes))

    counts = {status: sum(result.status == status for result in results) for status in ("success", "unsupported", "empty", "error")}
    manifest: dict[str, object] = {
        "batch_id": uuid4().hex[:12],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "total_files": len(results),
        "succeeded": counts["success"],
        "unsupported": counts["unsupported"],
        "empty": counts["empty"],
        "errors": counts["error"],
        "results": [asdict(result) for result in results],
    }

    archive = BytesIO()
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zip_file:
        for output_filename, markdown in outputs:
            zip_file.writestr(output_filename, markdown)
        zip_file.writestr("manifest.json", json.dumps(manifest, indent=2))
    archive.seek(0)
    return archive, manifest