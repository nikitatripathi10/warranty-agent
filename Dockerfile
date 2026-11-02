# ── Warranty Radar — Root Dockerfile for Render / Cloud Deployment ─────────────
#
# Enables 1-click zero-config deployment on Render, Railway, Fly.io, etc.
# Works directly from repository root.
#
# The SPA is built here and copied into the runtime image, so the API and the
# frontend deploy together on one origin. main.py serves it only when the
# directory exists, so this stays safe on hosts that build the backend alone.

# ── Stage 1: Frontend build ───────────────────────────────────────────────────
FROM node:20-slim AS frontend

WORKDIR /build/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm install --no-audit --no-fund

COPY frontend/ ./
RUN npm run build


# ── Stage 2: Python builder ───────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# ── Stage 3: Runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-hin \
    poppler-utils \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Copy backend code
COPY backend/ .

# Built SPA (served at / by main.py when present)
COPY --from=frontend /build/frontend/dist ./frontend_dist

RUN mkdir -p uploads

EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
