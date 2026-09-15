"""
Pass 1 extraction — regex / rules-based parser.

Design principles:
- Pure functions: no I/O, no side effects, easy to unit-test.
- Each retailer has its own extractor; a generic fallback is also provided.
- All functions return an ExtractionResult dataclass or None if they can't
  confidently parse the text.
- Compiled regex patterns are module-level constants for performance.

Confidence scoring:
- high   — all four key fields (product, date, price, brand/retailer) found
- medium — at least product name + price found
- low    — fewer fields found; should trigger LLM fallback
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional

from dateutil import parser as dateutil_parser

logger = logging.getLogger(__name__)


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class ExtractionResult:
    """Structured output from either extraction pass."""

    product_name: Optional[str] = None
    brand: Optional[str] = None
    retailer: Optional[str] = None
    purchase_date: Optional[date] = None
    price: Optional[Decimal] = None
    warranty_period_months: Optional[int] = None
    return_window_days: Optional[int] = None
    confidence: str = "low"          # 'high' | 'medium' | 'low'
    source_snippet: Optional[str] = None
    pass_used: str = "regex"


# ── Compiled regex patterns ───────────────────────────────────────────────────

# Amazon.in patterns
_AMZ_ORDER_ID = re.compile(r"Order\s+#?\s*(\d{3}-\d{7}-\d{7})", re.IGNORECASE)
_AMZ_PRODUCT  = re.compile(
    r"(?:Your order of|You ordered|Order Confirmation for|Items ordered)[:\s]+(.+?)(?:\n|has been|for ₹|for Rs\.)",
    re.IGNORECASE | re.DOTALL,
)
_AMZ_PRODUCT_ALT = re.compile(
    r"^\s*\d+\s+x\s+(.+?)(?:\s{2,}|₹|\n)", re.MULTILINE | re.IGNORECASE
)
_AMZ_DATE     = re.compile(
    r"(?:Order\s+date|Ordered\s+on|Placed\s+on)\s*[:\-]?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4})",
    re.IGNORECASE,
)
_AMZ_PRICE    = re.compile(
    r"(?:Order\s+Total|Grand\s+Total|Amount\s+Charged)[:\s]*(?:₹|Rs\.?|INR)\s*([\d,]+\.?\d*)",
    re.IGNORECASE,
)
_AMZ_PRICE_ALT = re.compile(
    r"(?:₹|Rs\.?|INR)\s*([\d,]+\.?\d*)\s*(?:paid|charged|total)",
    re.IGNORECASE,
)

# Flipkart patterns
_FK_ORDER_ID  = re.compile(r"OD\d{15,}", re.IGNORECASE)
_FK_PRODUCT   = re.compile(
    r"(?:Product\s+Name|Item)[:\s]+(.+?)(?:\n|Qty|Quantity|₹|Rs\.)",
    re.IGNORECASE,
)
_FK_PRODUCT_ALT = re.compile(
    r"(?:Your\s+order\s+of\s+|You\s+have\s+ordered\s+)(.+?)(?:\s+has\s+been|\n)",
    re.IGNORECASE,
)
# Bare product line: a non-blank line after the order date / price line that
# looks like a product name (starts with a capital letter, at least 5 chars)
_FK_PRODUCT_BARE = re.compile(
    r"(?:OD\d{10,}|Order\s+Date[^\n]+)\n+\s*([A-Z][^\n]{4,80}?)\s*\n",
    re.IGNORECASE | re.MULTILINE,
)
_FK_DATE      = re.compile(
    r"(?:Order\s+Date|Placed\s+on|Date\s+of\s+Order)[:\s]+(\d{1,2}\s+\w+\s+\d{4}|\d{1,2}[\-/]\w+[\-/]\d{2,4})",
    re.IGNORECASE,
)
_FK_PRICE     = re.compile(
    r"(?:Order\s+Total|Total\s+Amount|Amount\s+Payable)[:\s]*(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)",
    re.IGNORECASE,
)

# Generic patterns (used by extract_generic and as fallbacks in all extractors)
_GEN_PRICE    = re.compile(
    r"(?:₹|Rs\.?|INR|USD|\$)\s*([\d,]+\.?\d*)", re.IGNORECASE
)
_GEN_DATE     = re.compile(
    r"\b(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})\b",
    re.IGNORECASE,
)
_WARRANTY     = re.compile(
    r"(\d+)\s*[–-]?\s*(?:year|yr|month|mo)\s*(?:manufacturer'?s?\s*)?warranty",
    re.IGNORECASE,
)
_RETURN_WIN   = re.compile(
    r"(\d+)\s*[–-]?\s*(?:day|days)\s*(?:return|replacement|exchange|guarantee)",
    re.IGNORECASE,
)

# Meesho patterns
# Meesho order IDs look like: 123456789012 (12-digit numeric) or contain "meesho" in the body
_ME_ORDER_ID  = re.compile(r"(?:Order\s+ID|Order\s+#|Order\s+No\.?)[:\s]*(\d{9,14})", re.IGNORECASE)
_ME_PRODUCT   = re.compile(
    r"(?:Product\s+Name|Item\s+Name|You\s+ordered)[:\s]+(.+?)(?:\n|Qty|Quantity|₹|Rs\.)",
    re.IGNORECASE,
)
_ME_PRODUCT_ALT = re.compile(
    r"^\s*([A-Z][^\n]{4,120}?)\s*\n\s*(?:Qty|Quantity|Size|Color|₹)",
    re.IGNORECASE | re.MULTILINE,
)
_ME_DATE      = re.compile(
    r"(?:Order\s+Date|Placed\s+on|Order\s+placed)[:\s]+(\d{1,2}[\-/\s]\w+[\-/\s]\d{2,4}|\w+\s+\d{1,2},?\s+\d{4})",
    re.IGNORECASE,
)
_ME_PRICE     = re.compile(
    r"(?:Order\s+Total|Total\s+Amount|Amount\s+Paid|Grand\s+Total)[:\s]*(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)",
    re.IGNORECASE,
)

# Ajio patterns
_AJ_ORDER_ID  = re.compile(r"(?:Order\s+ID|Order\s+No\.?|Order\s+#)[:\s]*([A-Z]{2,4}\d{10,18}|FN\d{10,})", re.IGNORECASE)
_AJ_PRODUCT   = re.compile(
    r"(?:Product\s+Description|Product\s+Name|Item)[:\s]+(.+?)(?:\n|Size|Qty|₹|Rs\.)",
    re.IGNORECASE,
)
_AJ_PRODUCT_ALT = re.compile(
    r"^\s*([A-Z][^\n]{4,120}?)\s*\n\s*(?:Size|Colour|Color|Qty|₹)",
    re.IGNORECASE | re.MULTILINE,
)
_AJ_DATE      = re.compile(
    r"(?:Order\s+Date|Placed\s+on|Order\s+placed\s+on)[:\s]+(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4}|\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{1,2},?\s+\d{4})",
    re.IGNORECASE,
)
_AJ_PRICE     = re.compile(
    r"(?:Order\s+Total|Amount\s+Paid|Total\s+Payable|Grand\s+Total)[:\s]*(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)",
    re.IGNORECASE,
)


# ── Helper functions ──────────────────────────────────────────────────────────

def _clean(text: Optional[str]) -> Optional[str]:
    """Strip and collapse whitespace; return None for blank strings."""
    if not text:
        return None
    cleaned = re.sub(r"\s+", " ", text.strip())
    return cleaned or None


def _parse_price(raw: str) -> Optional[Decimal]:
    """Convert a price string like '1,299.00' to Decimal."""
    try:
        return Decimal(raw.replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def _parse_date(raw: str) -> Optional[date]:
    """Parse a date string using dateutil; return None on failure."""
    try:
        return dateutil_parser.parse(raw, dayfirst=True).date()
    except (ValueError, OverflowError):
        return None


def _score_confidence(result: ExtractionResult) -> str:
    """Compute confidence from how many key fields were successfully extracted."""
    found = sum([
        bool(result.product_name),
        bool(result.purchase_date),
        bool(result.price),
        bool(result.retailer or result.brand),
    ])
    if found >= 4:
        return "high"
    elif found >= 2:
        return "medium"
    return "low"


def _extract_warranty_and_return(text: str, result: ExtractionResult) -> None:
    """Populate warranty_period_months and return_window_days if detectable."""
    w_match = _WARRANTY.search(text)
    if w_match:
        qty = int(w_match.group(1))
        unit = w_match.group(0).lower()
        if "year" in unit or "yr" in unit:
            result.warranty_period_months = qty * 12
        else:
            result.warranty_period_months = qty

    r_match = _RETURN_WIN.search(text)
    if r_match:
        result.return_window_days = int(r_match.group(1))


# ── Amazon.in extractor ───────────────────────────────────────────────────────

def extract_amazon_in(text: str) -> Optional[ExtractionResult]:
    """
    Parse an Amazon.in order-confirmation email.

    Returns an ExtractionResult with confidence 'high'/'medium', or None if
    the text is clearly not an Amazon order email (no order ID pattern found).
    """
    if not _AMZ_ORDER_ID.search(text):
        logger.debug("extract_amazon_in: no Amazon order ID found — skipping")
        return None

    result = ExtractionResult(retailer="Amazon.in", pass_used="regex")

    # Product name
    m = _AMZ_PRODUCT.search(text)
    if m:
        result.product_name = _clean(m.group(1))
    if not result.product_name:
        m = _AMZ_PRODUCT_ALT.search(text)
        if m:
            result.product_name = _clean(m.group(1))

    # Purchase date
    m = _AMZ_DATE.search(text)
    if m:
        result.purchase_date = _parse_date(m.group(1))

    # Price
    m = _AMZ_PRICE.search(text)
    if m:
        result.price = _parse_price(m.group(1))
    if result.price is None:
        m = _AMZ_PRICE_ALT.search(text)
        if m:
            result.price = _parse_price(m.group(1))
    if result.price is None:
        # Last-resort: grab the largest ₹ amount in the email
        prices = [_parse_price(p) for p in _GEN_PRICE.findall(text)]
        valid_prices = [p for p in prices if p is not None]
        if valid_prices:
            result.price = max(valid_prices)

    # Date fallback
    if not result.purchase_date:
        m = _GEN_DATE.search(text)
        if m:
            result.purchase_date = _parse_date(m.group(1))

    # Warranty / return window
    _extract_warranty_and_return(text, result)

    # Build source snippet (first matching line with order ID)
    m_id = _AMZ_ORDER_ID.search(text)
    if m_id:
        start = max(0, m_id.start() - 50)
        end = min(len(text), m_id.end() + 100)
        result.source_snippet = text[start:end].strip()

    result.confidence = _score_confidence(result)
    logger.info(
        "Amazon.in extraction complete: product=%r price=%s confidence=%s",
        result.product_name,
        result.price,
        result.confidence,
    )
    return result


# ── Flipkart extractor ────────────────────────────────────────────────────────

def extract_flipkart(text: str) -> Optional[ExtractionResult]:
    """
    Parse a Flipkart order-confirmation email.

    Returns an ExtractionResult, or None if text is not a Flipkart email.
    """
    if not (_FK_ORDER_ID.search(text) or "flipkart" in text.lower()):
        logger.debug("extract_flipkart: not a Flipkart email — skipping")
        return None

    result = ExtractionResult(retailer="Flipkart", pass_used="regex")

    # Product name
    m = _FK_PRODUCT.search(text)
    if m:
        result.product_name = _clean(m.group(1))
    if not result.product_name:
        m = _FK_PRODUCT_ALT.search(text)
        if m:
            result.product_name = _clean(m.group(1))
    if not result.product_name:
        m = _FK_PRODUCT_BARE.search(text)
        if m:
            result.product_name = _clean(m.group(1))

    # Purchase date
    m = _FK_DATE.search(text)
    if m:
        result.purchase_date = _parse_date(m.group(1))
    if not result.purchase_date:
        m = _GEN_DATE.search(text)
        if m:
            result.purchase_date = _parse_date(m.group(1))

    # Price
    m = _FK_PRICE.search(text)
    if m:
        result.price = _parse_price(m.group(1))
    if result.price is None:
        prices = [_parse_price(p) for p in _GEN_PRICE.findall(text)]
        valid_prices = [p for p in prices if p is not None]
        if valid_prices:
            result.price = max(valid_prices)

    # Warranty / return window
    _extract_warranty_and_return(text, result)

    # Source snippet
    m_id = _FK_ORDER_ID.search(text)
    if m_id:
        start = max(0, m_id.start() - 50)
        end = min(len(text), m_id.end() + 100)
        result.source_snippet = text[start:end].strip()

    result.confidence = _score_confidence(result)
    logger.info(
        "Flipkart extraction complete: product=%r price=%s confidence=%s",
        result.product_name,
        result.price,
        result.confidence,
    )
    return result


# ── Meesho extractor ─────────────────────────────────────────────────────────

def extract_meesho(text: str) -> Optional[ExtractionResult]:
    """
    Parse a Meesho order-confirmation email.

    Returns an ExtractionResult, or None if text is not a Meesho email.
    """
    if "meesho" not in text.lower():
        logger.debug("extract_meesho: not a Meesho email — skipping")
        return None

    result = ExtractionResult(retailer="Meesho", pass_used="regex")

    # Product name
    m = _ME_PRODUCT.search(text)
    if m:
        result.product_name = _clean(m.group(1))
    if not result.product_name:
        m = _ME_PRODUCT_ALT.search(text)
        if m:
            result.product_name = _clean(m.group(1))

    # Purchase date
    m = _ME_DATE.search(text)
    if m:
        result.purchase_date = _parse_date(m.group(1))
    if not result.purchase_date:
        m = _GEN_DATE.search(text)
        if m:
            result.purchase_date = _parse_date(m.group(1))

    # Price
    m = _ME_PRICE.search(text)
    if m:
        result.price = _parse_price(m.group(1))
    if result.price is None:
        prices = [_parse_price(p) for p in _GEN_PRICE.findall(text)]
        valid_prices = [p for p in prices if p is not None]
        if valid_prices:
            result.price = max(valid_prices)

    # Warranty / return window
    _extract_warranty_and_return(text, result)

    # Source snippet around order ID (or start of email)
    m_id = _ME_ORDER_ID.search(text)
    if m_id:
        start = max(0, m_id.start() - 50)
        end = min(len(text), m_id.end() + 100)
        result.source_snippet = text[start:end].strip()

    result.confidence = _score_confidence(result)
    logger.info(
        "Meesho extraction complete: product=%r price=%s confidence=%s",
        result.product_name,
        result.price,
        result.confidence,
    )
    return result


# ── Ajio extractor ────────────────────────────────────────────────────────────

def extract_ajio(text: str) -> Optional[ExtractionResult]:
    """
    Parse an Ajio order-confirmation email.

    Returns an ExtractionResult, or None if text is not an Ajio email.
    """
    if not (_AJ_ORDER_ID.search(text) or "ajio" in text.lower()):
        logger.debug("extract_ajio: not an Ajio email — skipping")
        return None

    result = ExtractionResult(retailer="Ajio", pass_used="regex")

    # Product name
    m = _AJ_PRODUCT.search(text)
    if m:
        result.product_name = _clean(m.group(1))
    if not result.product_name:
        m = _AJ_PRODUCT_ALT.search(text)
        if m:
            result.product_name = _clean(m.group(1))

    # Purchase date
    m = _AJ_DATE.search(text)
    if m:
        result.purchase_date = _parse_date(m.group(1))
    if not result.purchase_date:
        m = _GEN_DATE.search(text)
        if m:
            result.purchase_date = _parse_date(m.group(1))

    # Price
    m = _AJ_PRICE.search(text)
    if m:
        result.price = _parse_price(m.group(1))
    if result.price is None:
        prices = [_parse_price(p) for p in _GEN_PRICE.findall(text)]
        valid_prices = [p for p in prices if p is not None]
        if valid_prices:
            result.price = max(valid_prices)

    # Warranty / return window
    _extract_warranty_and_return(text, result)

    # Source snippet
    m_id = _AJ_ORDER_ID.search(text)
    if m_id:
        start = max(0, m_id.start() - 50)
        end = min(len(text), m_id.end() + 100)
        result.source_snippet = text[start:end].strip()

    result.confidence = _score_confidence(result)
    logger.info(
        "Ajio extraction complete: product=%r price=%s confidence=%s",
        result.product_name,
        result.price,
        result.confidence,
    )
    return result


# ── Generic extractor ─────────────────────────────────────────────────────────

def extract_generic(text: str) -> ExtractionResult:
    """
    Last-resort regex pass for any email/document not matched by retailer extractors.

    Always returns an ExtractionResult (never None), but confidence will be 'low'
    unless price + date were both found — in which case it's 'medium'.
    This result should almost always trigger LLM fallback.
    """
    result = ExtractionResult(pass_used="regex")

    # Best-effort price
    prices = [_parse_price(p) for p in _GEN_PRICE.findall(text)]
    valid_prices = [p for p in prices if p is not None]
    if valid_prices:
        result.price = max(valid_prices)

    # Best-effort date
    m = _GEN_DATE.search(text)
    if m:
        result.purchase_date = _parse_date(m.group(1))

    # Warranty / return window
    _extract_warranty_and_return(text, result)

    result.confidence = _score_confidence(result)
    logger.info(
        "Generic extraction: price=%s date=%s confidence=%s",
        result.price,
        result.purchase_date,
        result.confidence,
    )
    return result


# ── Two-pass orchestrator (Pass 1 only) ──────────────────────────────────────

def run_regex_pass(text: str, hint: Optional[str] = None) -> ExtractionResult:
    """
    Run all regex extractors and return the best result.

    Args:
        text: Raw email/document text.
        hint: Optional source hint ('amazon', 'flipkart', etc.) to try that
              extractor first. Falls through to others if hint extractor fails.

    Returns:
        ExtractionResult — confidence will be 'low' if nothing useful was found,
        which should trigger the LLM fallback.
    """
    extractors = {
        "amazon": extract_amazon_in,
        "flipkart": extract_flipkart,
        "meesho": extract_meesho,
        "ajio": extract_ajio,
    }

    ordered: list = []
    if hint and hint.lower() in extractors:
        ordered.append(extractors[hint.lower()])
        ordered.extend([v for k, v in extractors.items() if k != hint.lower()])
    else:
        ordered = list(extractors.values())

    for extractor in ordered:
        result = extractor(text)
        if result is not None:
            return result

    # No retailer matched — run generic
    return extract_generic(text)
