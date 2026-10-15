"""
Category-based warranty fallback service.

When extraction confidence is 'low' and no explicit warranty period was found,
this module provides estimated warranty periods by product category — so the
system can still give users a useful best-guess rather than showing nothing.

All estimated records are flagged with is_estimated=True in the DB so the
UI can display a clear "estimated" badge.

Category detection is keyword-based (applied to product_name + brand text).
"""

from __future__ import annotations

import re
from typing import Optional

# ── Category definitions ──────────────────────────────────────────────────────
# Each entry: (canonical_category, warranty_months, return_days, keywords)
# Keywords are matched case-insensitively in order. First match wins.

_CATEGORIES: list[tuple[str, int, int, list[str]]] = [
    (
        "Smartphone",
        12,
        7,
        ["iphone", "samsung galaxy", "redmi", "realme", "oneplus", "pixel", "vivo",
         "oppo", "poco", "iqoo", "motorola", "nokia", "smartphone", "mobile phone"],
    ),
    (
        "Laptop / Computer",
        12,
        10,
        ["laptop", "macbook", "chromebook", "notebook", "ultrabook", "desktop",
         "all-in-one", "gaming pc", "imac"],
    ),
    (
        "Tablet",
        12,
        7,
        ["ipad", "tablet", "galaxy tab", "fire hd", "surface pro"],
    ),
    (
        "Headphones / Earbuds",
        12,
        7,
        ["airpods", "earbuds", "headphones", "earphones", "tws", "noise cancelling",
         "airdopes", "wh-1000", "boat", "boult", "jbl"],
    ),
    (
        "Television",
        12,
        10,
        ["television", "smart tv", " tv ", "oled tv", "qled tv", "led tv",
         "android tv", "fire tv", "lg tv", "samsung tv"],
    ),
    (
        "Refrigerator",
        12,
        10,
        ["refrigerator", "fridge", "double door", "single door", "side by side",
         "french door fridge"],
    ),
    (
        "Washing Machine",
        24,
        10,
        ["washing machine", "washer", "front load", "top load", "dryer"],
    ),
    (
        "Air Conditioner",
        12,
        10,
        ["air conditioner", "split ac", "window ac", " ac ", "inverter ac",
         "portable ac"],
    ),
    (
        "Microwave / Oven",
        12,
        10,
        ["microwave", "oven", "convection oven", "otg", "air fryer"],
    ),
    (
        "Small Kitchen Appliance",
        12,
        7,
        ["mixer", "grinder", "juicer", "blender", "toaster", "coffee maker",
         "water purifier", "ro purifier", "iron box", "steam iron",
         "water heater", "geyser", "instant heater", "kettle"],
    ),
    (
        "Camera",
        12,
        7,
        ["camera", "dslr", "mirrorless", "action cam", "gopro", "webcam",
         "dashcam", "security camera"],
    ),
    (
        "Speaker / Soundbar",
        12,
        7,
        ["speaker", "soundbar", "bluetooth speaker", "party speaker", "woofer",
         "home theatre"],
    ),
    (
        "Power Bank / Charger",
        6,
        7,
        ["power bank", "powerbank", "charger", "adapter", "usb hub"],
    ),
    (
        "Smartwatch / Fitness Tracker",
        12,
        7,
        ["smartwatch", "smart watch", "fitness tracker", "fitness band",
         "apple watch", "galaxy watch", "fire-boltt", "noise watch"],
    ),
    (
        "Clothing / Apparel",
        0,  # No warranty for clothing
        30,
        ["shirt", "t-shirt", "jeans", "trousers", "saree", "kurta", "dress",
         "jacket", "shoes", "sneakers", "sandals", "boots", "hoodie",
         "leggings", "shorts", "top ", " kurti"],
    ),
    (
        "Furniture",
        12,
        7,
        ["sofa", "chair", "table", "bed", "wardrobe", "shelf", "rack",
         "mattress", "desk", "bookshelf"],
    ),
    (
        "Personal Care",
        6,
        7,
        ["trimmer", "shaver", "hair dryer", "hair straightener", "epilator",
         "electric toothbrush", "face wash", "cream", "serum"],
    ),
]


def get_category_fallback(
    product_name: Optional[str],
    brand: Optional[str] = None,
) -> Optional[tuple[str, int, int]]:
    """
    Detect the product category and return an estimated warranty/return window.

    Args:
        product_name: Product name from extraction (may be None).
        brand: Brand from extraction (may be None).

    Returns:
        Tuple of (category_name, warranty_months, return_window_days) if a
        category is detected, or None if no match found.
        Note: warranty_months=0 means "no standard warranty" (e.g. clothing).
    """
    combined = " ".join(
        part for part in [product_name, brand] if part
    ).lower()

    if not combined.strip():
        return None

    for category, warranty_months, return_days, keywords in _CATEGORIES:
        for kw in keywords:
            if re.search(re.escape(kw), combined, re.IGNORECASE):
                return (category, warranty_months, return_days)

    return None


def apply_category_fallback(
    product_name: Optional[str],
    brand: Optional[str],
    existing_warranty_months: Optional[int],
    existing_return_days: Optional[int],
) -> dict:
    """
    Return a dict with fallback values to apply only where originals are None.

    Returns a dict with keys:
      - warranty_period_months (int | None)
      - return_window_days     (int | None)
      - category               (str | None)
      - is_estimated           (bool)
    """
    result = get_category_fallback(product_name, brand)

    if result is None:
        return {
            "warranty_period_months": existing_warranty_months,
            "return_window_days": existing_return_days,
            "category": None,
            "is_estimated": False,
        }

    category, warranty_months, return_days = result
    filled_warranty = existing_warranty_months if existing_warranty_months is not None else (
        warranty_months if warranty_months > 0 else None
    )
    filled_return = existing_return_days if existing_return_days is not None else return_days

    # is_estimated = True only if we actually filled in missing values
    was_estimated = (
        (existing_warranty_months is None and warranty_months > 0) or
        (existing_return_days is None)
    )

    return {
        "warranty_period_months": filled_warranty,
        "return_window_days": filled_return,
        "category": category,
        "is_estimated": was_estimated,
    }
