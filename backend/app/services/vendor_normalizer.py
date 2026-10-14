"""
Vendor normalization service.

Maps retailer name variants (from regex or LLM extraction) to a canonical
display name. For example:
  "Amazon.in", "amazon", "Amazon India"  →  "Amazon"
  "flipkart.com", "FK"                   →  "Flipkart"

Design:
  - All lookups are case-insensitive.
  - Returns None if the input is None/blank (caller decides how to handle).
  - Returns the canonical name, or the original (title-cased) string if unknown.
"""

from __future__ import annotations

import re
from typing import Optional

# ── Canonical name map ────────────────────────────────────────────────────────
# Keys are lowercase substrings to match; values are canonical display names.
# Longer/more specific keys should come first if there's any chance of collision.

_VENDOR_MAP: dict[str, str] = {
    # Amazon
    "amazon.in": "Amazon",
    "amazon india": "Amazon",
    "amazon.com": "Amazon",
    "amazon": "Amazon",

    # Flipkart
    "flipkart.com": "Flipkart",
    "flipkart": "Flipkart",

    # Myntra
    "myntra.com": "Myntra",
    "myntra": "Myntra",

    # Nykaa
    "nykaa.com": "Nykaa",
    "nykaa fashion": "Nykaa Fashion",
    "nykaa": "Nykaa",

    # Meesho
    "meesho.com": "Meesho",
    "meesho": "Meesho",

    # Ajio
    "ajio.com": "Ajio",
    "ajio": "Ajio",

    # JioMart
    "jiomart.com": "JioMart",
    "jiomart": "JioMart",
    "jio mart": "JioMart",

    # Blinkit (formerly Grofers)
    "blinkit.com": "Blinkit",
    "blinkit": "Blinkit",
    "grofers": "Blinkit",

    # Zepto
    "zeptonow.com": "Zepto",
    "zepto": "Zepto",

    # Swiggy / Instamart
    "swiggy.com": "Swiggy",
    "swiggy instamart": "Swiggy Instamart",
    "instamart": "Swiggy Instamart",
    "swiggy": "Swiggy",

    # Bigbasket
    "bigbasket.com": "BigBasket",
    "bigbasket": "BigBasket",
    "big basket": "BigBasket",

    # Snapdeal
    "snapdeal.com": "Snapdeal",
    "snapdeal": "Snapdeal",

    # Tata CLiQ
    "tatacliq.com": "Tata CLiQ",
    "tata cliq": "Tata CLiQ",
    "tatacliq": "Tata CLiQ",

    # Reliance Digital
    "reliancedigital.in": "Reliance Digital",
    "reliance digital": "Reliance Digital",

    # Croma
    "croma.com": "Croma",
    "croma": "Croma",

    # Vijay Sales
    "vijaysales.com": "Vijay Sales",
    "vijay sales": "Vijay Sales",

    # Apple
    "apple.com": "Apple",
    "apple store": "Apple",
    "apple": "Apple",

    # Samsung
    "samsung.com": "Samsung",
    "samsung shop": "Samsung",
    "samsung": "Samsung",

    # PhonePe
    "phonepe": "PhonePe",

    # Paytm Mall
    "paytmmall": "Paytm Mall",
    "paytm mall": "Paytm Mall",
}

# Sort by length descending so longer/more-specific patterns match first
_SORTED_KEYS = sorted(_VENDOR_MAP.keys(), key=len, reverse=True)


def normalize_vendor(raw: Optional[str]) -> Optional[str]:
    """
    Normalise a raw retailer/vendor string to its canonical display name.

    Args:
        raw: The raw retailer name from extraction (may be None).

    Returns:
        Canonical name (e.g. "Amazon") or the original title-cased string if
        the vendor is not in the map. Returns None if raw is None or empty.
    """
    if not raw or not raw.strip():
        return None

    lowered = raw.strip().lower()
    # Strip common TLDs and URL noise for matching
    cleaned = re.sub(r"\bhttps?://\S+", "", lowered).strip()

    for key in _SORTED_KEYS:
        if key in cleaned:
            return _VENDOR_MAP[key]

    # Not in map — return cleaned, title-cased version of the original
    return raw.strip().title()
