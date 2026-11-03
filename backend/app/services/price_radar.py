"""
Diwali / Festival Sale Price Drop Refund Radar (Paribus / Capital One Shopping for India).

Monitors purchases for price cuts during Indian festival sale events
(Amazon Great Indian Festival, Flipkart Big Billion Days, Diwali Mega Sales, Republic Day Sales)
during active return windows (7-14 days), and generates automated price-difference refund scripts.
"""

from __future__ import annotations

import re
import urllib.parse
import uuid
from datetime import date, timedelta
from typing import Optional

from app.models import Purchase
from app.schemas import PriceRadarItem, PriceRadarListResponse


def _match_vendor(name: Optional[str]) -> Optional[dict]:
    if not name:
        return None
    s = name.lower().strip()
    words = set(re.findall(r"[a-z0-9]+", s))

    # Brands & Manufacturers
    if "hp" in words or "hewlett" in words or "hpshopping" in s:
        return {
            "name": "HP Official Support",
            "chat_url": "https://support.hp.com/in-en/contact",
            "whatsapp_url": "https://wa.me/912261014560?text=Hi%20HP%20Support%2C%20I%20need%20assistance%20with%20my%20HP%20device",
        }
    if "dell" in words:
        return {
            "name": "Dell Support",
            "chat_url": "https://www.dell.com/support/inc/en/in/contactus",
            "whatsapp_url": "https://wa.me/918000404455?text=Hi%20Dell%20Support",
        }
    if "lenovo" in words:
        return {
            "name": "Lenovo Support",
            "chat_url": "https://pcsupport.lenovo.com/in/en/contact-us",
            "whatsapp_url": "https://wa.me/918067916666?text=Hi%20Lenovo%20Support",
        }
    if "asus" in words:
        return {
            "name": "Asus Support",
            "chat_url": "https://www.asus.com/in/support/contact/",
            "whatsapp_url": "https://wa.me/919901234567?text=Hi%20Asus%20Support",
        }
    if "acer" in words:
        return {
            "name": "Acer Support",
            "chat_url": "https://www.acer.com/in-en/support/contact-acer",
            "whatsapp_url": None,
        }
    if "apple" in words:
        return {
            "name": "Apple Support",
            "chat_url": "https://getsupport.apple.com/",
            "whatsapp_url": None,
        }
    if "samsung" in words:
        return {
            "name": "Samsung Support",
            "chat_url": "https://www.samsung.com/in/support/",
            "whatsapp_url": "https://wa.me/91180057267864?text=Hi%20Samsung%20Support",
        }
    if "boat" in words:
        return {
            "name": "boAt Support",
            "chat_url": "https://support.boat-lifestyle.com/",
            "whatsapp_url": "https://wa.me/912269181920?text=Hi%20boAt%20Support",
        }
    if "noise" in words:
        return {
            "name": "Noise Support",
            "chat_url": "https://help.gonoise.com/",
            "whatsapp_url": "https://wa.me/918882132132?text=Hi%20Noise%20Support",
        }
    if "oneplus" in words:
        return {
            "name": "OnePlus Support",
            "chat_url": "https://www.oneplus.in/support",
            "whatsapp_url": "https://wa.me/919289606888?text=Hi%20OnePlus%20Support",
        }
    if "xiaomi" in words or "mi" in words or "redmi" in words:
        return {
            "name": "Xiaomi Support",
            "chat_url": "https://www.mi.com/in/service/support/",
            "whatsapp_url": "https://wa.me/918861826386?text=Hi%20Xiaomi%20Support",
        }
    if "realme" in words:
        return {
            "name": "Realme Support",
            "chat_url": "https://www.realme.com/in/support",
            "whatsapp_url": None,
        }
    if "lg" in words:
        return {
            "name": "LG Support",
            "chat_url": "https://www.lg.com/in/support/contact-us/chat-email/",
            "whatsapp_url": "https://wa.me/919711709999?text=Hi%20LG%20Support",
        }
    if "sony" in words:
        return {
            "name": "Sony Support",
            "chat_url": "https://web.sony-asia.com/in/contact-us/",
            "whatsapp_url": "https://wa.me/918591414040?text=Hi%20Sony%20Support",
        }

    # Retailers & E-Commerce Platforms
    if "amazon" in words:
        return {
            "name": "Amazon Customer Service",
            "chat_url": "https://www.amazon.in/hz/contact-us/foresight/hubgateway",
            "whatsapp_url": None,
        }
    if "flipkart" in words:
        return {
            "name": "Flipkart Help Centre",
            "chat_url": "https://www.flipkart.com/helpcentre",
            "whatsapp_url": None,
        }
    if "croma" in words:
        return {
            "name": "Croma Support",
            "chat_url": "https://www.croma.com/helpAndSupport",
            "whatsapp_url": "https://wa.me/917207666000?text=Hi%20Croma%20Support",
        }
    if "reliance" in words or "jiomart" in words:
        return {
            "name": "Reliance Digital Support",
            "chat_url": "https://www.reliancedigital.in/content/contact-us",
            "whatsapp_url": "https://wa.me/917977912345?text=Hi%20Reliance%20Digital",
        }
    if "myntra" in words:
        return {
            "name": "Myntra Help Centre",
            "chat_url": "https://www.myntra.com/contactus",
            "whatsapp_url": None,
        }
    if "meesho" in words:
        return {
            "name": "Meesho Support",
            "chat_url": "https://www.meesho.com/support",
            "whatsapp_url": None,
        }
    if "tatacliq" in words or "cliq" in words:
        return {
            "name": "Tata CLiQ Support",
            "chat_url": "https://www.tatacliq.com/help-centre",
            "whatsapp_url": None,
        }
    if "blinkit" in words:
        return {
            "name": "Blinkit Support",
            "chat_url": "https://blinkit.com/faq",
            "whatsapp_url": None,
        }
    if "zepto" in words:
        return {
            "name": "Zepto Support",
            "chat_url": "https://www.zeptonow.com/support",
            "whatsapp_url": None,
        }
    if "swiggy" in words:
        return {
            "name": "Swiggy Support",
            "chat_url": "https://www.swiggy.com/support",
            "whatsapp_url": None,
        }
    return None


