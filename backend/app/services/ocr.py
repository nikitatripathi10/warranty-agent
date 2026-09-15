"""
OCR and text-extraction service for uploaded documents.

Supports:
  - Text-based PDFs   → pdfplumber (fast, no OCR)
  - Scanned PDFs      → pdf2image  → pytesseract
  - Images (JPG/PNG)  → pytesseract directly

Design:
  - Returns a plain string — the caller feeds it into the extraction pipeline.
  - Never stores the raw bytes in the database.
  - Falls back gracefully at each stage; returns empty string on complete failure.

System requirements (installed separately, not via pip):
  - Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki  (Windows)
  - Poppler:       https://github.com/oschwartz10612/poppler-windows (Windows)
    Set POPPLER_PATH env var to the bin/ directory if not on PATH.
"""

from __future__ import annotations

import logging
import os
from io import BytesIO
from typing import Optional

logger = logging.getLogger(__name__)

# Poppler bin path for pdf2image on Windows (optional — falls back to PATH)
_POPPLER_PATH: Optional[str] = os.getenv("POPPLER_PATH")

# Minimum characters pdfplumber must extract before we consider a PDF text-based
_MIN_TEXT_CHARS = 50


def extract_text_from_pdf(file_bytes: bytes, filename: str = "document.pdf") -> str:
    """
    Extract text from a PDF file.

    Strategy:
    1. Try pdfplumber for text-based PDFs (fast, no external deps).
    2. If extracted text < _MIN_TEXT_CHARS, assume scanned — use pdf2image + pytesseract.

    Args:
        file_bytes: Raw PDF bytes.
        filename:   Original filename (used only for logging).

    Returns:
        Extracted text as a plain string, or '' on failure.
    """
    # -- Pass 1: pdfplumber direct text extraction --
    try:
        import pdfplumber

        text_parts: list[str] = []
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        text = "\n".join(text_parts).strip()

        if len(text) >= _MIN_TEXT_CHARS:
            logger.info(
                "pdfplumber extracted %d chars from '%s' (text-based PDF)",
                len(text),
                filename,
            )
            return text

        logger.info(
            "pdfplumber only got %d chars from '%s' — attempting OCR",
            len(text),
            filename,
        )
    except Exception as exc:
        logger.warning("pdfplumber failed for '%s': %s — falling back to OCR", filename, exc)

    # -- Pass 2: pdf2image + pytesseract --
    return _ocr_pdf(file_bytes, filename)


def extract_text_from_image(file_bytes: bytes, filename: str = "image") -> str:
    """
    Run pytesseract OCR on an image file (JPEG, PNG, WEBP, TIFF, etc.).

    Args:
        file_bytes: Raw image bytes.
        filename:   Original filename (used only for logging).

    Returns:
        OCR'd text as a plain string, or '' on failure.
    """
    try:
        from PIL import Image
        import pytesseract

        image = Image.open(BytesIO(file_bytes))
        # Upscale small images for better OCR accuracy
        image = _maybe_upscale(image)
        text = pytesseract.image_to_string(image, lang="eng+hin", config="--psm 3")
        text = text.strip()
        logger.info("pytesseract extracted %d chars from '%s'", len(text), filename)
        return text
    except Exception as exc:
        logger.error("OCR failed for image '%s': %s", filename, exc)
        return ""


def extract_text(file_bytes: bytes, filename: str, content_type: str = "") -> tuple[str, bool]:
    """
    Unified entry point — dispatches to the right extractor based on file type.

    Args:
        file_bytes:   Raw file content.
        filename:     Original filename.
        content_type: MIME type from the upload (e.g. 'application/pdf').

    Returns:
        Tuple of (extracted_text: str, ocr_used: bool).
        ocr_used=True means pytesseract was invoked.
    """
    filename_lower = filename.lower()
    is_pdf = "pdf" in content_type or filename_lower.endswith(".pdf")
    is_image = any(
        filename_lower.endswith(ext)
        for ext in (".jpg", ".jpeg", ".png", ".webp", ".tiff", ".tif", ".bmp", ".gif")
    ) or "image/" in content_type

    if is_pdf:
        # extract_text_from_pdf handles both text-based and scanned internally
        text = extract_text_from_pdf(file_bytes, filename)
        ocr_used = len(text) < _MIN_TEXT_CHARS or _is_ocr_fallback_used(file_bytes)
        return text, ocr_used

    if is_image:
        text = extract_text_from_image(file_bytes, filename)
        return text, True  # Always uses OCR for images

    # Unknown type — try as text-based PDF, then as image
    logger.warning("Unknown file type for '%s' (content_type=%r) — trying PDF then image", filename, content_type)
    pdf_text = extract_text_from_pdf(file_bytes, filename)
    if pdf_text:
        return pdf_text, False
    img_text = extract_text_from_image(file_bytes, filename)
    return img_text, True


# ── Internal helpers ──────────────────────────────────────────────────────────

def _ocr_pdf(file_bytes: bytes, filename: str) -> str:
    """Convert each PDF page to an image and run pytesseract on it."""
    try:
        from pdf2image import convert_from_bytes
        import pytesseract

        kwargs: dict = {"dpi": 200}
        if _POPPLER_PATH:
            kwargs["poppler_path"] = _POPPLER_PATH

        images = convert_from_bytes(file_bytes, **kwargs)
        logger.info("pdf2image converted '%s' into %d page(s)", filename, len(images))

        text_parts: list[str] = []
        for i, page_image in enumerate(images, start=1):
            page_image = _maybe_upscale(page_image)
            page_text = pytesseract.image_to_string(
                page_image, lang="eng+hin", config="--psm 3"
            )
            text_parts.append(page_text)
            logger.debug("OCR page %d of '%s': %d chars", i, filename, len(page_text))

        full_text = "\n".join(text_parts).strip()
        logger.info("OCR extracted %d chars from '%s'", len(full_text), filename)
        return full_text

    except Exception as exc:
        logger.error("OCR pipeline failed for '%s': %s", filename, exc)
        return ""


def _is_ocr_fallback_used(file_bytes: bytes) -> bool:
    """Heuristic: check if pdfplumber got enough text without OCR."""
    try:
        import pdfplumber

        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            total = sum(
                len(p.extract_text() or "") for p in pdf.pages
            )
        return total < _MIN_TEXT_CHARS
    except Exception:
        return True


def _maybe_upscale(image, min_width: int = 1000):
    """Upscale small images to improve OCR accuracy."""
    try:
        from PIL import Image

        w, h = image.size
        if w < min_width:
            scale = min_width / w
            new_size = (int(w * scale), int(h * scale))
            return image.resize(new_size, Image.LANCZOS)
    except Exception:
        pass
    return image
