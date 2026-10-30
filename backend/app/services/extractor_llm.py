"""
Pass 2 & Multimodal Vision extraction — Google Gemini API (gemini-3.1-flash-lite / gemini-3.5-flash-lite).

Supports both:
- Multimodal document scanning (sending image/PDF bytes directly to Gemini Vision via inline_data)
- Text extraction fallback (sending email/OCR text to Gemini)
"""

from __future__ import annotations

import base64
import json
import logging
import os
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional

import httpx
from dotenv import load_dotenv

from app.services.extractor_regex import ExtractionResult

load_dotenv()

logger = logging.getLogger(__name__)

_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
_MODELS = ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite"]
_API_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

_SYSTEM_PROMPT = """\
You are a precise data-extraction assistant for a warranty-tracking and purchase-radar system.
Extract purchase information from the provided invoice image, PDF, or text and return
ONLY a single valid JSON object (NEVER a JSON array, no prose, no markdown fences).

Required JSON schema:
{
  "product_name": string or null,
  "brand": string or null,
  "retailer": string or null,
  "purchase_date": "YYYY-MM-DD" or null,
  "price": number or null,
  "warranty_period_months": integer or null,
  "return_window_days": integer or null,
  "confidence": "high" | "medium" | "low"
}

Rules:
1. Always return a SINGLE JSON object `{...}`, never a list `[...]`.
2. If the bill/invoice contains multiple line items, combine the main item names into "product_name" (e.g. "Orange Powder, Walnuts, Coin (+3 more)") and set "price" to the final total bill amount (or sum of line item amounts).
3. If "brand" is not distinct from the store/retailer on a multi-item bill, set "brand" to the brand of the primary product or the store/bill name.
4. "price" must be a plain number (no currency symbols). Ignore penalty/fine-print charges like cheque bouncing charges.
5. "purchase_date" must be ISO 8601 (YYYY-MM-DD).
6. "warranty_period_months": convert years to months (1 year = 12 months). If the invoice states "Warranty direct from service centre" or manufacturer warranty without specifying duration, use 12.
7. "return_window_days": integer number of days in the return/replacement window if mentioned.
8. Set "confidence" to "high" when at least product_name and 2 other fields (price, purchase_date, retailer, or brand) are found.
"""


def extract_with_llm(
    text: str,
    file_bytes: Optional[bytes] = None,
    mime_type: Optional[str] = None,
) -> Optional[ExtractionResult]:
    """
    Send document image/PDF bytes and/or extracted text to the Gemini API
    and parse the structured JSON response.
    """
    api_key = (_GEMINI_API_KEY or os.getenv("GEMINI_API_KEY") or "").strip()
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — LLM extraction skipped.")
        return None

    max_chars = 8_000
    truncated_text = (text or "")[:max_chars]

    parts: list[dict] = [{"text": _SYSTEM_PROMPT}]

    if file_bytes and mime_type in {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "application/pdf",
    }:
        norm_mime = "image/jpeg" if mime_type == "image/jpg" else mime_type
        b64_data = base64.b64encode(file_bytes).decode("ascii")
        parts.append({"inline_data": {"mime_type": norm_mime, "data": b64_data}})

    if truncated_text.strip():
        parts.append({"text": f"\nExtracted OCR / Document Text:\n{truncated_text}\n\nReturn JSON object:"})
    else:
        parts.append({"text": "\nExtract all purchase and warranty fields from this document as a single JSON object:"})

    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "temperature": 0.0,
            "maxOutputTokens": 512,
            "responseMimeType": "application/json",
        },
    }

    for model_name in _MODELS:
        url = _API_URL_TEMPLATE.format(model=model_name)
        try:
            resp = httpx.post(
                url,
                params={"key": api_key},
                json=payload,
                timeout=12.0,
            )
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            body = resp.json()
            candidates = body.get("candidates") or []
            if not candidates:
                continue
            content_parts = candidates[0].get("content", {}).get("parts") or []
            raw_text = "".join(p.get("text", "") for p in content_parts if "text" in p).strip()
            if raw_text:
                parsed = _parse_llm_response(raw_text, model_name=model_name)
                if parsed is not None:
                    return parsed
        except Exception as exc:
            logger.warning("Gemini API call failed for model %s: %s", model_name, exc)

    return None


def _parse_llm_response(raw: str, model_name: str = "gemini-3.1-flash-lite") -> Optional[ExtractionResult]:
    """Parse Gemini's raw JSON output into an ExtractionResult."""
    clean = raw.strip()
    if clean.startswith("```"):
        lines = clean.splitlines()
        clean = "\n".join(line for line in lines if not line.startswith("```")).strip()

    try:
        parsed_json = json.loads(clean)
    except json.JSONDecodeError as exc:
        logger.error("LLM response is not valid JSON (error at char %d): %r", exc.pos, raw[:200])
        return None

    # Handle case where model returns a list of items instead of a single dict
    if isinstance(parsed_json, list):
        valid_dicts = [d for d in parsed_json if isinstance(d, dict)]
        if not valid_dicts:
            return None
        if len(valid_dicts) == 1:
            data = valid_dicts[0]
        else:
            names = [str(d.get("product_name")).strip() for d in valid_dicts if d.get("product_name")]
            shown = ", ".join(names[:3])
            extra = f" (+{len(names) - 3} more)" if len(names) > 3 else ""
            total_price = sum(
                float(d["price"]) for d in valid_dicts if d.get("price") is not None
            )
            data = dict(valid_dicts[0])
            data["product_name"] = f"{shown}{extra}" if shown else None
            if total_price > 0:
                data["price"] = round(total_price, 2)
    elif isinstance(parsed_json, dict):
        data = parsed_json
    else:
        return None

    result = ExtractionResult(pass_used="llm")
    result.product_name = _str_or_none(data.get("product_name"))
    result.brand = _str_or_none(data.get("brand")) or _str_or_none(data.get("retailer"))
    result.retailer = _str_or_none(data.get("retailer"))
    result.price = _decimal_or_none(data.get("price"))
    result.confidence = _validated_confidence(data.get("confidence", "high" if result.product_name else "low"))

    raw_date = data.get("purchase_date")
    if raw_date and isinstance(raw_date, str):
        try:
            result.purchase_date = date.fromisoformat(raw_date[:10])
        except ValueError:
            logger.warning("LLM returned invalid purchase_date: %r", raw_date)

    raw_months = data.get("warranty_period_months")
    if raw_months is not None:
        try:
            result.warranty_period_months = int(raw_months)
        except (TypeError, ValueError):
            pass

    raw_days = data.get("return_window_days")
    if raw_days is not None:
        try:
            result.return_window_days = int(raw_days)
        except (TypeError, ValueError):
            pass

    result.source_snippet = f"[Gemini Vision AI — {model_name}]"
    logger.info(
        "LLM extraction complete (%s): product=%r brand=%r retailer=%r price=%s date=%s confidence=%s",
        model_name,
        result.product_name,
        result.brand,
        result.retailer,
        result.price,
        result.purchase_date,
        result.confidence,
    )
    return result


def _str_or_none(value) -> Optional[str]:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    return str(value).strip()


def _decimal_or_none(value) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _validated_confidence(value) -> str:
    if value in ("high", "medium", "low"):
        return value
    return "low"