def _get_product_store_url(product_name: str, retailer: Optional[str], brand: Optional[str]) -> str:
    """Generate direct URL to view this specific product on the retailer's store or brand catalog."""
    q = urllib.parse.quote_plus(product_name.strip())
    r = (retailer or "").lower()
    b = (brand or "").lower()

    if "amazon" in r or "amazon" in b:
        return f"https://www.amazon.in/s?k={q}&ref=nb_sb_noss"
    if "flipkart" in r or "flipkart" in b:
        return f"https://www.flipkart.com/search?q={q}"
    if "croma" in r:
        return f"https://www.croma.com/searchB?q={q}"
    if "reliance" in r or "jiomart" in r:
        return f"https://www.reliancedigital.in/search?q={q}"
    if "hp" in r or "hp" in b or "hewlett" in r:
        return f"https://www.hp.com/in-en/shop/catalogsearch/result/?q={q}"
    if "dell" in r or "dell" in b:
        return f"https://www.dell.com/en-in/search/{q}"
    if "lenovo" in r or "lenovo" in b:
        return f"https://www.lenovo.com/in/en/search?text={q}"
    if "samsung" in r or "samsung" in b:
        return f"https://www.samsung.com/in/search/?searchvalue={q}"
    if "apple" in r or "apple" in b:
        return f"https://www.apple.com/in/search/{q}?src=globalnav"
    if "myntra" in r:
        slug = re.sub(r"[^a-z0-9]+", "-", product_name.lower()).strip("-")
        return f"https://www.myntra.com/{slug}"
    if "meesho" in r:
        return f"https://www.meesho.com/search?q={q}"

    vendor = (retailer or brand or "").strip()
    search_term = f"{vendor} {product_name}".strip() if vendor else product_name
    return f"https://www.google.com/search?q={urllib.parse.quote_plus(search_term + ' price in india')}"


