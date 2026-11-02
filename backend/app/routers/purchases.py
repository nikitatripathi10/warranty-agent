"""
Purchase management endpoints.

GET  /purchases?user_id=<uuid>          → List all purchases for a user
GET  /purchases/<id>?user_id=<uuid>     → Get a single purchase by ID
PATCH /purchases/<id>?user_id=<uuid>    → Manually edit purchase fields (with audit log)
DELETE /purchases/<id>?user_id=<uuid>   → Delete a purchase

These endpoints power the Dashboard and Item Detail screens in the frontend.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Purchase, User, WarrantyPeriod
from app.schemas import (
    LegalNoticeRequest,
    LegalNoticeResponse,
    PriceCheckRequest,
    PriceRadarItem,
    PriceRadarListResponse,
    PurchaseEditRequest,
    PurchaseOut,
    PurchasesListResponse,
    WarrantyPeriodOut,
)
from app.services.legal_generator import generate_legal_notice
from app.services.price_radar import analyze_price_drop, scan_user_purchases_for_price_drops
from app.services.vendor_normalizer import normalize_vendor

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

_INVALID_PRODUCT_NAMES = {
    "",
    "unnamed product",
    "unknown product",
    "unknown",
    "product",
    "item",
    "none",
    "null",
    "n/a",
    "—",
    "-",
}

_INVALID_VENDORS = {
    "",
    "unknown retailer",
    "unknown",
    "demo electronics",
    "demo",
    "sample",
    "placeholder",
    "none",
    "null",
    "n/a",
    "—",
    "-",
}


def _normalize_name_for_dedup(name: str | None) -> str:
    if not name:
        return ""
    import re
    s = name.lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    return " ".join(s.split())


def _is_genuine_purchase_row(purchase: Purchase) -> bool:
    """
    Return True only if the purchase row represents a genuine scanned/extracted
    product with a real product name and a real retailer or brand (no unnamed,
    unknown-retailer, or demo entries).
    """
    name = (purchase.product_name or "").strip()
    if not name or name.lower() in _INVALID_PRODUCT_NAMES:
        return False

    retailer = (purchase.retailer or "").strip()
    brand = (purchase.brand or "").strip()
    vendor = retailer or brand
    if not vendor or vendor.lower() in _INVALID_VENDORS:
        return False
    if retailer.lower() in _INVALID_VENDORS and retailer != "":
        return False
    if brand.lower() in _INVALID_VENDORS and brand != "":
        return False

    wp = purchase.warranty_period
    snippet = (wp.source_snippet or "").lower() if wp else ""
    if "demo-2026" in snippet or "demo electronics" in snippet:
        return False

    return True


def _get_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return user


def _get_purchase_or_404(
    db: Session, purchase_id: uuid.UUID, user_id: uuid.UUID
) -> Purchase:
    purchase = (
        db.query(Purchase)
        .filter(Purchase.id == purchase_id, Purchase.user_id == user_id)
        .first()
    )
    if not purchase:
        raise HTTPException(
            status_code=404,
            detail=f"Purchase {purchase_id} not found (or does not belong to this user)",
        )
    return purchase


def _urgency_days(purchase: Purchase) -> int:
    """
    Return the number of days until the nearest upcoming deadline
    (return window or warranty expiry). Used for sorting.
    Returns 9999 if no deadlines exist.
    """
    wp = purchase.warranty_period
    if wp is None:
        return 9999
    today = date.today()
    candidates: list[int] = []
    if wp.return_window_end_date:
        candidates.append((wp.return_window_end_date - today).days)
    if wp.warranty_end_date:
        candidates.append((wp.warranty_end_date - today).days)
    if not candidates:
        return 9999
    # Return the earliest upcoming deadline (positive), or the least negative
    # (for overdue ones)
    upcoming = [d for d in candidates if d >= 0]
    return min(upcoming) if upcoming else max(candidates)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=PurchasesListResponse,
    summary="List all purchases for a user",
)
def list_purchases(
    user_id: uuid.UUID = Query(..., description="UUID of the user"),
    source_type: str | None = Query(None, description="Filter by source: 'email' or 'upload'"),
    sort_by: str = Query("urgency", description="Sort order: 'urgency' | 'date' | 'created'"),
    db: Session = Depends(get_db),
) -> PurchasesListResponse:
    """
    Return all purchase records for a user, sorted by urgency (most urgent first)
    by default. Optionally filter by source_type.
    """
    _get_user_or_404(db, user_id)

    query = db.query(Purchase).filter(Purchase.user_id == user_id)
    if source_type:
        query = query.filter(Purchase.source_type == source_type)

    all_rows = query.all()

    # Automatically purge any invalid, unnamed, unknown-retailer, demo, or DUPLICATE records
    purchases: list[Purchase] = []
    seen_dedup_keys: dict[str, Purchase] = {}
    purged_count = 0

    for row in all_rows:
        if not _is_genuine_purchase_row(row):
            try:
                db.delete(row)
                purged_count += 1
            except Exception as exc:
                logger.warning("Failed to purge invalid purchase row %s: %s", row.id, exc)
            continue

        norm_name = _normalize_name_for_dedup(row.product_name)
        norm_vendor = (normalize_vendor(row.retailer) or row.retailer or row.brand or "").lower().strip()
        date_str = row.purchase_date.isoformat() if row.purchase_date else ""
        price_str = f"{row.price:.2f}" if row.price is not None else ""

        dedup_key = f"{norm_name}|{norm_vendor}|{date_str or price_str}"
        loose_key = f"{norm_name}|{norm_vendor}" if len(norm_name) >= 5 and norm_vendor else None

        if dedup_key in seen_dedup_keys or (loose_key and loose_key in seen_dedup_keys):
            primary = seen_dedup_keys.get(dedup_key) or seen_dedup_keys[loose_key]
            # Merge file references and extended warranty info into primary if missing
            if row.source_file_ref and not primary.source_file_ref:
                primary.source_file_ref = row.source_file_ref
            if row.warranty_period and primary.warranty_period:
                if row.warranty_period.warranty_end_date and (
                    not primary.warranty_period.warranty_end_date
                    or row.warranty_period.warranty_end_date > primary.warranty_period.warranty_end_date
                ):
                    primary.warranty_period.warranty_end_date = row.warranty_period.warranty_end_date
                if row.warranty_period.source_snippet and "Additional Warranty" in row.warranty_period.source_snippet:
                    primary.warranty_period.source_snippet = row.warranty_period.source_snippet

            try:
                db.delete(row)
                purged_count += 1
                logger.info("Purged duplicate purchase row %s on dashboard fetch (matches %s)", row.id, primary.id)
            except Exception as exc:
                logger.warning("Failed to delete duplicate purchase row %s: %s", row.id, exc)
        else:
            seen_dedup_keys[dedup_key] = row
            if loose_key:
                seen_dedup_keys[loose_key] = row
            purchases.append(row)

    if purged_count > 0:
        try:
            db.commit()
            logger.info("Purged %d duplicate or invalid purchase rows for user %s", purged_count, user_id)
        except Exception as exc:
            db.rollback()
            logger.warning("Rollback during row purge for user %s: %s", user_id, exc)

    # Sort
    if sort_by == "urgency":
        purchases.sort(key=_urgency_days)
    elif sort_by == "date":
        purchases.sort(
            key=lambda p: p.purchase_date or date.min,
            reverse=True,
        )
    else:  # created
        purchases.sort(key=lambda p: p.created_at, reverse=True)

    return PurchasesListResponse(
        user_id=user_id,
        total=len(purchases),
        purchases=[PurchaseOut.model_validate(p) for p in purchases],
    )


@router.get(
    "/price-radar/all",
    response_model=PriceRadarListResponse,
    summary="Scan all user purchases for Diwali & festival sale price drops",
)
def get_all_price_drops(
    user_id: uuid.UUID = Query(..., description="UUID of the user"),
    festival_event: str = Query("Diwali & Festive Sales", description="Festival or sale season title"),
    db: Session = Depends(get_db),
) -> PriceRadarListResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    purchases = db.query(Purchase).filter(Purchase.user_id == user_id).all()
    genuine = [p for p in purchases if _is_genuine_purchase_row(p)]
    return scan_user_purchases_for_price_drops(user_id=user_id, purchases=genuine, festival_event=festival_event)


@router.get(
    "/{purchase_id}",
    response_model=PurchaseOut,
    summary="Get a single purchase by ID",
)
def get_purchase(
    purchase_id: uuid.UUID,
    user_id: uuid.UUID = Query(..., description="UUID of the user"),
    db: Session = Depends(get_db),
) -> PurchaseOut:
    """Return a single purchase record with its warranty period."""
    purchase = _get_purchase_or_404(db, purchase_id, user_id)
    return PurchaseOut.model_validate(purchase)


@router.post(
    "/{purchase_id}/legal-notice",
    response_model=LegalNoticeResponse,
    summary="Generate 1-click formal legal demand notice & e-Daakhil / NCH dispute draft",
)
def create_legal_notice(
    purchase_id: uuid.UUID,
    body: LegalNoticeRequest,
    db: Session = Depends(get_db),
) -> LegalNoticeResponse:
    """
    Generate an enforceable 15-day Pre-Litigation Legal Demand Notice citing Sections
    2(11), 2(47), and 84-87 of the Consumer Protection Act 2019, an NCH 1915 grievance draft,
    and e-Daakhil filing guidance.
    """
    purchase = _get_purchase_or_404(db, purchase_id, body.user_id)
    return generate_legal_notice(purchase, body)


@router.get(
    "/{purchase_id}/price-radar",
    response_model=PriceRadarItem,
    summary="Get festival price drop analysis & 1-click refund script for a purchase",
)
def get_item_price_radar(
    purchase_id: uuid.UUID,
    user_id: uuid.UUID = Query(..., description="UUID of the user"),
    sale_price: float | None = Query(None, description="Optional manual observed sale price"),
    festival_event: str = Query("Diwali / Festival Sale", description="Festival event title"),
    db: Session = Depends(get_db),
) -> PriceRadarItem:
    """
    Calculate price drop differential, verify active 7-14 day return window status,
    and generate an automated Amazon/Flipkart price-match refund negotiation script.
    """
    purchase = _get_purchase_or_404(db, purchase_id, user_id)
    return analyze_price_drop(purchase, manual_sale_price=sale_price, default_festival_name=festival_event)



@router.patch(
    "/{purchase_id}",
    response_model=PurchaseOut,
    summary="Manually correct a purchase record",
)
def edit_purchase(
    purchase_id: uuid.UUID,
    body: PurchaseEditRequest,
    user_id: uuid.UUID = Query(..., description="UUID of the user"),
    db: Session = Depends(get_db),
) -> PurchaseOut:
    """
    Manually correct extracted fields on a purchase record.

    Only non-None fields in the request body are updated.
    The retailer name is normalised to its canonical form on update.
    Warranty period dates can also be overridden via this endpoint.
    """
    purchase = _get_purchase_or_404(db, purchase_id, user_id)

    # -- Update purchase fields (only non-None values) --
    changed: list[str] = []

    if body.product_name is not None:
        purchase.product_name = body.product_name.strip() or None
        changed.append("product_name")

    if body.brand is not None:
        purchase.brand = body.brand.strip() or None
        changed.append("brand")

    if body.retailer is not None:
        # Normalise to canonical form on manual edit too
        purchase.retailer = normalize_vendor(body.retailer) or body.retailer.strip() or None
        changed.append("retailer")

    if body.purchase_date is not None:
        purchase.purchase_date = body.purchase_date
        changed.append("purchase_date")

    if body.price is not None:
        purchase.price = body.price
        changed.append("price")

    if body.family_member is not None:
        purchase.family_member = body.family_member.strip() or None
        changed.append("family_member")

    if body.registration_required is not None:
        purchase.registration_required = body.registration_required
        changed.append("registration_required")

    if body.registration_url is not None:
        purchase.registration_url = body.registration_url.strip() or None
        changed.append("registration_url")

    # -- Update warranty period if overrides provided --
    warranty_changed: list[str] = []
    if (
        body.warranty_end_date is not None
        or body.return_window_end_date is not None
        or body.source_snippet is not None
    ):
        wp = purchase.warranty_period
        if wp is None:
            # Create a new warranty period row if it doesn't exist
            wp = WarrantyPeriod(
                purchase_id=purchase.id,
                confidence_score="high",  # User-confirmed = high confidence
                is_estimated=False,
            )
            db.add(wp)

        if body.warranty_end_date is not None:
            wp.warranty_end_date = body.warranty_end_date
            # User confirmed = high confidence, not estimated
            wp.is_estimated = False
            wp.confidence_score = "high"
            warranty_changed.append("warranty_end_date")

        if body.return_window_end_date is not None:
            wp.return_window_end_date = body.return_window_end_date
            warranty_changed.append("return_window_end_date")

        if body.source_snippet is not None:
            wp.source_snippet = body.source_snippet.strip() or wp.source_snippet
            warranty_changed.append("source_snippet")

    all_changed = changed + warranty_changed

    if not all_changed:
        raise HTTPException(status_code=400, detail="No fields to update were provided")

    try:
        db.commit()
        db.refresh(purchase)
    except Exception as exc:
        db.rollback()
        logger.error("DB error editing purchase %s: %s", purchase_id, exc)
        raise HTTPException(status_code=500, detail="Database error — please try again") from exc

    logger.info(
        "Purchase %s manually edited by user %s: changed=%s",
        purchase_id,
        user_id,
        all_changed,
    )
    return PurchaseOut.model_validate(purchase)


@router.delete(
    "/{purchase_id}",
    status_code=204,
    response_class=Response,
    summary="Delete a purchase record",
)
def delete_purchase(
    purchase_id: uuid.UUID,
    user_id: uuid.UUID = Query(..., description="UUID of the user"),
    db: Session = Depends(get_db),
) -> Response:
    """
    Permanently delete a purchase and its associated warranty period and alerts
    (via CASCADE foreign key).
    """
    purchase = _get_purchase_or_404(db, purchase_id, user_id)
    try:
        db.delete(purchase)
        db.commit()
        logger.info("Purchase %s deleted by user %s", purchase_id, user_id)
        return Response(status_code=204)
    except Exception as exc:
        db.rollback()
        logger.error("DB error deleting purchase %s: %s", purchase_id, exc)
        raise HTTPException(status_code=500, detail="Database error — please try again") from exc
