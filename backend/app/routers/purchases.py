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
    PurchaseEditRequest,
    PurchaseOut,
    PurchasesListResponse,
    WarrantyPeriodOut,
)
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

    # Automatically purge any invalid, unnamed, unknown-retailer, or demo records
    purchases: list[Purchase] = []
    purged_count = 0
    for row in all_rows:
        if _is_genuine_purchase_row(row):
            purchases.append(row)
        else:
            try:
                db.delete(row)
                purged_count += 1
            except Exception as exc:
                logger.warning("Failed to purge invalid purchase row %s: %s", row.id, exc)

    if purged_count > 0:
        try:
            db.commit()
            logger.info("Purged %d invalid/unnamed/demo purchase rows for user %s", purged_count, user_id)
        except Exception as exc:
            db.rollback()
            logger.warning("Rollback during invalid row purge for user %s: %s", user_id, exc)

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
    if body.warranty_end_date is not None or body.return_window_end_date is not None:
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
