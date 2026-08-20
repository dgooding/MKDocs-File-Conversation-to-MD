import os
import shutil
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Protocol

from PIL import Image


class OCRAdapter(Protocol):
    def extract_text(self, image: Image.Image) -> str | None: ...


@dataclass(frozen=True)
class TesseractOCR:
    executable: str

    @classmethod
    def detect(cls) -> "TesseractOCR | None":
        configured = os.environ.get("TESSERACT_CMD", "").strip()
        if configured:
            candidates = [configured]
        else:
            candidates = [
                shutil.which("tesseract"),
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Tesseract-OCR/tesseract.exe"),
            ]

        for candidate in candidates:
            if not candidate or not Path(candidate).is_file():
                continue
            try:
                probe = subprocess.run(
                    [candidate, "--version"],
                    capture_output=True,
                    timeout=4,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError):
                continue
            if probe.returncode == 0:
                return cls(candidate)
        return None

    def extract_text(self, image: Image.Image) -> str | None:
        buffer = BytesIO()
        image.convert("RGB").save(buffer, format="PNG")
        try:
            result = subprocess.run(
                [self.executable, "stdin", "stdout", "-l", "eng", "--psm", "6"],
                input=buffer.getvalue(),
                capture_output=True,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode != 0:
            return None
        text = result.stdout.decode("utf-8", errors="replace").strip()
        return text or None


@lru_cache(maxsize=1)
def _rapidocr_engine():
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


@dataclass(frozen=True)
class RapidOCRAdapter:
    """Pure-Python OCR fallback (ONNX Runtime); needs no external binary install."""

    @classmethod
    def detect(cls) -> "RapidOCRAdapter | None":
        try:
            _rapidocr_engine()
        except Exception:
            return None
        return cls()

    def extract_text(self, image: Image.Image) -> str | None:
        import numpy as np

        try:
            result, _ = _rapidocr_engine()(np.array(image.convert("RGB")))
        except Exception:
            return None
        if not result:
            return None
        lines = [str(entry[1]) for entry in result if entry and len(entry) > 1]
        text = "\n".join(lines).strip()
        return text or None


def detect_ocr_adapter() -> OCRAdapter | None:
    """Prefer Tesseract when configured/installed; otherwise fall back to the bundled pure-Python engine."""
    return TesseractOCR.detect() or RapidOCRAdapter.detect()