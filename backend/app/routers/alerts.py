"""
Alert management endpoints.

GET  /alerts?user_id=<uuid>              → List upcoming alerts for a user
GET  /alerts/history?user_id=<uuid>      → List sent/past alerts for a user
POST /alerts/backfill?user_id=<uuid>     → Create missing alert rows for all purchases
POST /alerts/recall-check?user_id=<uuid> → Run recall fuzzy-match check for all purchases
GET  /recalls                            → List all known recall records
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert, Purchase, Recall, User
from app.schemas import (
    AlertOut,
    AlertsListResponse,
    RecallCheckResponse,
    RecallOut,
)
from app.services.alert_engine import backfill_alerts_for_user, get_upcoming_alerts
from app.services.recall_watcher import get_all_recalls, run_recall_check_for_user

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return user


# ── Alert endpoints ───────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=AlertsListResponse,
    summary="List upcoming alerts for a user",
)
def list_alerts(
    user_id: uuid.UUID = Query(..., description="UUID of the user"),
    days_ahead: int = Query(30, ge=1, le=365, description="Look-ahead window in days"),
    db: Session = Depends(get_db),
) -> AlertsListResponse:
    """
    Return all unsent alerts due within the next `days_ahead` days,
    sorted by fire_date ascending (most urgent first).
    """
    _get_user_or_404(db, user_id)
    alerts = get_upcoming_alerts(db, user_id, days_ahead=days_ahead)
    return AlertsListResponse(
        user_id=user_id,
        total=len(alerts),
        alerts=[AlertOut(**a) for a in alerts],
    )


@router.get(
    "/history",
    response_model=AlertsListResponse,
    summary="List past (sent) alerts for a user",
)
def list_alert_history(
    user_id: uuid.UUID = Query(..., description="UUID of the user"),
    db: Session = Depends(get_db),
) -> AlertsListResponse:
    """
    Return all alerts that have already been sent/fired, newest first.
    """
    _get_user_or_404(db, user_id)

    from datetime import date
    alerts_rows = (
        db.query(Alert, Purchase)
        .join(Purchase, Alert.purchase_id == Purchase.id)
        .filter(Purchase.user_id == user_id, Alert.sent == True)  # noqa: E712
        .order_by(Alert.fire_date.desc())
        .all()
    )

    result = []
    for alert, purchase in alerts_rows:
        fire_date_val = alert.fire_date.date()
        days_until = (fire_date_val - date.today()).days
        result.append(AlertOut(
            alert_id=str(alert.id),
            purchase_id=str(purchase.id),
            product_name=purchase.product_name,
            brand=purchase.brand,
            retailer=purchase.retailer,
            alert_type=alert.alert_type,
            fire_date=fire_date_val.isoformat(),
            days_until=days_until,
            is_overdue=days_until < 0,
        ))

    return AlertsListResponse(user_id=user_id, total=len(result), alerts=result)


@router.post(
    "/backfill",
    summary="Create missing alert rows for all user purchases",
)
def backfill_alerts(
    user_id: uuid.UUID = Query(..., description="UUID of the user"),
    db: Session = Depends(get_db),
) -> dict:
    """
    Idempotent: creates alert rows for any purchase that has warranty dates
    but no corresponding alert yet. Safe to call multiple times.
    """
    _get_user_or_404(db, user_id)
    created = backfill_alerts_for_user(db, user_id)
    return {"user_id": str(user_id), "alerts_created": created}


# ── Recall endpoints ──────────────────────────────────────────────────────────

@router.post(
    "/recall-check",
    response_model=RecallCheckResponse,
    summary="Run recall check for all user purchases",
)
def recall_check(
    user_id: uuid.UUID = Query(..., description="UUID of the user"),
    db: Session = Depends(get_db),
) -> RecallCheckResponse:
    """
    Fuzzy-match all user purchases against known recall records.
    Creates recall Alert rows for any matches.
    """
    _get_user_or_404(db, user_id)
    result = run_recall_check_for_user(db, user_id)
    return RecallCheckResponse(
        user_id=user_id,
        purchases_checked=result["purchases_checked"],
        recall_matches=result["recall_matches"],
    )


@router.get(
    "/recalls",
    response_model=list[RecallOut],
    summary="List all known product recall records",
)
def list_recalls(db: Session = Depends(get_db)) -> list[RecallOut]:
    """Return all product recall records in the database."""
    recalls = get_all_recalls(db)
    return [RecallOut(**r) for r in recalls]
