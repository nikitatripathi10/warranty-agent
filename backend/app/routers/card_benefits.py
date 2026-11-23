"""
Credit-card benefit endpoints (mounted under /purchases).

GET /purchases/{id}/card-benefits?user_id=   -> detected card + what it may add
PUT /purchases/{id}/payment-card             -> pick (or clear) the card used
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Purchase
from app.schemas import CardBenefitReport, PaymentCardRequest
from app.services.card_benefits import build_card_report, get_payment_method, set_manual_card

router = APIRouter()


def _get_purchase_or_404(db: Session, purchase_id: uuid.UUID, user_id: uuid.UUID) -> Purchase:
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


@router.get(
    "/{purchase_id}/card-benefits",
    response_model=CardBenefitReport,
    summary="Which credit card paid, and does it add free warranty or purchase protection?",
)
def get_card_benefits(
    purchase_id: uuid.UUID,
    user_id: uuid.UUID = Query(..., description="UUID of the user"),
    db: Session = Depends(get_db),
) -> CardBenefitReport:
    purchase = _get_purchase_or_404(db, purchase_id, user_id)
    return build_card_report(purchase, get_payment_method(db, purchase.id))


@router.put(
    "/{purchase_id}/payment-card",
    response_model=CardBenefitReport,
    summary="Choose (or clear) the credit card used for a purchase",
)
def put_payment_card(
    purchase_id: uuid.UUID,
    body: PaymentCardRequest,
    db: Session = Depends(get_db),
) -> CardBenefitReport:
    purchase = _get_purchase_or_404(db, purchase_id, body.user_id)
    try:
        row = set_manual_card(db, purchase.id, body.card_key, body.last4)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return build_card_report(purchase, row)

