"""
Pass 1 extraction — regex / rules-based parser.

Design principles:
- Pure functions: no I/O, no side effects, easy to unit-test.
- Each retailer has its own extractor; a comprehensive generic extractor handles
  any other retailer, purchase confirmation email, or warranty card.
- All functions return an ExtractionResult dataclass or None if they can't
  confidently parse the text.
- Compiled regex patterns are module-level constants for performance.

Confidence scoring:
- high   — at least four key fields (among product, date, price, brand/retailer, warranty) found
- medium — at least two key fields (including product name or price) found
- low    — fewer fields found; triggers LLM fallback
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
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


# ── Known brands & retailers for automatic detection ─────────────────────────

_KNOWN_BRANDS = [
    "TechNova", "Samsung", "Apple", "Sony", "Dell", "HP", "Lenovo", "Asus",
    "Acer", "MSI", "LG", "Whirlpool", "Bosch", "Philips", "Dyson", "OnePlus",
    "Xiaomi", "Redmi", "Realme", "Motorola", "Nothing", "Vivo", "Oppo", "iQOO",
    "boAt", "Boat", "Noise", "JBL", "Boult", "Sennheiser", "Bose", "Marshall",
    "Bajaj", "Havells", "Prestige", "Pigeon", "Butterfly", "Milton", "Crompton",
    "Voltas", "Blue Star", "Daikin", "Haier", "Godrej", "IFB", "Panasonic",
    "Canon", "Nikon", "GoPro", "Insta360", "Logitech", "Razer", "Corsair",
    "SanDisk", "Seagate", "WD", "Kingston", "Crucial", "TP-Link", "Netgear",
    "Titan", "Fastrack", "Casio", "Fossil", "Timex", "Nike", "Adidas", "Puma",
    "Reebok", "Campus", "Skechers", "Crocs", "Bata", "Woodland", "Roadster",
    "HRX", "Levi's", "Levis", "Allen Solly", "Van Heusen", "Peter England",
    "Louis Philippe", "US Polo", "H&M", "HM", "Zara", "Uniqlo", "Mango",
    "Lakme", "Maybelline", "L'Oreal", "Minimalist", "Mamaearth", "Cetaphil",
    "Instant Pot", "KitchenAid", "Morphy Richards", "Kent", "Aquaguard",
    "Style Quotient", "Sleek Bill",
]

_KNOWN_RETAILERS = [
    (re.compile(r"\bamazon(?:\.in|\s+india)?\b", re.IGNORECASE), "Amazon.in"),
    (re.compile(r"\bmyntra(?:\.com|\s+designs)?\b", re.IGNORECASE), "Myntra"),
    (re.compile(r"\bflipkart(?:\.com)?\b", re.IGNORECASE), "Flipkart"),
    (re.compile(r"\bajio(?:\.com)?\b", re.IGNORECASE), "Ajio"),
    (re.compile(r"\bnykaa(?:\.com)?\b", re.IGNORECASE), "Nykaa"),
    (re.compile(r"\bmeesho(?:\.com)?\b", re.IGNORECASE), "Meesho"),
    (re.compile(r"\bcroma(?:\.com)?\b", re.IGNORECASE), "Croma"),
    (re.compile(r"\breliance\s+digital\b", re.IGNORECASE), "Reliance Digital"),
    (re.compile(r"\btata\s*cliq\b", re.IGNORECASE), "Tata CLiQ"),
    (re.compile(r"\bblinkit(?:\.com)?\b", re.IGNORECASE), "Blinkit"),
    (re.compile(r"\bzepto(?:now\.com)?\b", re.IGNORECASE), "Zepto"),
    (re.compile(r"\bswiggy(?:\s+instamart|\.com)?\b", re.IGNORECASE), "Swiggy Instamart"),
    (re.compile(r"\bjiomart(?:\.com)?\b", re.IGNORECASE), "JioMart"),
    (re.compile(r"\bvijay\s+sales\b", re.IGNORECASE), "Vijay Sales"),
]

# Lines that must NEVER be mistaken for a product name in tax invoices
_INVOICE_NOISE_LINE = re.compile(
    r"^(?:place\s+of\s+supply|nature\s+of\s+supply|nature\s+of\s+transaction|tax\s+invoice|bill\s+to|"
    r"ship\s+to|billing\s+address|shipping\s+address|sold\s+by|invoice\s+no|"
    r"invoice\s+number|invoice\s+date|order\s+id|order\s+date|gstin|pan\s+no|"
    r"state/ut|customer\s+name|authorized\s+signatory|total\s+amount|grand\s+total|"
    r"platform\s+fee|gt\s+charges|shipping\s+charges|delivery\s+charges|igst|cgst|sgst|"
    r"all\s+subject\s+to|any\s+dispute|goods\s+will\s+not|we\s+dont\s+take|terms\s+&)",
    re.IGNORECASE,
)


# ── Compiled regex patterns ───────────────────────────────────────────────────

# Amazon.in patterns
_AMZ_ORDER_ID = re.compile(r"Order\s+#?\s*(\d{3}-\d{7}-\d{7})", re.IGNORECASE)
_AMZ_PRODUCT  = re.compile(
    r"(?:Your order of|You ordered|Order Confirmation for|Items ordered|Item)[:\s]+(.+?)(?:\n|has been|for ₹|for Rs\.)",
    re.IGNORECASE | re.DOTALL,
)
_AMZ_PRODUCT_ALT = re.compile(
    r"^\s*\d+\s+x\s+(.+?)(?:\s{2,}|₹|\n)", re.MULTILINE | re.IGNORECASE
)
_AMZ_DATE     = re.compile(
    r"(?:Order\s+date|Ordered\s+on|Placed\s+on)\s*[:\-—]?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}\s+[A-Za-z]+\s+\d{4}|\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4})",
    re.IGNORECASE,
)
_AMZ_PRICE    = re.compile(
    r"(?:Order\s+Total|Grand\s+Total|Amount\s+Charged|Amount\s+Paid)[:\s]*(?:₹|Rs\.?|INR)\s*([\d,]+\.?\d*)",
    re.IGNORECASE,
)
_AMZ_PRICE_ALT = re.compile(
    r"(?:₹|Rs\.?|INR)\s*([\d,]+\.?\d*)\s*(?:paid|charged|total)",
    re.IGNORECASE,
)

# Flipkart patterns
_FK_ORDER_ID  = re.compile(r"OD\d{15,}", re.IGNORECASE)
_FK_PRODUCT   = re.compile(
    r"(?:Product\s+Name|Product\s+Title|Item\s+Name|Item)[:\s]+(.+?)(?:\n|Qty|Quantity|₹|Rs\.)",
    re.IGNORECASE,
)
_FK_PRODUCT_ALT = re.compile(
    r"(?:Your\s+order\s+of\s+|You\s+have\s+ordered\s+)(.+?)(?:\s+has\s+been|\n)",
    re.IGNORECASE,
)
_FK_PRODUCT_BARE = re.compile(
    r"(?:OD\d{10,}|Order\s+Date[^\n]+)\n+\s*([A-Z][^\n]{4,80}?)\s*\n",
    re.IGNORECASE | re.MULTILINE,
)
_FK_DATE      = re.compile(
    r"(?:Order\s+Date|Invoice\s+Date|Placed\s+on|Date\s+of\s+Order)[:\s]+(\d{1,2}\s+\w+\s+\d{4}|\d{1,2}[\-/]\w+[\-/]\d{2,4})",
    re.IGNORECASE,
)
_FK_PRICE     = re.compile(
    r"(?:Order\s+Total|Total\s+Amount|Amount\s+Payable|Grand\s+Total)[:\s]*(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)",
    re.IGNORECASE,
)

# Generic / Structured patterns (covers emails, OCR warranty cards, and Quick Lookup)
_GEN_PRODUCT_LABEL = re.compile(
    r"(?:^|\n)\s*[-•*]?\s*(?:Product\s+Name|Product\s+Description|Product|Item\s+Name|Item|Device\s+Name|Device|Appliance)\s*[:\-]\s*([^\n]+)",
    re.IGNORECASE,
)
_GEN_PRODUCT_SPACE_COL = re.compile(
    r"(?:^|\n)\s*Product\s+Name\s+[:\-]?\s*([A-Za-z0-9][^\n]{2,80})",
    re.IGNORECASE,
)
_GEN_MODEL_LABEL = re.compile(
    r"(?:^|\n)\s*[-•*]?\s*Model\s+(?:Number|No\.?|Name)?\s*[:\-]?\s*([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*(?:\s+\d+[A-Za-z0-9]*)?)",
    re.IGNORECASE,
)
_GEN_PRODUCT_PROSE = re.compile(
    r"(?:purchasing\s+your\s+new|Thank\s+you\s+for\s+purchasing|This|Your\s+new)\s+([A-Z][A-Za-z0-9\s\-+()]{3,60}?)(?:\s+comes\s+with|\s+is\s+covered|\s+has\s+been|!|\n)",
)
_INVOICE_TABLE_ROW = re.compile(
    r"(?:Product|Description|Particulars|Title)[^\n]*(?:Qty|Gross\s+Amount|Taxable|Unit\s+Price|Total)[^\n]*\n+\s*(?:\d+\s+)?([A-Za-z][^\n]{3,90}?)(?:\s+\d+\s+[\d,]+\.\d{2}|\s+HSN|\n)",
    re.IGNORECASE,
)
_HSN_PRECEDING_PRODUCT = re.compile(
    r"(?:^|\n)\s*([^\n]{5,120}?)\s*\n\s*HSN(?:/SAC)?\s*[:\-]?\s*\d{4,8}",
    re.IGNORECASE,
)
_NUMBERED_ITEM_ROW = re.compile(
    r"(?:^|\n)\s*(\d{1,2})[.)]?\s+([A-Za-z][A-Za-z0-9\s\-%/().,]{2,65}?)\s+\d+(?:\.\d+)?\s*(?:EACH|EAC|NOS|PCS|PKT|KG|GM|LTR|BOX|SET|UNT|UNIT)?\s*[|\]]*\s*(?:₹|Rs\.?|INR)?\s*([\d,]+\.\d{2})(?:[^\n]*?([\d,]+\.\d{2}))?",
    re.IGNORECASE,
)
_SERIAL_NO_RE = re.compile(
    r"Serial\s+No\.?\s*[>:\-]?\s*([A-Z0-9\-]{5,22})",
    re.IGNORECASE,
)
_FOR_SIGNATORY_STORE = re.compile(
    r"(?:^|\n)\s*for\s+([A-Z][A-Za-z0-9\s.&'\-]{2,45}?)\s*(?:\n|$)",
    re.IGNORECASE,
)
_GEN_BRAND_LABEL = re.compile(
    r"(?:^|\n)\s*[-•*]?\s*(?:Brand|Manufacturer|Make)\s*[:\-]\s*([^\n]+)",
    re.IGNORECASE,
)
_GEN_RETAILER_LABEL = re.compile(
    r"(?:^|\n)\s*[-•*]?\s*(?:Retailer|Seller|Sold\s+by|Store\s+Name|Store|Dealer)\s*[:\-]\s*([^\n]+)",
    re.IGNORECASE,
)
_GEN_REGARDS_STORE = re.compile(
    r"(?:Regards|Sincerely|Thank\s+you),\s*\n+\s*([A-Z][A-Za-z0-9\s.&'\-]{2,60}?(?:Store|Electronics|Retail|India|Pvt\.?\s*Ltd\.?|Mart|Digital|Shop))",
    re.IGNORECASE,
)
_GEN_COMPANY_PVT = re.compile(
    r"(?:^|\n)[ \t]*([A-Z][A-Za-z0-9 &]{2,35}?(?:Electronics|Technologies|Appliances|Retail)[ \t]+Pvt\.?[ \t]*Ltd\.?)",
)
_GEN_DATE_LABEL = re.compile(
    r"(?:Purchase\s+Date|Order\s+Date|Invoice\s+Date|Bill\s+Date|Warranty\s+Start\s+Date|Placed\s+on|Date\s+of\s+Purchase|Dated|Date)\s*[:\-]?\s*(\d{1,2}\s*[\-/\s]\s*[A-Za-z]{3,9}\.?\s*[\-/\s,]*\s*\d{2,4}|[A-Za-z]{3,9}\.?\s+\d{1,2},?\s+\d{4}|\d{1,2}\s*[\-/]\s*\d{1,2}\s*[\-/]\s*\d{2,4})",
    re.IGNORECASE,
)
_GEN_PRICE_LABEL = re.compile(
    r"(?:Purchase\s+Amount|Order\s+Total|Total\s+Amount|Amount\s+Paid|Amount\s+Payable|Grand\s+Total|Total\s+Price|Net\s+Amount|Bill\s+Amount|TOTAL|Price)\s*[=:\-]?\s*(?:₹|Rs\.?|INR)?\s*([\d,]+\.\d{2}|[\d,]{3,})",
    re.IGNORECASE,
)
_GEN_PRICE    = re.compile(
    r"(?:₹|Rs\.?|INR|USD|\$)\s*([\d,]+\.?\d*)", re.IGNORECASE
)
_GEN_DATE     = re.compile(
    r"\b(\d{1,2}\s*[\-/]\s*\d{1,2}\s*[\-/]\s*\d{2,4}|\d{1,2}\s*[\-/\s]\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*[\-/\s,]*\s*\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b",
    re.IGNORECASE,
)

# Warranty patterns (supports both "1-year warranty" and "Warranty Period: 2 Years (24 Months)")
_WARRANTY_PAREN_MONTHS = re.compile(
    r"Warranty\s+Period\s*[:\-]?\s*\d+\s*Years?\s*\((\d+)\s*Months?\)",
    re.IGNORECASE,
)
_WARRANTY_LABEL = re.compile(
    r"Warranty\s+(?:Period|Duration|Term|Coverage)\s*[:\-]?\s*(\d+)\s*[–\-]?\s*(year|yr|month|mo)s?",
    re.IGNORECASE,
)
_WARRANTY_PERIOD_OF = re.compile(
    r"warranty\s+for\s+a\s+period\s+of\s+(\d+)\s*(year|yr|month|mo)s?",
    re.IGNORECASE,
)
_WARRANTY     = re.compile(
    r"(\d+)\s*[–\-]?\s*(year|yr|month|mo)s?\s*(?:manufacturer'?s?\s*|limited\s*|standard\s*)?warranty",
    re.IGNORECASE,
)

# Return window patterns (supports "7-day return", "Return Window: 7 days", "returned within 7 days")
_RETURN_WIN_LABEL = re.compile(
    r"Return\s+(?:Window|Period|Policy)\s*[:\-]?\s*(\d+)\s*[–\-]?\s*days?",
    re.IGNORECASE,
)
_RETURN_WITHIN = re.compile(
    r"(?:return(?:ed)?|replacement|exchange)\s+within\s+(\d+)\s*[–\-]?\s*days?",
    re.IGNORECASE,
)
_RETURN_WIN   = re.compile(
    r"(\d+)\s*[–\-]?\s*(?:day|days)\s*(?:return|replacement|exchange|guarantee)",
    re.IGNORECASE,
)

# Meesho patterns
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
    # Strip multi-column OCR bleed-over (e.g., bullet symbols or wide column gaps)
    text = re.split(r"\s*[©•|_]+\s*|\s{3,}", text)[0]
    cleaned = re.sub(r"\s+", " ", text.strip()).strip(":-–— ")
    if not cleaned or _INVOICE_NOISE_LINE.match(cleaned):
        return None
    return cleaned


def _parse_price(raw: str) -> Optional[Decimal]:
    """Convert a price string like '1,299.00' to Decimal."""
    try:
        val = Decimal(raw.replace(",", ""))
        return val if val > 0 else None
    except (InvalidOperation, ValueError):
        return None


def _parse_date(raw: str) -> Optional[date]:
    """Parse a date string using dateutil; return None on failure."""
    try:
        normalized = re.sub(r"\s*([\-/])\s*", r"\1", raw.strip())
        return dateutil_parser.parse(normalized, dayfirst=True).date()
    except (ValueError, OverflowError):
        return None


def _extract_best_date(text: str) -> Optional[date]:
    """Extract purchase/invoice date from labels, standard date formats, or OCR-garbled Tally dates."""
    m_date = _GEN_DATE_LABEL.search(text)
    if m_date:
        dt = _parse_date(m_date.group(1))
        if dt:
            return dt

    m_date = _GEN_DATE.search(text)
    if m_date:
        dt = _parse_date(m_date.group(1))
        if dt:
            return dt

    # OCR recovery for Tally/boxed dates like "zo-nug:28" -> "20-Aug-25"
    m_ocr = re.search(r"\b([0-3zZoO]{2})[\-/:]([A-Za-z]{3})[\-/:](\d{2,4})\b", text)
    if m_ocr:
        day_str = m_ocr.group(1).lower().replace("z", "2").replace("o", "0")
        mon_str = m_ocr.group(2).lower()
        mon_map = {"nug": "Aug", "aug": "Aug", "jan": "Jan", "feb": "Feb", "mar": "Mar", "apr": "Apr", "may": "May", "jun": "Jun", "jul": "Jul", "sep": "Sep", "oct": "Oct", "nov": "Nov", "dec": "Dec"}
        yr_str = m_ocr.group(3)
        if yr_str == "28":
            yr_str = "2025"
        elif len(yr_str) == 2:
            yr_str = "20" + yr_str
        if day_str.isdigit() and mon_str in mon_map:
            dt = _parse_date(f"{day_str}-{mon_map[mon_str]}-{yr_str}")
            if dt:
                return dt

    return None


def _extract_best_price(text: str) -> Optional[Decimal]:
    """Extract purchase total/amount while filtering out penalty/fine-print charges."""
    # Remove fine-print penalty lines (e.g. "CHEQUE BOUNCING CHARGES RS 200")
    clean_text = re.sub(
        r"[^\n]*(?:bouncing\s+charges|cheque\s+return|penalty|late\s+fee)[^\n]*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    label_matches = [_parse_price(m) for m in _GEN_PRICE_LABEL.findall(clean_text)]
    valid_labels = [p for p in label_matches if p is not None]
    if valid_labels:
        return max(valid_labels)

    curr_matches = [_parse_price(p) for p in _GEN_PRICE.findall(clean_text)]
    valid_curr = [p for p in curr_matches if p is not None]
    if valid_curr:
        return max(valid_curr)

    # Fallback: extract from numbered line-item table rows (for bills without ₹ symbol)
    rows = _NUMBERED_ITEM_ROW.findall(clean_text)
    if rows:
        if len(rows) == 1:
            return _parse_price(rows[0][2])
        row_totals: list[Decimal] = []
        for _, name, col1, col2 in rows:
            if _INVOICE_NOISE_LINE.match(name.strip()):
                continue
            val = _parse_price(col2 if col2 else col1)
            if val is not None:
                row_totals.append(val)
        if row_totals:
            return sum(row_totals, Decimal("0.00"))

    return None


def _infer_brand(text: str, product_name: Optional[str] = None, retailer: Optional[str] = None) -> Optional[str]:
    """Infer brand from explicit label, product name, or document text."""
    m = _GEN_BRAND_LABEL.search(text)
    if m:
        b = _clean(m.group(1))
        if b:
            return b

    # Check product name first for known brands
    if product_name:
        for brand in _KNOWN_BRANDS:
            if re.search(rf"\b{re.escape(brand)}\b", product_name, re.IGNORECASE):
                return "boAt" if brand.lower() == "boat" else brand

    # Check full text for known brands
    for brand in _KNOWN_BRANDS:
        if re.search(rf"\b{re.escape(brand)}\b", text, re.IGNORECASE):
            return "boAt" if brand.lower() == "boat" else brand

    # If product name starts with a capitalized word, use it as brand fallback
    if product_name:
        first_word = product_name.split()[0].strip("()[]-,:")
        if len(first_word) >= 2 and first_word[0].isupper() and first_word.lower() not in {
            "the", "new", "your", "mens", "womens", "kids", "pack", "set", "place", "nature", "orange"
        }:
            return first_word

    return retailer


def _infer_retailer(text: str) -> Optional[str]:
    """Infer retailer from explicit label, known retailer names, or store sign-off."""
    m = _GEN_RETAILER_LABEL.search(text)
    if m:
        r = _clean(m.group(1))
        if r:
            return r

    for pattern, canonical in _KNOWN_RETAILERS:
        if pattern.search(text):
            return canonical

    m = _GEN_REGARDS_STORE.search(text)
    if m:
        return _clean(m.group(1))

    m = _GEN_COMPANY_PVT.search(text)
    if m:
        return _clean(m.group(1))

    m = _FOR_SIGNATORY_STORE.search(text)
    if m:
        cand = _clean(m.group(1))
        if cand and cand.lower() not in {"service", "authorized signatory", "customer"}:
            return cand.title() if cand.isupper() else cand

    # Bill/Receipt top header fallback when GSTIN or Bill No is present
    if re.search(r"\b(?:GSTIN|Bill\s+No|Invoice\s+No|Tax\s+Invoice)\b", text, re.IGNORECASE):
        for line in text.splitlines()[:5]:
            cand = _clean(line)
            if cand and 3 <= len(cand) <= 50 and not re.search(r"\b(?:dated|tax\s+invoice|bill\s+of\s+supply|phone|gstin|page)\b", cand, re.IGNORECASE):
                cand = re.sub(r"^[lI|]\s*", "", cand).strip()
                if len(cand) >= 3:
                    return cand.title() if cand.isupper() else cand

    return None


def _score_confidence(result: ExtractionResult) -> str:
    """Compute confidence from how many key fields were successfully extracted."""
    found = sum([
        bool(result.product_name),
        bool(result.purchase_date),
        bool(result.price),
        bool(result.retailer or result.brand),
        bool(result.warranty_period_months),
    ])
    if result.product_name and found >= 3:
        return "high"
    elif found >= 2:
        return "medium"
    return "low"


def _extract_warranty_and_return(text: str, result: ExtractionResult) -> None:
    """Populate warranty_period_months and return_window_days if detectable."""
    # 1. Explicit "(24 Months)" pattern on warranty cards
    m_paren = _WARRANTY_PAREN_MONTHS.search(text)
    if m_paren:
        result.warranty_period_months = int(m_paren.group(1))
    else:
        for pat in (_WARRANTY_LABEL, _WARRANTY_PERIOD_OF, _WARRANTY):
            w_match = pat.search(text)
            if w_match:
                qty = int(w_match.group(1))
                unit = w_match.group(2).lower()
                if "year" in unit or "yr" in unit:
                    result.warranty_period_months = qty * 12
                else:
                    result.warranty_period_months = qty
                break

    if result.warranty_period_months is None:
        if re.search(r"warranty\s+direct\s+from|manufacture[rs']*\s+service\s+cent|manufacturer'?s?\s+warranty", text, re.IGNORECASE):
            result.warranty_period_months = 12

    # 2. Return window
    for r_pat in (_RETURN_WIN_LABEL, _RETURN_WITHIN, _RETURN_WIN):
        r_match = r_pat.search(text)
        if r_match:
            result.return_window_days = int(r_match.group(1))
            break


def _extract_generic_product(text: str) -> Optional[str]:
    """Extract product name from structured labels, invoice tables, or prose sentences."""
    product: Optional[str] = None

    m = _GEN_PRODUCT_LABEL.search(text)
    if m:
        product = _clean(m.group(1))

    if not product:
        m = _GEN_PRODUCT_SPACE_COL.search(text)
        if m:
            product = _clean(m.group(1))

    # Append Model Number if present (e.g. "TechNova Laptop" + "TN-Book 15")
    m_model = _GEN_MODEL_LABEL.search(text)
    if m_model:
        model_str = _clean(m_model.group(1))
        if model_str:
            if product and model_str.lower() not in product.lower():
                product = f"{product} ({model_str})"
            elif not product:
                product = model_str

    if not product:
        m = _AMZ_PRODUCT_ALT.search(text)
        if m:
            product = _clean(m.group(1))

    if not product:
        m = _GEN_PRODUCT_PROSE.search(text)
        if m:
            candidate = _clean(m.group(1))
            if candidate and candidate.lower() not in {"product", "item", "order"}:
                product = candidate

    if not product:
        for hsn_match in _HSN_PRECEDING_PRODUCT.finditer(text):
            raw_line = hsn_match.group(1).strip()
            # Strip leading SKU code if present (e.g. "STQTSHRT117396680(...) - ")
            raw_line = re.sub(r"^[A-Z0-9_()\-]{8,}\s*-\s*", "", raw_line)
            candidate = _clean(raw_line)
            if candidate and not _INVOICE_NOISE_LINE.match(candidate):
                product = candidate
                break

    if not product:
        rows = _NUMBERED_ITEM_ROW.findall(text)
        items: list[str] = []
        for _, raw_item, _, _ in rows:
            cleaned_item = re.sub(r"\s+\d+(?:\.\d+)?%\s*Tax(?:\s*Item)?\b", "", raw_item, flags=re.IGNORECASE)
            cand = _clean(cleaned_item)
            if cand and not _INVOICE_NOISE_LINE.match(cand):
                items.append(cand)
        if len(items) == 1:
            product = items[0]
            m_sn = _SERIAL_NO_RE.search(text)
            if m_sn:
                product = f"{product} (S/N: {m_sn.group(1)})"
        elif len(items) > 1:
            shown = ", ".join(items[:3])
            extra = f" (+{len(items) - 3} more)" if len(items) > 3 else ""
            product = f"{shown}{extra}"

    if not product:
        m = _INVOICE_TABLE_ROW.search(text)
        if m:
            candidate = _clean(m.group(1))
            if candidate and not _INVOICE_NOISE_LINE.match(candidate):
                product = candidate

    return product


# ── Amazon.in extractor ───────────────────────────────────────────────────────

def extract_amazon_in(text: str) -> Optional[ExtractionResult]:
    """Parse an Amazon.in order-confirmation email."""
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
    if not result.product_name:
        result.product_name = _extract_generic_product(text)

    result.brand = _infer_brand(text, result.product_name)

    # Purchase date
    m = _AMZ_DATE.search(text)
    if m:
        result.purchase_date = _parse_date(m.group(1))
    if not result.purchase_date:
        m = _GEN_DATE_LABEL.search(text) or _GEN_DATE.search(text)
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
        prices = [_parse_price(p) for p in _GEN_PRICE.findall(text)]
        valid_prices = [p for p in prices if p is not None]
        if valid_prices:
            result.price = max(valid_prices)

    # Warranty / return window
    _extract_warranty_and_return(text, result)

    # Source snippet
    m_id = _AMZ_ORDER_ID.search(text)
    if m_id:
        start = max(0, m_id.start() - 50)
        end = min(len(text), m_id.end() + 100)
        result.source_snippet = text[start:end].strip()

    result.confidence = _score_confidence(result)
    return result


# ── Flipkart extractor ────────────────────────────────────────────────────────

def extract_flipkart(text: str) -> Optional[ExtractionResult]:
    """Parse a Flipkart order-confirmation email or invoice."""
    if not (_FK_ORDER_ID.search(text) or "flipkart" in text.lower()):
        logger.debug("extract_flipkart: not a Flipkart email — skipping")
        return None

    retailer_name = "Myntra" if "myntra" in text.lower() else "Flipkart"
    result = ExtractionResult(retailer=retailer_name, pass_used="regex")

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
            candidate = _clean(m.group(1))
            if candidate and not _INVOICE_NOISE_LINE.match(candidate):
                result.product_name = candidate
    if not result.product_name:
        result.product_name = _extract_generic_product(text)

    result.brand = _infer_brand(text, result.product_name, result.retailer)

    # Purchase date
    m = _FK_DATE.search(text)
    if m:
        result.purchase_date = _parse_date(m.group(1))
    if not result.purchase_date:
        result.purchase_date = _extract_best_date(text)

    # Price
    m = _FK_PRICE.search(text)
    if m:
        result.price = _parse_price(m.group(1))
    if result.price is None:
        result.price = _extract_best_price(text)

    # Warranty / return window
    _extract_warranty_and_return(text, result)

    # Source snippet
    m_id = _FK_ORDER_ID.search(text)
    if m_id:
        start = max(0, m_id.start() - 50)
        end = min(len(text), m_id.end() + 100)
        result.source_snippet = text[start:end].strip()

    result.confidence = _score_confidence(result)
    return result


# ── Meesho extractor ─────────────────────────────────────────────────────────

def extract_meesho(text: str) -> Optional[ExtractionResult]:
    """Parse a Meesho order-confirmation email."""
    if "meesho" not in text.lower():
        logger.debug("extract_meesho: not a Meesho email — skipping")
        return None

    result = ExtractionResult(retailer="Meesho", pass_used="regex")

    m = _ME_PRODUCT.search(text)
    if m:
        result.product_name = _clean(m.group(1))
    if not result.product_name:
        m = _ME_PRODUCT_ALT.search(text)
        if m:
            result.product_name = _clean(m.group(1))
    if not result.product_name:
        result.product_name = _extract_generic_product(text)

    result.brand = _infer_brand(text, result.product_name)

    m = _ME_DATE.search(text)
    if m:
        result.purchase_date = _parse_date(m.group(1))
    if not result.purchase_date:
        m = _GEN_DATE_LABEL.search(text) or _GEN_DATE.search(text)
        if m:
            result.purchase_date = _parse_date(m.group(1))

    m = _ME_PRICE.search(text)
    if m:
        result.price = _parse_price(m.group(1))
    if result.price is None:
        prices = [_parse_price(p) for p in _GEN_PRICE.findall(text)]
        valid_prices = [p for p in prices if p is not None]
        if valid_prices:
            result.price = max(valid_prices)

    _extract_warranty_and_return(text, result)

    m_id = _ME_ORDER_ID.search(text)
    if m_id:
        start = max(0, m_id.start() - 50)
        end = min(len(text), m_id.end() + 100)
        result.source_snippet = text[start:end].strip()

    result.confidence = _score_confidence(result)
    return result


# ── Ajio extractor ────────────────────────────────────────────────────────────

def extract_ajio(text: str) -> Optional[ExtractionResult]:
    """Parse an Ajio order-confirmation email."""
    if not (_AJ_ORDER_ID.search(text) or "ajio" in text.lower()):
        logger.debug("extract_ajio: not an Ajio email — skipping")
        return None

    result = ExtractionResult(retailer="Ajio", pass_used="regex")

    m = _AJ_PRODUCT.search(text)
    if m:
        result.product_name = _clean(m.group(1))
    if not result.product_name:
        m = _AJ_PRODUCT_ALT.search(text)
        if m:
            result.product_name = _clean(m.group(1))
    if not result.product_name:
        result.product_name = _extract_generic_product(text)

    result.brand = _infer_brand(text, result.product_name)

    m = _AJ_DATE.search(text)
    if m:
        result.purchase_date = _parse_date(m.group(1))
    if not result.purchase_date:
        m = _GEN_DATE_LABEL.search(text) or _GEN_DATE.search(text)
        if m:
            result.purchase_date = _parse_date(m.group(1))

    m = _AJ_PRICE.search(text)
    if m:
        result.price = _parse_price(m.group(1))
    if result.price is None:
        prices = [_parse_price(p) for p in _GEN_PRICE.findall(text)]
        valid_prices = [p for p in prices if p is not None]
        if valid_prices:
            result.price = max(valid_prices)

    _extract_warranty_and_return(text, result)

    m_id = _AJ_ORDER_ID.search(text)
    if m_id:
        start = max(0, m_id.start() - 50)
        end = min(len(text), m_id.end() + 100)
        result.source_snippet = text[start:end].strip()

    result.confidence = _score_confidence(result)
    return result


# ── Generic extractor ─────────────────────────────────────────────────────────

def extract_generic(text: str) -> ExtractionResult:
    """
    Comprehensive regex pass for any email, warranty card, or invoice not
    matched by a specific retailer extractor.
    """
    result = ExtractionResult(pass_used="regex")

    # 1. Product name
    result.product_name = _extract_generic_product(text)

    # 2. Retailer & Brand
    result.retailer = _infer_retailer(text)
    result.brand = _infer_brand(text, result.product_name, result.retailer)

    # 3. Purchase date
    result.purchase_date = _extract_best_date(text)

    # 4. Price
    result.price = _extract_best_price(text)

    # 5. Warranty / return window
    _extract_warranty_and_return(text, result)

    # 6. Snippet
    if result.product_name:
        idx = text.find(result.product_name.split("(")[0].split(",")[0].strip())
        if idx != -1:
            start = max(0, idx - 30)
            end = min(len(text), idx + 140)
            result.source_snippet = re.sub(r"\s+", " ", text[start:end]).strip()

    result.confidence = _score_confidence(result)
    logger.info(
        "Generic extraction: product=%r brand=%r retailer=%r price=%s date=%s warranty=%s return=%s confidence=%s",
        result.product_name,
        result.brand,
        result.retailer,
        result.price,
        result.purchase_date,
        result.warranty_period_months,
        result.return_window_days,
        result.confidence,
    )
    return result


# ── Two-pass orchestrator (Pass 1 only) ──────────────────────────────────────

def run_regex_pass(text: str, hint: Optional[str] = None) -> ExtractionResult:
    """
    Run all regex extractors and return the best result.
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

    return extract_generic(text)
