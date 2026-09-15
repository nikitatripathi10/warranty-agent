"""
Pass 2 extraction — Anthropic Claude LLM fallback.

Called when the regex pass returns confidence == 'low'.  We send the cleaned
email/document text to Claude with a structured prompt + few-shot examples and
expect a JSON response matching ExtractionResult fields.

Design principles:
- Hard timeout (ANTHROPIC_TIMEOUT_SECONDS) on every API call.
- Malformed JSON responses are caught and logged; we return None rather than crash.
- The model is instructed explicitly to output confidence='low' rather than guess.
- Prompt includes 2 few-shot examples to anchor the model's output format.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional

import anthropic
from dotenv import load_dotenv

from app.services.extractor_regex import ExtractionResult

load_dotenv()

logger = logging.getLogger(__name__)

_ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
_ANTHROPIC_TIMEOUT = float(os.getenv("ANTHROPIC_TIMEOUT_SECONDS", "30"))
_MODEL = "claude-haiku-4-5"  # Fast + cheap — ideal for structured extraction

# ── Prompt templates ──────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a precise data-extraction assistant for a warranty-tracking system.
Extract purchase information from the provided email or document text and return
ONLY a valid JSON object — no prose, no markdown, no code fences.

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
1. If you are uncertain about a field, set it to null — do NOT guess.
2. If the overall extraction is uncertain, set confidence to "low".
3. confidence = "high"   → product_name, purchase_date, price, AND retailer/brand all found
   confidence = "medium" → at least product_name AND price found
   confidence = "low"    → anything else
4. price must be a plain number (no currency symbols). Use INR value if multiple currencies.
5. purchase_date must be ISO 8601 (YYYY-MM-DD).
6. warranty_period_months: convert years to months (1 year = 12 months).
7. return_window_days: integer number of days in the return/replacement window.
8. MULTILINGUAL: The input may be written in Hindi, Hinglish (Hindi+English mix), or any
   other regional-language format. You MUST still extract all fields correctly and return
   them using the same English-keyed JSON schema above. Translate product names and brands
   to their standard English/brand-name form where possible; if not possible, transliterate.
"""

_FEW_SHOT_EXAMPLES = """
--- EXAMPLE 1 ---
INPUT:
Dear Customer,
Thank you for your order from Amazon.in
Order #405-9812345-0123456 placed on August 15, 2025.
1 x Sony WH-1000XM5 Wireless Headphones (Black)
Order Total: ₹28,990.00
1-year manufacturer's warranty included.
Return within 30 days of delivery.

OUTPUT:
{"product_name": "Sony WH-1000XM5 Wireless Headphones (Black)", "brand": "Sony", "retailer": "Amazon.in", "purchase_date": "2025-08-15", "price": 28990.00, "warranty_period_months": 12, "return_window_days": 30, "confidence": "high"}

--- EXAMPLE 2 ---
INPUT:
Hi Ananya,
Your Flipkart order OD126789012345678901 has been confirmed.
Order Date: 10 September 2025
Boat Airdopes 411 Pro True Wireless Earbuds
₹1,799
7-day replacement guarantee.

OUTPUT:
{"product_name": "Boat Airdopes 411 Pro True Wireless Earbuds", "brand": "Boat", "retailer": "Flipkart", "purchase_date": "2025-09-10", "price": 1799.00, "warranty_period_months": null, "return_window_days": 7, "confidence": "high"}

--- EXAMPLE 3 (uncertain — model must say low) ---
INPUT:
Thanks for shopping with us. Your item will be dispatched shortly.
Total charged: ₹3,500

OUTPUT:
{"product_name": null, "brand": null, "retailer": null, "purchase_date": null, "price": 3500.00, "warranty_period_months": null, "return_window_days": null, "confidence": "low"}

--- EXAMPLE 4 (Hindi / Hinglish — extract fields into English-keyed JSON) ---
INPUT:
प्रिय ग्राहक,
आपका Meesho ऑर्डर confirm ho gaya hai.
ऑर्डर ID: 987654321012
उत्पाद: Samsung Galaxy Buds2 Pro (Graphite)
कुल राशि: ₹8,999
ऑर्डर दिनांक: 3 सितम्बर 2025
7 दिन वापसी नीति लागू है.

OUTPUT:
{"product_name": "Samsung Galaxy Buds2 Pro (Graphite)", "brand": "Samsung", "retailer": "Meesho", "purchase_date": "2025-09-03", "price": 8999.00, "warranty_period_months": null, "return_window_days": 7, "confidence": "high"}

--- END EXAMPLES ---
"""

