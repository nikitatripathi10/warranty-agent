# ── Warranty Radar — Backend Dockerfile ──────────────────────────────────────
#
# Multi-stage build:
#   Stage 1 (builder): install Python deps into a clean virtualenv
#   Stage 2 (runtime): copy only the venv + app code — no build tools
#
# Build:
#   docker build -t warranty-radar-backend .
#
# Run locally (set env vars via --env-file):
#   docker run -p 8000:8000 --env-file .env warranty-radar-backend
#
# Note: Tesseract and Poppler are installed in the runtime stage for OCR support.

# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tools needed for some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtualenv and install dependencies
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Install Tesseract OCR + Poppler (for scanned PDF support)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-hin \
    poppler-utils \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv

# Make venv executables take priority
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Copy application code
COPY . .

# Create uploads directory (runtime — typically mounted as a volume)
RUN mkdir -p uploads

# Expose the default uvicorn port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Start uvicorn (PORT env var is set by Railway/Render automatically)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
