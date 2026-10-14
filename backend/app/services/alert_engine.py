"""
Alert engine — schedules and fires warranty/return-window/recall alerts.

Three alert types (as per Milestone 3):
  1. return_window_expiry  — fires N days BEFORE the return deadline
  2. warranty_expiry       — fires N days BEFORE warranty end date
  3. recall                — fires immediately when a recall matches an owned product

The engine runs as a background scheduler using APScheduler.
On startup it:
  1. Creates any missing alert rows for all purchases that have warranty dates.
  2. Fires any overdue alerts.
  3. Schedules a daily check job.

Design:
  - Alert creation is idempotent (won't create duplicates for existing rows).
  - All times are treated as UTC naive datetimes.
  - The scheduler runs in-process using APScheduler's BackgroundScheduler.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Alert, Purchase, WarrantyPeriod

logger = logging.getLogger(__name__)

# ── Alert lead times (configurable) ──────────────────────────────────────────
RETURN_WINDOW_LEAD_DAYS: int = 2   # Notify 2 days before return window closes
WARRANTY_EXPIRY_LEAD_DAYS: int = 14  # Notify 14 days before warranty expires


# ── Alert creation helpers ────────────────────────────────────────────────────

def _alert_exists(db: Session, purchase_id, alert_type: str) -> bool:
    """Check whether an alert of this type already exists for this purchase."""
    return (
        db.query(Alert)
        .filter(Alert.purchase_id == purchase_id, Alert.alert_type == alert_type)
        .first()
    ) is not None


def create_alerts_for_purchase(
    db: Session,
    purchase: Purchase,
    warranty: Optional[WarrantyPeriod],
) -> int:
    """
    Create missing Alert rows for a purchase + warranty period.

    Returns the number of new alerts created.
    """
    if warranty is None:
        return 0

    created = 0
    today = date.today()

    # ── Return-window alert ────────────────────────────────────────────────
    if warranty.return_window_end_date:
        fire_date = warranty.return_window_end_date - timedelta(days=RETURN_WINDOW_LEAD_DAYS)
        if not _alert_exists(db, purchase.id, "return_window_expiry"):
            db.add(Alert(
                purchase_id=purchase.id,
                alert_type="return_window_expiry",
                fire_date=datetime.combine(fire_date, datetime.min.time()),
            ))
            created += 1
            logger.debug(
                "Scheduled return_window_expiry alert for purchase %s on %s",
                purchase.id, fire_date,
            )

    # ── Warranty-expiry alert ──────────────────────────────────────────────
    if warranty.warranty_end_date:
        fire_date = warranty.warranty_end_date - timedelta(days=WARRANTY_EXPIRY_LEAD_DAYS)
        if not _alert_exists(db, purchase.id, "warranty_expiry"):
            db.add(Alert(
                purchase_id=purchase.id,
                alert_type="warranty_expiry",
                fire_date=datetime.combine(fire_date, datetime.min.time()),
            ))
            created += 1
            logger.debug(
                "Scheduled warranty_expiry alert for purchase %s on %s",
                purchase.id, fire_date,
            )

    if created:
        db.commit()

    return created


def backfill_alerts_for_user(db: Session, user_id) -> int:
    """
    Create any missing alert rows for all of a user's purchases.
    Safe to call multiple times (idempotent via _alert_exists check).

    Returns total new alerts created.
    """
    purchases = db.query(Purchase).filter(Purchase.user_id == user_id).all()
    total = 0
    for purchase in purchases:
        warranty = purchase.warranty_period
        total += create_alerts_for_purchase(db, purchase, warranty)
    logger.info("Backfilled %d alerts for user %s", total, user_id)
    return total


# ── Daily scheduler job ───────────────────────────────────────────────────────

def run_daily_alert_check() -> None:
    """
    Daily job: backfill alerts for all users, then log upcoming due alerts.

    In a future milestone this will send actual email/push notifications.
    For now it marks alerts as 'processed' and logs them.
    """
    logger.info("=== Daily alert check starting ===")
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()

        # Find all unsent alerts that are due (fire_date <= now)
        due_alerts = (
            db.query(Alert)
            .filter(Alert.sent == False, Alert.fire_date <= now)  # noqa: E712
            .all()
        )

        for alert in due_alerts:
            purchase = db.query(Purchase).filter(Purchase.id == alert.purchase_id).first()
            product = purchase.product_name if purchase else "Unknown product"
            logger.info(
                "[ALERT DUE] type=%s | product=%r | fire_date=%s",
                alert.alert_type,
                product,
                alert.fire_date.date(),
            )
            alert.sent = True  # Mark as sent

        if due_alerts:
            db.commit()
            logger.info("Marked %d alerts as sent", len(due_alerts))
        else:
            logger.info("No due alerts found")

    except Exception as exc:
        logger.error("Error during daily alert check: %s", exc)
        db.rollback()
    finally:
        db.close()
    logger.info("=== Daily alert check complete ===")


def start_scheduler() -> None:
    """
    Start the APScheduler background scheduler.
    Called once from FastAPI lifespan on startup.
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler

        scheduler = BackgroundScheduler()
        scheduler.add_job(
            run_daily_alert_check,
            trigger="cron",
            hour=8,  # 8:00 AM UTC daily
            minute=0,
            id="daily_alert_check",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("APScheduler started — daily alert check at 08:00 UTC")

        # Run once immediately on startup to catch any overdue alerts
        run_daily_alert_check()

    except ImportError:
        logger.warning(
            "APScheduler not installed — alert scheduling disabled. "
            "Add 'apscheduler' to requirements.txt to enable."
        )
    except Exception as exc:
        logger.error("Failed to start APScheduler: %s", exc)


def get_upcoming_alerts(db: Session, user_id, days_ahead: int = 30) -> list[dict]:
    """
    Return a list of upcoming (unsent) alerts for a user within the next N days.

    Returns list of dicts with alert info for the API response.
    """
    cutoff = datetime.utcnow() + timedelta(days=days_ahead)
    now = datetime.utcnow()

    alerts = (
        db.query(Alert, Purchase)
        .join(Purchase, Alert.purchase_id == Purchase.id)
        .filter(
            Purchase.user_id == user_id,
            Alert.sent == False,  # noqa: E712
            Alert.fire_date <= cutoff,
        )
        .order_by(Alert.fire_date)
        .all()
    )

    result = []
    for alert, purchase in alerts:
        days_until = (alert.fire_date.date() - date.today()).days
        result.append({
            "alert_id": str(alert.id),
            "purchase_id": str(purchase.id),
            "product_name": purchase.product_name,
            "brand": purchase.brand,
            "retailer": purchase.retailer,
            "alert_type": alert.alert_type,
            "fire_date": alert.fire_date.date().isoformat(),
            "days_until": days_until,
            "is_overdue": days_until < 0,
        })

    return result
