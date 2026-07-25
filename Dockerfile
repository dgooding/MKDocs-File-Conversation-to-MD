# Production image: full conversion stack for Railway / Render / Fly / HF Spaces
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000 \
    MPLCONFIGDIR=/tmp/matplotlib \
    HOME=/tmp

# System libs for PDF / OCR / Office extraction
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-osd \
        poppler-utils \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libgomp1 \
        fonts-dejavu-core \
        fonts-liberation \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install "Pillow>=10.0.0" \
    && (pip install "markitdown[all]>=0.1.1" || pip install "markitdown[docx,pptx,xlsx,pdf,audio,youtube-transcription]>=0.1.1" || true)

COPY . .

# Build MkDocs static site into /app/site
RUN python -m mkdocs build --clean

# Writable runtime dirs (ephemeral on free tiers)
RUN mkdir -p /app/docs/converted /app/docs/assets/converted /app/.uploads /tmp \
    && chmod -R 777 /app/docs/converted /app/docs/assets/converted /app/.uploads /tmp

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/api/health" || exit 1

# Railway/Render set PORT; bind all interfaces
CMD ["sh", "-c", "exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