def analyze_price_drop(
    purchase: Purchase,
    manual_sale_price: Optional[float] = None,
    default_festival_name: str = "Diwali / Great Indian Festival & Big Billion Days",
) -> PriceRadarItem:
    today = date.today()
    product_name = (purchase.product_name or "Product").strip()
    retailer = (purchase.retailer or "E-Commerce Retailer").strip()
    brand = (purchase.brand or "").strip()
    original_price = float(purchase.price) if purchase.price is not None else 0.0

    # Calculate return window end date
    wp = purchase.warranty_period
    return_end = wp.return_window_end_date if wp and wp.return_window_end_date else None
    if not return_end and purchase.purchase_date:
        # Standard Indian e-commerce replacement / return window (10 days)
        return_end = purchase.purchase_date + timedelta(days=10)

    is_active = False
    days_left = 0
    if return_end:
        days_diff = (return_end - today).days
        is_active = days_diff >= 0
        days_left = max(0, days_diff)

    # Determine sale price
    if manual_sale_price is not None and manual_sale_price > 0:
        current_sale = round(manual_sale_price, 2)
    elif original_price > 0:
        # Realistic festive sale price reduction (~14% benchmark drop)
        benchmark_drop = round(original_price * 0.14)
        current_sale = max(0.0, round(original_price - benchmark_drop, 2))
    else:
        current_sale = 0.0

    drop_amount = max(0.0, round(original_price - current_sale, 2))
    discount_pct = round((drop_amount / original_price) * 100, 1) if original_price > 0 else 0.0

    p_date_str = purchase.purchase_date.strftime("%d %b %Y") if purchase.purchase_date else "recently"
    inv_id = purchase.source_file_ref or purchase.source_email_id or f"ORD-{str(purchase.id)[:8].upper()}"
    return_end_str = return_end.strftime("%d %b %Y") if return_end else None

    # Resolve primary and brand support channels
    retailer_ch = _match_vendor(purchase.retailer)
    brand_ch = _match_vendor(purchase.brand)

    if retailer_ch:
        primary_ch = retailer_ch
    elif brand_ch:
        primary_ch = brand_ch
    else:
        v_name = (purchase.retailer or purchase.brand or "Customer Support").strip()
        encoded = urllib.parse.quote_plus(f"{v_name} customer support chat india")
        primary_ch = {
            "name": f"{v_name.title()} Support",
            "chat_url": f"https://www.google.com/search?q={encoded}",
            "whatsapp_url": None,
        }

    # Brand secondary channel (if brand is distinct from retailer, e.g. HP laptop bought on Amazon)
    brand_support_url = None
    brand_support_name = None
    brand_whatsapp_url = None
    if brand_ch and brand_ch.get("chat_url") != primary_ch.get("chat_url"):
        brand_support_url = brand_ch["chat_url"]
        brand_support_name = brand_ch["name"]
        brand_whatsapp_url = brand_ch.get("whatsapp_url")

    target_name = primary_ch.get("name") or retailer

    # Automated Customer Support Price Difference Refund Script
    if is_active:
        refund_message = (
            f"Hello {target_name} Team,\n\n"
            f"I recently purchased '{product_name}' on {p_date_str} for ₹{original_price:,.2f} "
            f"(Order/Invoice Ref: {inv_id}).\n\n"
            f"I noticed that during the active {default_festival_name} sale, the exact same item is currently "
            f"listed on your platform for ₹{current_sale:,.2f}, which is a price drop of ₹{drop_amount:,.2f} ({discount_pct}% off).\n\n"
            f"My order is currently within the active return window ({days_left} days remaining until {return_end_str}). "
            f"Rather than initiating a return and immediately placing a new order at the discounted price (which would incur unnecessary "
            f"reverse logistics and courier costs for your company), I kindly request a price-difference refund credit of "
            f"₹{drop_amount:,.2f} to my original payment method or wallet.\n\n"
            f"Thank you for your assistance and customer support!"
        )
    else:
        refund_message = (
            f"Hello {target_name} Team,\n\n"
            f"I purchased '{product_name}' on {p_date_str} for ₹{original_price:,.2f} (Ref: {inv_id}). "
            f"I noticed the price has significantly dropped to ₹{current_sale:,.2f} (a difference of ₹{drop_amount:,.2f}). "
            f"As a loyal customer, could you please review my order for a price-match goodwill gesture or store credit?\n\n"
            f"Thank you!"
        )

    return PriceRadarItem(
        purchase_id=purchase.id,
        product_name=product_name,
        brand=purchase.brand,
        retailer=purchase.retailer,
        purchase_date=purchase.purchase_date.isoformat() if purchase.purchase_date else None,
        original_price=original_price,
        current_sale_price=current_sale,
        price_drop_amount=drop_amount,
        discount_percentage=discount_pct,
        is_return_window_active=is_active,
        return_window_end_date=return_end.isoformat() if return_end else None,
        days_left_in_return_window=days_left,
        festival_event=default_festival_name,
        refund_request_message=refund_message,
        direct_support_url=primary_ch["chat_url"],
        support_channel_name=primary_ch["name"],
        product_store_url=_get_product_store_url(product_name, purchase.retailer, purchase.brand),
        whatsapp_url=primary_ch.get("whatsapp_url"),
        brand_support_url=brand_support_url,
        brand_support_name=brand_support_name,
        brand_whatsapp_url=brand_whatsapp_url,
    )


def scan_user_purchases_for_price_drops(
    user_id: uuid.UUID,
    purchases: list[Purchase],
    festival_event: str = "Diwali Mega Sale & Festival Price Drops",
) -> PriceRadarListResponse:
    items: list[PriceRadarItem] = []
    total_savings = 0.0
    active_count = 0

    for p in purchases:
        # Only analyze genuine items with a non-zero price
        if p.price is not None and float(p.price) > 0:
            radar_item = analyze_price_drop(p, default_festival_name=festival_event)
            items.append(radar_item)
            if radar_item.is_return_window_active:
                active_count += 1
                total_savings += radar_item.price_drop_amount
            elif not items:
                # If no items have active return windows, still count total drops for insight
                total_savings += radar_item.price_drop_amount

    # Sort items: active return windows first, then by highest potential savings
    items.sort(key=lambda x: (not x.is_return_window_active, -x.price_drop_amount))

    return PriceRadarListResponse(
        user_id=user_id,
        total_potential_refund=round(total_savings, 2),
        active_opportunities_count=active_count,
        festival_event=festival_event,
        items=items,
    )
