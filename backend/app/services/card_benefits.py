"""
Credit-card benefit matcher.

Many premium Indian credit cards bundle an insurance-backed *extended warranty*
(typically +1 year after the manufacturer warranty) or *purchase protection*
(damage / theft cover for a limited period). Most cardholders never use it
because nobody reminds them at the moment it matters.

This module:
  1. detects which credit card paid for a purchase from the invoice / order text
     (issuer, optional card variant, last four digits);
  2. matches the card against a small benefit catalogue;
  3. works out the extended-coverage end date and the documents needed to claim.

IMPORTANT - accuracy
--------------------
Card benefits differ by exact variant and change over time, and the catalogue
below is compiled from public summaries, *not* from issuer contracts. The
catalogue is therefore deliberately conservative (it lists only cards where an
extended warranty or purchase protection is publicly reported), every answer is
phrased as "may" and carries a disclaimer, and the user is told to confirm in
their card's current benefit guide before relying on it.

Pure functions plus three small DB helpers; nothing here calls the network.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Optional

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from app.models import Purchase, PurchasePaymentMethod
from app.schemas import (
    CardBenefitOut,
    CardBenefitReport,
    CardOption,
    DetectedCardOut,
)

logger = logging.getLogger(__name__)

CATALOG_LAST_REVIEWED = "2026-11"
OTHER_CARD_KEY = "other_card"

DISCLAIMER = (
    "Benefits differ by exact card variant and change over time. This is guidance "
    "based on public information (catalogue last reviewed "
    f"{CATALOG_LAST_REVIEWED}) - confirm in your card's current benefit guide or "
    "with the issuer before relying on it."
)

# Combined manufacturer + card cover is normally capped at three years.
_MAX_TOTAL_MONTHS = 36
# Card extensions generally need a manufacturer warranty of at least one year.
_MIN_MANUFACTURER_MONTHS = 12


# ── Catalogue ─────────────────────────────────────────────────────────────────

ISSUER_LABELS: dict[str, str] = {
    "hdfc": "HDFC Bank",
    "icici": "ICICI Bank",
    "axis": "Axis Bank",
    "sbi": "SBI Card",
    "kotak": "Kotak Mahindra Bank",
    "amex": "American Express",
    "idfc": "IDFC FIRST Bank",
    "yes": "YES Bank",
    "rbl": "RBL Bank",
    "indusind": "IndusInd Bank",
    "au": "AU Small Finance Bank",
    "sc": "Standard Chartered",
    "hsbc": "HSBC",
    "citi": "Citibank",
    "federal": "Federal Bank",
    "bob": "Bank of Baroda (BOBCARD)",
}

_ISSUER_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("hdfc", re.compile(r"\bhdfc\b", re.I)),
    ("icici", re.compile(r"\bicici\b", re.I)),
    ("axis", re.compile(r"\baxis\b", re.I)),
    ("sbi", re.compile(r"\bsbi\b|state\s+bank\s+of\s+india", re.I)),
    ("kotak", re.compile(r"\bkotak\b", re.I)),
    ("amex", re.compile(r"\bamerican\s+express\b|\bamex\b", re.I)),
    ("idfc", re.compile(r"\bidfc\b", re.I)),
    ("yes", re.compile(r"\byes\s+bank\b", re.I)),
    ("rbl", re.compile(r"\brbl\b", re.I)),
    ("indusind", re.compile(r"\bindusind\b", re.I)),
    ("au", re.compile(r"\bau\s+(?:small\s+finance|bank)\b", re.I)),
    ("sc", re.compile(r"standard\s+chartered", re.I)),
    ("hsbc", re.compile(r"\bhsbc\b", re.I)),
    ("citi", re.compile(r"\bciti(?:bank)?\b", re.I)),
    ("federal", re.compile(r"\bfederal\s+bank\b", re.I)),
    ("bob", re.compile(r"\bbobcard\b|bank\s+of\s+baroda", re.I)),
]


@dataclass(frozen=True)
class CardProfile:
    """One card in the benefit catalogue."""

    key: str
    issuer: str
    name: str
    extended_warranty_months: int = 0
    protection_summary: Optional[str] = None
    insurer: Optional[str] = None
    variant_pattern: Optional[re.Pattern[str]] = None


def _p(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.I)


_CATALOG_LIST: list[CardProfile] = [
    CardProfile(
        key="axis_magnus",
        issuer="axis",
        name="Axis Bank Magnus",
        extended_warranty_months=12,
        protection_summary=(
            "Reported to include extended warranty and purchase protection on "
            "eligible items bought with the card. Limits vary - check your benefit guide."
        ),
        variant_pattern=_p(r"\bmagnus\b"),
    ),
    CardProfile(
        key="axis_reserve",
        issuer="axis",
        name="Axis Bank Reserve",
        extended_warranty_months=12,
        protection_summary=(
            "Reported to include extended warranty and purchase protection on "
            "eligible items bought with the card. Limits vary - check your benefit guide."
        ),
        variant_pattern=_p(r"\breserve\b"),
    ),
    CardProfile(
        key="icici_sapphiro",
        issuer="icici",
        name="ICICI Bank Sapphiro",
        protection_summary=(
            "Reported to include a card protection plan for damage / theft of items "
            "bought with the card. A standalone extended warranty is not confirmed."
        ),
        variant_pattern=_p(r"\bsapphiro\b"),
    ),
    CardProfile(
        key="icici_emeralde",
        issuer="icici",
        name="ICICI Bank Emeralde",
        protection_summary=(
            "Reported to include a card protection plan for damage / theft of items "
            "bought with the card. A standalone extended warranty is not confirmed."
        ),
        variant_pattern=_p(r"\bemeralde\b"),
    ),
    CardProfile(
        key="amex_platinum_charge",
        issuer="amex",
        name="American Express Platinum Charge",
        protection_summary=(
            "Reported purchase protection (about 90 days from purchase) against theft "
            "and accidental damage. This is not an extended warranty."
        ),
        variant_pattern=_p(r"platinum\s+charge"),
    ),
    CardProfile(
        key="hdfc_infinia",
        issuer="hdfc",
        name="HDFC Bank Infinia",
        protection_summary=(
            "Insurance-backed cover for damage / theft / burglary of items bought with "
            "the card, for a limited period. No standalone extended warranty is documented."
        ),
        insurer="HDFC ERGO General Insurance",
        variant_pattern=_p(r"\binfinia\b"),
    ),
    CardProfile(
        key="hdfc_diners_black",
        issuer="hdfc",
        name="HDFC Bank Diners Club Black",
        protection_summary=(
            "Insurance-backed cover for damage / theft / burglary of items bought with "
            "the card, for a limited period. No standalone extended warranty is documented."
        ),
        insurer="HDFC ERGO General Insurance",
        variant_pattern=_p(r"diners?\s+club\s+black|diners\s+black"),
    ),
    CardProfile(
        key="hdfc_regalia",
        issuer="hdfc",
        name="HDFC Bank Regalia",
        protection_summary=(
            "Insurance-backed cover for damage / theft / burglary of items bought with "
            "the card, for a limited period. No standalone extended warranty is documented."
        ),
        insurer="HDFC ERGO General Insurance",
        variant_pattern=_p(r"\bregalia\b"),
    ),
]

CARD_CATALOG: dict[str, CardProfile] = {c.key: c for c in _CATALOG_LIST}


def list_card_options() -> list[CardOption]:
    """Cards the user can pick from, plus an 'other' escape hatch."""
    options = [CardOption(key=c.key, label=c.name, issuer=c.issuer) for c in _CATALOG_LIST]
    options.append(CardOption(key=OTHER_CARD_KEY, label="My card isn't listed", issuer="other"))
    return options


# ── Detection ────────────────────────────────────────────────────────────────

_CREDIT_RE = re.compile(r"(?:credit|charge)\s*card", re.I)
_DEBIT_RE = re.compile(r"debit\s*card", re.I)
_LAST4_RE = re.compile(
    r"(?:ending(?:\s+in|\s+with)?|last\s*4(?:\s*digits)?|x{2,}|\*{2,}|•{2,}|\.{3,})"
    r"\s*[:\-]?\s*(\d{4})\b",
    re.I,
)
_MAX_SCAN_CHARS = 200_000


@dataclass
class DetectedCard:
    issuer: str
    card_key: Optional[str]
    last4: Optional[str]
    evidence: str


def detect_payment_card(text: Optional[str]) -> Optional[DetectedCard]:
    """
    Find the credit card used to pay, e.g. "HDFC Bank Credit Card ending 4021".

    Only *credit* cards count (debit cards carry none of these benefits). When
    several issuers appear, the one mentioned first in the document wins.
    Returns None when no issuer is mentioned next to the words "credit card".
    """
    if not text or not text.strip():
        return None

    flat = re.sub(r"\s+", " ", text[:_MAX_SCAN_CHARS])
    candidates: list[tuple[int, str, str]] = []

    for issuer, pattern in _ISSUER_PATTERNS:
        for m in pattern.finditer(flat):
            start = max(0, m.start() - 60)
            window = flat[start : m.end() + 90]
            credit = _CREDIT_RE.search(window)
            if not credit:
                continue
            issuer_pos = m.start() - start
            debit = _DEBIT_RE.search(window)
            if debit and abs(debit.start() - issuer_pos) < abs(credit.start() - issuer_pos):
                continue  # a debit card is the closer mention
            candidates.append((m.start(), issuer, window))
            break  # first qualifying mention per issuer is enough

    if not candidates:
        return None

    _, issuer, window = min(candidates, key=lambda c: c[0])

    card_key: Optional[str] = None
    for profile in _CATALOG_LIST:
        if profile.issuer == issuer and profile.variant_pattern and profile.variant_pattern.search(window):
            card_key = profile.key
            break

    last4_match = _LAST4_RE.search(window)
    return DetectedCard(
        issuer=issuer,
        card_key=card_key,
        last4=last4_match.group(1) if last4_match else None,
        evidence=window.strip()[:200],
    )


# ── Benefit analysis ─────────────────────────────────────────────────────────

_COMMON_CONDITIONS = [
    "The item must be paid for in full on this credit card - split payments, "
    "part-UPI/cash, or certain EMI / voucher payments can void a claim.",
    "The product needs a valid Indian manufacturer warranty (usually at least 12 months).",
]
_EXTENDED_CONDITIONS = _COMMON_CONDITIONS + [
    "Extended warranty covers mechanical / electrical breakdown from manufacturing "
    "defects - not accidental damage, wear and tear, or commercial use.",
    "Manufacturer plus card cover is normally capped at 3 years in total.",
]
_PROTECTION_CONDITIONS = _COMMON_CONDITIONS + [
    "Purchase protection covers damage / theft / burglary within a limited window "
    "after purchase, not ordinary breakdown.",
]

_EXTENDED_CLAIM_STEPS = [
    "Keep the credit card statement line showing this purchase.",
    "Keep the tax invoice (Warranty Agent already holds this one) and the manufacturer warranty card.",
    "When the fault appears after the manufacturer warranty ends, get a job sheet from an "
    "authorised service centre stating the fault is a manufacturing / internal defect.",
    "Report the claim to the card's insurance helpdesk (see your card benefit guide) as soon as "
    "the fault is found - claim windows are short.",
]
_PROTECTION_CLAIM_STEPS = [
    "Report the incident to the card insurer immediately - windows are usually days, not months.",
    "For theft or burglary, file an FIR; for damage, keep photos and an authorised service-centre estimate.",
    "Send the tax invoice and the credit card statement line for this purchase.",
]


def _fmt_date(d: date) -> str:
    return d.strftime("%d %b %Y")


def _benefit(status: str, headline: str, **kwargs) -> CardBenefitOut:
    return CardBenefitOut(status=status, headline=headline, disclaimer=DISCLAIMER, **kwargs)


def analyze_card_benefit(
    purchase: Purchase,
    card_key: Optional[str],
    issuer: Optional[str] = None,
    today: Optional[date] = None,
) -> CardBenefitOut:
    """Work out what, if anything, the card adds on top of the manufacturer warranty."""
    today = today or date.today()

    if card_key is None:
        label = ISSUER_LABELS.get(issuer or "")
        if label:
            return _benefit(
                "needs_card",
                f"We spotted a {label} credit card on this invoice. Pick your exact card "
                "to see whether it adds free cover.",
            )
        return _benefit(
            "needs_card",
            "Paid with a credit card? Pick it to check for free extended-warranty or "
            "purchase-protection perks.",
        )

    if card_key == OTHER_CARD_KEY or card_key not in CARD_CATALOG:
        return _benefit(
            "no_known_benefit",
            "We don't have benefit data for this card. Check its benefit guide for "
            "extended warranty or purchase protection.",
        )

    card = CARD_CATALOG[card_key]

    if card.extended_warranty_months <= 0:
        return _benefit(
            "purchase_protection_only",
            f"{card.name} offers purchase protection, not an extended warranty.",
            card_label=card.name,
            protection_summary=card.protection_summary,
            insurer=card.insurer,
            conditions=_PROTECTION_CONDITIONS,
            claim_steps=_PROTECTION_CLAIM_STEPS,
        )

    wp = purchase.warranty_period
    warranty_end = wp.warranty_end_date if wp else None
    base_months: Optional[int] = None
    if warranty_end and purchase.purchase_date:
        base_months = round((warranty_end - purchase.purchase_date).days / 30.44)

    estimated_hint = " (estimated - confirm on your warranty card)" if wp and wp.is_estimated else ""

    if base_months is not None and base_months < _MIN_MANUFACTURER_MONTHS:
        return _benefit(
            "not_eligible",
            f"This item's manufacturer warranty looks like {base_months} months{estimated_hint}; "
            f"card extensions usually need at least {_MIN_MANUFACTURER_MONTHS}.",
            card_label=card.name,
            protection_summary=card.protection_summary,
            conditions=_EXTENDED_CONDITIONS,
            manufacturer_warranty_end=_fmt_date(warranty_end) if warranty_end else None,
        )

    extension = card.extended_warranty_months
    if base_months is not None:
        extension = min(extension, max(0, _MAX_TOTAL_MONTHS - base_months))
    if extension <= 0:
        return _benefit(
            "not_eligible",
            "This item already has the maximum 3 years of cover, so the card adds nothing more.",
            card_label=card.name,
            conditions=_EXTENDED_CONDITIONS,
            manufacturer_warranty_end=_fmt_date(warranty_end) if warranty_end else None,
        )

    if warranty_end is None:
        return _benefit(
            "extended_warranty",
            f"{card.name} may add +{extension} months of free cover after your manufacturer "
            "warranty ends.",
            card_label=card.name,
            extension_months=extension,
            protection_summary=card.protection_summary,
            insurer=card.insurer,
            conditions=_EXTENDED_CONDITIONS,
            claim_steps=_EXTENDED_CLAIM_STEPS,
        )

    extended_end = warranty_end + relativedelta(months=extension)
    days_left = (extended_end - today).days
    if days_left < 0:
        headline = f"{card.name}'s extra cover for this item ended on {_fmt_date(extended_end)}."
    else:
        headline = (
            f"{card.name} may add +{extension} months of free cover - "
            f"until {_fmt_date(extended_end)} ({days_left} days from today){estimated_hint}."
        )
    return _benefit(
        "extended_warranty",
        headline,
        card_label=card.name,
        extension_months=extension,
        manufacturer_warranty_end=_fmt_date(warranty_end),
        extended_warranty_end=_fmt_date(extended_end),
        days_until_extended_end=days_left,
        protection_summary=card.protection_summary,
        insurer=card.insurer,
        conditions=_EXTENDED_CONDITIONS,
        claim_steps=_EXTENDED_CLAIM_STEPS,
    )


def build_card_report(
    purchase: Purchase,
    row: Optional[PurchasePaymentMethod],
    today: Optional[date] = None,
) -> CardBenefitReport:
    """Full response for GET /purchases/{id}/card-benefits."""
    detected: Optional[DetectedCardOut] = None
    card_key = row.card_key if row else None
    issuer = row.issuer if row else None

    if row is not None:
        profile = CARD_CATALOG.get(card_key or "")
        if profile:
            issuer = issuer or profile.issuer
        detected = DetectedCardOut(
            issuer=issuer,
            issuer_label=ISSUER_LABELS.get(issuer or ""),
            card_key=card_key,
            card_label=profile.name if profile else None,
            last4=row.last4,
            source=row.source,
            evidence=row.evidence,
        )

    return CardBenefitReport(
        purchase_id=purchase.id,
        detected_card=detected,
        options=list_card_options(),
        benefit=analyze_card_benefit(purchase, card_key, issuer, today),
    )


# ── Persistence helpers ──────────────────────────────────────────────────────

def get_payment_method(db: Session, purchase_id: uuid.UUID) -> Optional[PurchasePaymentMethod]:
    return (
        db.query(PurchasePaymentMethod)
        .filter(PurchasePaymentMethod.purchase_id == purchase_id)
        .first()
    )


def record_detected_card(
    db: Session, purchase_id: uuid.UUID, text: Optional[str]
) -> Optional[PurchasePaymentMethod]:
    """
    Detect the card in ``text`` and store it for the purchase.

    A card the user chose by hand is never overwritten by detection. Only the
    issuer, variant key, last four digits and a short evidence snippet are kept.
    """
    detected = detect_payment_card(text)
    if detected is None:
        return None

    row = get_payment_method(db, purchase_id)
    if row is not None and row.source == "manual":
        return row

    if row is None:
        row = PurchasePaymentMethod(purchase_id=purchase_id)
        db.add(row)
    row.issuer = detected.issuer
    row.card_key = detected.card_key
    row.last4 = detected.last4
    row.source = "detected"
    row.evidence = detected.evidence
    db.commit()
    db.refresh(row)
    return row


def set_manual_card(
    db: Session,
    purchase_id: uuid.UUID,
    card_key: Optional[str],
    last4: Optional[str] = None,
) -> Optional[PurchasePaymentMethod]:
    """
    Save the card the user picked. ``card_key=None`` clears the choice.

    Raises ValueError for a key that is neither in the catalogue nor 'other_card'.
    """
    row = get_payment_method(db, purchase_id)

    if card_key is None:
        if row is not None:
            db.delete(row)
            db.commit()
        return None

    if card_key != OTHER_CARD_KEY and card_key not in CARD_CATALOG:
        raise ValueError(f"Unknown card_key {card_key!r}")

    if row is None:
        row = PurchasePaymentMethod(purchase_id=purchase_id)
        db.add(row)
    profile = CARD_CATALOG.get(card_key)
    row.card_key = card_key
    row.issuer = profile.issuer if profile else (row.issuer or "other")
    row.last4 = last4 or row.last4
    row.source = "manual"
    db.commit()
    db.refresh(row)
    return row

