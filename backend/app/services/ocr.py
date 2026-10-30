"""
OCR and text-extraction service for uploaded documents.

Supports:
  - Text-based PDFs   → pdfplumber (fast, no OCR)
  - Scanned PDFs      → pdf2image  → pytesseract
  - Images (JPG/PNG)  → pytesseract directly

Design:
  - Normalizes image dimensions (upscales tiny images < 900px, downscales huge
    images > 1400px) and converts to grayscale so Tesseract OCR completes in
    1–3 seconds even on constrained cloud CPUs (e.g. 0.1 vCPU Render instances).
  - Enforces a hard per-page timeout on pytesseract calls so uploads never hang.
"""

from __future__ import annotations

import logging
import os
import time
from io import BytesIO
from typing import Optional

logger = logging.getLogger(__name__)

# Poppler bin path for pdf2image on Windows (optional — falls back to PATH)
_POPPLER_PATH: Optional[str] = os.getenv("POPPLER_PATH")

# Minimum characters pdfplumber must extract before we consider a PDF text-based
_MIN_TEXT_CHARS = 40

# Hard timeout (seconds) for a single pytesseract call
_OCR_TIMEOUT_SEC = 20


def extract_text_from_pdf(file_bytes: bytes, filename: str = "document.pdf") -> str:
    """
    Extract text from a PDF file.

    Strategy:
    1. Try pdfplumber for text-based PDFs (fast, no external deps).
    2. If extracted text < _MIN_TEXT_CHARS, assume scanned — use pdf2image + pytesseract.
    """
    try:
        import pdfplumber

        text_parts: list[str] = []
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            for page in pdf.pages[:5]:  # Cap at 5 pages for fast invoice turnaround
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

    return _ocr_pdf(file_bytes, filename)


def extract_text_from_image(file_bytes: bytes, filename: str = "image") -> str:
    """
    Run fast pytesseract OCR on an image file (JPEG, PNG, WEBP, TIFF, etc.).
    """
    t0 = time.monotonic()
    try:
        from PIL import Image
        import pytesseract

        image = Image.open(BytesIO(file_bytes))
        image = _prepare_image_for_ocr(image)

        # Primary fast pass with English LSTM model
        text = pytesseract.image_to_string(
            image,
            lang="eng",
            config="--oem 1 --psm 3",
            timeout=_OCR_TIMEOUT_SEC,
        ).strip()

        # Fallback to English + Hindi only if primary pass found almost nothing
        if len(text) < 20:
            try:
                text_hin = pytesseract.image_to_string(
                    image,
                    lang="eng+hin",
                    config="--oem 1 --psm 3",
                    timeout=_OCR_TIMEOUT_SEC,
                ).strip()
                if len(text_hin) > len(text):
                    text = text_hin
            except Exception:
                pass

        elapsed = time.monotonic() - t0
        logger.info(
            "pytesseract extracted %d chars from '%s' in %.2fs",
            len(text),
            filename,
            elapsed,
        )
        return text
    except Exception as exc:
        logger.error("OCR failed for image '%s': %s", filename, exc)
        return ""


def extract_text(file_bytes: bytes, filename: str, content_type: str = "") -> tuple[str, bool]:
    """
    Unified entry point — dispatches to the right extractor based on file type.
    """
    filename_lower = filename.lower()
    is_pdf = "pdf" in content_type or filename_lower.endswith(".pdf")
    is_image = any(
        filename_lower.endswith(ext)
        for ext in (".jpg", ".jpeg", ".png", ".webp", ".tiff", ".tif", ".bmp", ".gif")
    ) or "image/" in content_type

    if is_pdf:
        text = extract_text_from_pdf(file_bytes, filename)
        ocr_used = len(text) < _MIN_TEXT_CHARS or _is_ocr_fallback_used(file_bytes)
        return text, ocr_used

    if is_image:
        text = extract_text_from_image(file_bytes, filename)
        return text, True

    logger.warning(
        "Unknown file type for '%s' (content_type=%r) — trying PDF then image",
        filename,
        content_type,
    )
    pdf_text = extract_text_from_pdf(file_bytes, filename)
    if pdf_text:
        return pdf_text, False
    img_text = extract_text_from_image(file_bytes, filename)
    return img_text, True


# ── Internal helpers ──────────────────────────────────────────────────────────

def _ocr_pdf(file_bytes: bytes, filename: str) -> str:
    """Convert PDF pages (up to 3) to images and run fast pytesseract on them."""
    try:
        from pdf2image import convert_from_bytes
        import pytesseract

        kwargs: dict = {"dpi": 130, "first_page": 1, "last_page": 3}
        if _POPPLER_PATH:
            kwargs["poppler_path"] = _POPPLER_PATH

        images = convert_from_bytes(file_bytes, **kwargs)
        logger.info("pdf2image converted '%s' into %d page(s)", filename, len(images))

        text_parts: list[str] = []
        for i, page_image in enumerate(images, start=1):
            page_image = _prepare_image_for_ocr(page_image)
            page_text = pytesseract.image_to_string(
                page_image,
                lang="eng",
                config="--oem 1 --psm 3",
                timeout=_OCR_TIMEOUT_SEC,
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
            total = sum(len(p.extract_text() or "") for p in pdf.pages[:5])
        return total < _MIN_TEXT_CHARS
    except Exception:
        return True


def _prepare_image_for_ocr(image, min_width: int = 800, max_dim: int = 1150):
    """
    Normalize image dimensions and convert to grayscale ('L') so Tesseract runs
    quickly without timing out on high-resolution photos or screenshots.
    """
    try:
        from PIL import Image

        # Convert RGBA/P to RGB with white background first
        if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
            bg = Image.new("RGB", image.size, (255, 255, 255))
            rgba = image.convert("RGBA")
            bg.paste(rgba, mask=rgba.split()[3])
            image = bg

        w, h = image.size
        longest = max(w, h)
        if longest > max_dim:
            scale = max_dim / longest
            image = image.resize((int(w * scale), int(h * scale)), Image.BILINEAR)
        elif w < min_width:
            scale = min_width / w
            image = image.resize((int(w * scale), int(h * scale)), Image.BILINEAR)

        return image.convert("L")
    except Exception:
        return image
