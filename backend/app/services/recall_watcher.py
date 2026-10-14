"""
Recall / product defect watcher.

Checks user-owned products against known recall records in the database
using fuzzy matching (rapidfuzz) on brand + model name.

Design:
  - RapidFuzz is used for approximate string matching (handles minor spelling
    differences, abbreviations, model-number variants).
  - The match threshold is intentionally conservative (80%) to avoid false
    positives that would alarm users unnecessarily.
  - In Milestone 3, recall data is seeded manually / via the admin endpoint.
    A future milestone will auto-fetch from public recall APIs.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Alert, Purchase, Recall
from datetime import datetime

logger = logging.getLogger(__name__)

# Fuzzy-match threshold (0-100). 80 = conservative; lower = more matches.
_FUZZY_THRESHOLD = 80


def _fuzzy_score(a: str, b: str) -> float:
    """Return a rapidfuzz token_set_ratio score between two strings."""
    try:
        from rapidfuzz import fuzz
        return fuzz.token_set_ratio(a.lower(), b.lower())
    except ImportError:
        logger.warning("rapidfuzz not installed — recall matching disabled")
        return 0.0


def check_recalls_for_purchase(
    db: Session,
    purchase: Purchase,
) -> list[Recall]:
    """
    Check whether any known recall matches this purchase.

    Matches on brand + product_model using rapidfuzz token_set_ratio.

    Returns:
        List of matching Recall objects (may be empty).
    """
    recalls = db.query(Recall).all()
    matches: list[Recall] = []

    # Build a combined search string for the purchase
    purchase_text = " ".join(
        part for part in [purchase.brand, purchase.product_name] if part
    )
    if not purchase_text.strip():
        return []

    for recall in recalls:
        recall_text = " ".join(
            part for part in [recall.brand, recall.product_model] if part
        )
        if not recall_text.strip():
            continue

        score = _fuzzy_score(purchase_text, recall_text)
        if score >= _FUZZY_THRESHOLD:
            logger.info(
                "Recall match: purchase '%s' ↔ recall '%s' (score=%.0f)",
                purchase_text,
                recall_text,
                score,
            )
            matches.append(recall)

    return matches


def create_recall_alerts(db: Session, purchase: Purchase, recalls: list[Recall]) -> int:
    """
    Create recall Alert rows for matched recalls if they don't already exist.

    Recall alerts fire immediately (fire_date = now).

    Returns: Number of new alerts created.
    """
    created = 0
    for recall in recalls:
        # Alert ID is per-purchase, not per-recall (simplification for M3)
        existing = (
            db.query(Alert)
            .filter(
                Alert.purchase_id == purchase.id,
                Alert.alert_type == "recall",
            )
            .first()
        )
        if not existing:
            db.add(Alert(
                purchase_id=purchase.id,
                alert_type="recall",
                fire_date=datetime.utcnow(),  # Fires immediately
            ))
            created += 1
            logger.warning(
                "Created RECALL alert for purchase %s (product=%r)",
                purchase.id,
                purchase.product_name,
            )

    if created:
        db.commit()

    return created


def run_recall_check_for_user(db: Session, user_id) -> dict:
    """
    Run recall check for all of a user's purchases.

    Returns:
        Dict with 'checked', 'matches' counts.
    """
    purchases = db.query(Purchase).filter(Purchase.user_id == user_id).all()
    total_matches = 0

    for purchase in purchases:
        matches = check_recalls_for_purchase(db, purchase)
        if matches:
            total_matches += create_recall_alerts(db, purchase, matches)

    return {"purchases_checked": len(purchases), "recall_matches": total_matches}


def get_all_recalls(db: Session) -> list[dict]:
    """Return all recall records as dicts for API responses."""
    recalls = db.query(Recall).order_by(Recall.date_found.desc()).all()
    return [
        {
            "id": str(r.id),
            "brand": r.brand,
            "product_model": r.product_model,
            "description": r.description,
            "source_url": r.source_url,
            "date_found": r.date_found.isoformat() if r.date_found else None,
        }
        for r in recalls
    ]
