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


# ── WhatsApp proactive notifications ─────────────────────────────────────────

def _format_whatsapp_alert(db: Session, purchase: Purchase, alert: Alert) -> str:
    """Build a concise WhatsApp reminder for a due warranty, return, or recall alert."""
    from app.services.card_benefits import build_card_report, get_payment_method

    today = date.today()
    product = purchase.product_name or "Your product"
    vendor = purchase.retailer or purchase.brand
    vendor_part = f" ({vendor})" if vendor else ""
    wp = purchase.warranty_period

    if alert.alert_type == "return_window_expiry":
        deadline = (wp.return_window_end_date if wp else None) or alert.fire_date.date()
        date_str = deadline.strftime("%d %b %Y")
        days_left = (deadline - today).days
        when = (
            f"closes on {date_str} ({days_left} day(s) left)"
            if days_left >= 0
            else f"closed on {date_str}"
        )
        return (
            f"↩️ Return window reminder: {product}{vendor_part} return window {when}.\n"
            "Check Warranty Agent for Festival Price Drop refund scripts before closing."
        )

    if alert.alert_type == "recall":
        return (
            f"⚠️ Product recall notice: {product}{vendor_part} matched an official recall advisory.\n"
            "Open Warranty Agent for claim details."
        )

    # Default: warranty_expiry
    deadline = (wp.warranty_end_date if wp else None) or alert.fire_date.date()
    date_str = deadline.strftime("%d %b %Y")
    days_left = (deadline - today).days
    when = (
        f"expires on {date_str} ({days_left} day(s) left)"
        if days_left >= 0
        else f"expired on {date_str}"
    )
    lines = [f"⏰ Warranty reminder: {product}{vendor_part} warranty {when}."]

    row = get_payment_method(db, purchase.id)
    if row is not None:
        report = build_card_report(purchase, row, today=today)
        benefit = report.benefit
        if benefit.status == "extended_warranty" and benefit.extension_months:
            until = f" (until {benefit.extended_warranty_end})" if benefit.extended_warranty_end else ""
            lines.append(
                f"💳 Good news: your {benefit.card_label} card may add +{benefit.extension_months} months "
                f"free cover{until} — open Warranty Agent for claim steps."
            )
        elif benefit.status == "needs_card" and report.detected_card and report.detected_card.issuer_label:
            lines.append(
                f"💳 Paid with a {report.detected_card.issuer_label} credit card — open Warranty Agent "
                "to check free extended-warranty perks."
            )

    return "\n".join(lines)


def _notify_whatsapp_if_linked(
    db: Session,
    purchase: Optional[Purchase],
    alert: Alert,
) -> bool:
    """
    Send a WhatsApp reminder if the bot is configured and the purchase owner
    has linked their WhatsApp number. Failures are logged and never block alerts.
    """
    if purchase is None:
        return False

    from app.models import WhatsAppLink
    from app.services.whatsapp_client import get_active_client, is_configured

    if not is_configured():
        return False

    link = (
        db.query(WhatsAppLink)
        .filter(WhatsAppLink.user_id == purchase.user_id, WhatsAppLink.phone_number.isnot(None))
        .first()
    )
    if link is None or not link.phone_number:
        return False

    try:
        message = _format_whatsapp_alert(db, purchase, alert)
        get_active_client().send_text(link.phone_number, message)
        return True
    except Exception as exc:  # noqa: BLE001 - notification error must never break alert loop
        logger.warning(
            "Failed to send WhatsApp alert %s for purchase %s: %s",
            alert.id,
            purchase.id,
            exc,
        )
        return False


# ── Daily scheduler job ───────────────────────────────────────────────────────

def run_daily_alert_check() -> None:
    """
    Daily job: process due alerts, notify linked WhatsApp users, and mark sent.
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
            _notify_whatsapp_if_linked(db, purchase, alert)
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
        if not purchase.product_name or not (purchase.retailer or purchase.brand):
            continue
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