_USER_PROMPT_TEMPLATE = """\
{few_shot}

Now extract from the following text:

INPUT:
{text}

OUTPUT:"""


# ── Main extraction function ──────────────────────────────────────────────────

def extract_with_llm(text: str) -> Optional[ExtractionResult]:
    """
    Send text to Claude and parse the structured JSON response.

    Args:
        text: Cleaned email/document text (not stored anywhere after this call).

    Returns:
        ExtractionResult with pass_used='llm', or None if the API call fails
        or the response is not valid JSON matching the schema.
    """
    if not _ANTHROPIC_API_KEY:
        logger.warning(
            "ANTHROPIC_API_KEY not set — LLM extraction fallback disabled. "
            "Set the key in .env to enable it."
        )
        return None

    # Truncate very long documents to avoid hitting context limits / cost
    max_chars = 8_000
    truncated_text = text[:max_chars]
    if len(text) > max_chars:
        logger.info("LLM input truncated from %d to %d chars", len(text), max_chars)

    user_prompt = _USER_PROMPT_TEMPLATE.format(
        few_shot=_FEW_SHOT_EXAMPLES,
        text=truncated_text,
    )

    client = anthropic.Anthropic(api_key=_ANTHROPIC_API_KEY)

    try:
        response = client.messages.create(
            model=_MODEL,
            max_tokens=512,
            timeout=_ANTHROPIC_TIMEOUT,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.APITimeoutError:
        logger.error(
            "Anthropic API timed out after %.0f seconds — skipping LLM extraction",
            _ANTHROPIC_TIMEOUT,
        )
        return None
    except anthropic.APIStatusError as exc:
        logger.error("Anthropic API error (status %s): %s", exc.status_code, exc.message)
        return None
    except Exception as exc:
        logger.error("Unexpected error calling Anthropic API: %s", exc)
        return None

    raw_content = response.content[0].text if response.content else ""
    return _parse_llm_response(raw_content)


def _parse_llm_response(raw: str) -> Optional[ExtractionResult]:
    """
    Parse Claude's raw text output into an ExtractionResult.

    Handles:
    - Clean JSON
    - JSON wrapped in markdown code fences (```json ... ```)
    - Partial / malformed JSON (logs error, returns None)
    """
    # Strip possible markdown code fences
    clean = raw.strip()
    if clean.startswith("```"):
        lines = clean.splitlines()
        clean = "\n".join(
            line for line in lines if not line.startswith("```")
        ).strip()

    try:
        data: dict = json.loads(clean)
    except json.JSONDecodeError as exc:
        logger.error(
            "LLM response is not valid JSON (error at char %d): %r…",
            exc.pos,
            raw[:200],
        )
        return None

    # Build ExtractionResult from the parsed dict
    result = ExtractionResult(pass_used="llm")

    result.product_name = _str_or_none(data.get("product_name"))
    result.brand = _str_or_none(data.get("brand"))
    result.retailer = _str_or_none(data.get("retailer"))
    result.price = _decimal_or_none(data.get("price"))
    result.confidence = _validated_confidence(data.get("confidence", "low"))

    raw_date = data.get("purchase_date")
    if raw_date and isinstance(raw_date, str):
        try:
            result.purchase_date = date.fromisoformat(raw_date)
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

    result.source_snippet = f"[LLM extraction — model: {_MODEL}]"

    logger.info(
        "LLM extraction complete: product=%r price=%s confidence=%s",
        result.product_name,
        result.price,
        result.confidence,
    )
    return result


# ── Helper utilities ──────────────────────────────────────────────────────────

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
    logger.warning("LLM returned unexpected confidence value %r — defaulting to 'low'", value)
    return "low"
