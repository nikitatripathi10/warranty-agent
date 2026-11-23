"""
Forward-to-email ingestion.

Every user gets a private address, ``bills+<token>@<INBOUND_EMAIL_DOMAIN>``.
Forwarding an Amazon / Flipkart / any order email (with or without a PDF or
photo attachment) to it saves the purchase - from Gmail, Outlook, Yahoo or any
other mail app, with no Gmail OAuth and therefore no Google security audit.

Flow
----
mail provider -> Cloudflare Email Routing -> Email Worker (infra/cloudflare-email-worker)
              -> POST /ingestion/inbound-email  (shared-secret header)
              -> this module: same extraction / de-duplication / card detection as
                 Gmail sync and web uploads, then an optional WhatsApp confirmation.

The email body is never stored; only the extracted purchase fields, the
forwarded message id (for idempotency) and, if one was attached, the invoice file.
"""

from __future__ import annotations

import base64
import binascii
import logging
import os
import re
import secrets
import string
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import EmailInbox, Purchase, User, WhatsAppLink
from app.routers.ingestion import (
    _find_existing_duplicate_purchase,
    _is_valid_extracted_purchase,
    _persist_purchase,
    _run_extraction_pipeline,
    process_file_bytes,
)
from app.services import whatsapp_client
from app.services.extractor_regex import ExtractionResult
from app.services.whatsapp_bot import SlidingWindowLimiter, format_saved_reply

logger = logging.getLogger(__name__)

TOKEN_LENGTH = 10
_TOKEN_ALPHABET = string.ascii_lowercase + string.digits
ADDRESS_LOCAL_PREFIX = "bills"
MAX_ATTACHMENTS = 5
MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024
MAX_BODY_CHARS = 200_000
VERIFICATION_CODE_TTL = timedelta(hours=24)

# At most 60 forwarded emails per inbox per hour (in-memory, per process).
inbound_limiter = SlidingWindowLimiter(limit=60, window_seconds=3600)

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+")
_LOCAL_RE = re.compile(rf"^{ADDRESS_LOCAL_PREFIX}\+([a-z0-9]{{6,32}})$")
_CODE_BODY_RE = re.compile(r"(?:confirmation\s+code|verification\s+code|code)\D{0,40}?(\d{6,9})", re.I)
_CODE_SUBJECT_RE = re.compile(r"\(#(\d{6,9})\)")


# ── Configuration ────────────────────────────────────────────────────────────

def inbound_domain() -> Optional[str]:
    return os.getenv("INBOUND_EMAIL_DOMAIN", "").strip().lower().lstrip("@") or None


def inbound_secret() -> Optional[str]:
    return os.getenv("INBOUND_EMAIL_SECRET", "").strip() or None


def is_enabled() -> bool:
    """True when the server has both a mail domain and the shared secret."""
    return bool(inbound_domain() and inbound_secret())


# ── Inbox addresses ──────────────────────────────────────────────────────────

def generate_inbox_token() -> str:
    return "".join(secrets.choice(_TOKEN_ALPHABET) for _ in range(TOKEN_LENGTH))


def build_address(token: str, domain: Optional[str] = None) -> Optional[str]:
    domain = domain or inbound_domain()
    if not domain:
        return None
    return f"{ADDRESS_LOCAL_PREFIX}+{token}@{domain}"


def extract_token_from_address(to_field: Optional[str]) -> Optional[str]:
    """
    Pull the inbox token out of a recipient header such as
    ``"Bills <bills+k7p2qm9a4x@warrantyagent.in>, other@x.com"``.

    When INBOUND_EMAIL_DOMAIN is set, the address must be on that domain.
    """
    if not to_field:
        return None
    domain = inbound_domain()
    for address in _EMAIL_RE.findall(to_field):
        local, _, addr_domain = address.lower().rpartition("@")
        if domain and addr_domain != domain:
            continue
        match = _LOCAL_RE.match(local)
        if match:
            return match.group(1)
    return None


def _new_unique_token(db: Session) -> str:
    for _ in range(20):
        token = generate_inbox_token()
        if db.query(EmailInbox).filter(EmailInbox.inbox_token == token).first() is None:
            return token
    raise RuntimeError("Could not allocate a unique inbox token")  # pragma: no cover


def get_or_create_inbox(db: Session, user: User) -> EmailInbox:
    inbox = db.query(EmailInbox).filter(EmailInbox.user_id == user.id).first()
    if inbox is None:
        inbox = EmailInbox(user_id=user.id, inbox_token=_new_unique_token(db))
        db.add(inbox)
        db.commit()
        db.refresh(inbox)
    return inbox


def rotate_inbox(db: Session, user: User) -> EmailInbox:
    """Replace the user's token; the old address stops working immediately."""
    inbox = get_or_create_inbox(db, user)
    inbox.inbox_token = _new_unique_token(db)
    inbox.verification_code = None
    inbox.verification_received_at = None
    db.commit()
    db.refresh(inbox)
    return inbox


def find_user_by_token(db: Session, token: str) -> Optional[User]:
    inbox = db.query(EmailInbox).filter(EmailInbox.inbox_token == (token or "").lower()).first()
    return db.get(User, inbox.user_id) if inbox else None


def active_verification_code(inbox: EmailInbox, now: Optional[datetime] = None) -> Optional[str]:
    """The latest Gmail forwarding code, if it arrived within the last 24 hours."""
    now = now or datetime.utcnow()
    if inbox.verification_code and inbox.verification_received_at:
        if now - inbox.verification_received_at <= VERIFICATION_CODE_TTL:
            return inbox.verification_code
    return None


# ── Gmail forwarding confirmation ────────────────────────────────────────────

def detect_forwarding_confirmation(sender: str, subject: str, body: str) -> Optional[str]:
    """
    Return the confirmation code from Gmail's "forwarding confirmation" email.

    Gmail refuses to forward until the owner enters this code, so we capture it
    and show it in the app instead of treating the email as a bill.
    """
    sender_l = (sender or "").lower()
    subject_l = (subject or "").lower()
    if "forwarding-noreply@google.com" not in sender_l and "gmail forwarding confirmation" not in subject_l:
        return None
    for pattern, haystack in ((_CODE_SUBJECT_RE, subject or ""), (_CODE_BODY_RE, body or "")):
        match = pattern.search(haystack)
        if match:
            return match.group(1)
    return None


# ── Processing ───────────────────────────────────────────────────────────────

@dataclass
class InboundAttachmentData:
    filename: str
    content_type: str
    data: bytes


@dataclass
class InboundResult:
    status: str  # 'saved' | 'duplicate' | 'unreadable' | 'forwarding_confirmation'
    purchase: Optional[Purchase] = None


def decode_attachments(raw: list[tuple[str, str, str]]) -> list[InboundAttachmentData]:
    """Decode base64 attachments, skipping corrupt, empty or oversized ones (max 5)."""
    decoded: list[InboundAttachmentData] = []
    for filename, content_type, b64 in raw[:MAX_ATTACHMENTS]:
        try:
            data = base64.b64decode(b64, validate=False)
        except (binascii.Error, ValueError):
            logger.warning("Skipping attachment %r: invalid base64", filename)
            continue
        if not data or len(data) > MAX_ATTACHMENT_BYTES:
            continue
        decoded.append(InboundAttachmentData(filename or "attachment", content_type or "", data))
    return decoded


def _retailer_hint(body: str) -> Optional[str]:
    lowered = body.lower()
    for name in ("amazon", "flipkart", "meesho", "ajio"):
        if name in lowered:
            return name
    return None


def _merge_missing(target: ExtractionResult, source: Optional[ExtractionResult]) -> None:
    """Fill fields the attachment extraction left blank from the email-body extraction."""
    if source is None:
        return
    for field in ("brand", "retailer", "purchase_date", "price", "warranty_period_months", "return_window_days"):
        if getattr(target, field) is None and getattr(source, field) is not None:
            setattr(target, field, getattr(source, field))
    payload = "\n".join(p for p in (target.payment_text, source.payment_text) if p)
    target.payment_text = payload or None


def process_inbound_email(
    db: Session,
    user: User,
    *,
    sender: str = "",
    subject: str = "",
    text: str = "",
    html: str = "",
    message_id: str = "",
    attachments: Optional[list[InboundAttachmentData]] = None,
) -> InboundResult:
    """Run one forwarded email through the same pipeline as Gmail sync and uploads."""
    attachments = attachments or []
    main_text = text if (text or "").strip() else (html or "")
    body = ((f"Subject: {subject}\n" if subject else "") + main_text)[:MAX_BODY_CHARS]

    code = detect_forwarding_confirmation(sender, subject, body)
    if code:
        inbox = get_or_create_inbox(db, user)
        inbox.verification_code = code
        inbox.verification_received_at = datetime.utcnow()
        db.commit()
        return InboundResult("forwarding_confirmation")

    source_id = f"fwd:{message_id.strip()}"[:255] if (message_id or "").strip() else None
    if source_id:
        already = (
            db.query(Purchase)
            .filter(Purchase.user_id == user.id, Purchase.source_email_id == source_id)
            .first()
        )
        if already is not None:
            return InboundResult("duplicate", already)

    body_result: Optional[ExtractionResult] = None
    if body.strip():
        body_result = _run_extraction_pipeline(body, hint=_retailer_hint(body))

    result = body_result
    source_file_ref: Optional[str] = None
    body_is_enough = (
        body_result is not None
        and _is_valid_extracted_purchase(body_result)
        and body_result.confidence == "high"
        and body_result.warranty_period_months is not None
    )
    if not body_is_enough:
        for att in attachments:
            try:
                ref, _name, att_result, _ocr = process_file_bytes(att.data, att.filename, att.content_type)
            except HTTPException as exc:
                logger.warning("Skipping attachment %r: %s", att.filename, exc.detail)
                continue
            _merge_missing(att_result, body_result)
            if _is_valid_extracted_purchase(att_result):
                result, source_file_ref = att_result, ref
                break

    if result is None or not _is_valid_extracted_purchase(result):
        return InboundResult("unreadable")

    duplicate = _find_existing_duplicate_purchase(db, user.id, result, source_file_ref)
    purchase = _persist_purchase(
        db,
        user_id=user.id,
        result=result,
        source_type="email",
        source_email_id=source_id,
        source_file_ref=source_file_ref,
    )
    return InboundResult("duplicate" if duplicate is not None else "saved", purchase)


# ── Optional WhatsApp confirmation ───────────────────────────────────────────

def notify_whatsapp(db: Session, user_id: uuid.UUID, result: InboundResult) -> bool:
    """Tell the user on WhatsApp that their forwarded bill was processed (best effort)."""
    if result.purchase is None or not whatsapp_client.is_configured():
        return False
    link = (
        db.query(WhatsAppLink)
        .filter(WhatsAppLink.user_id == user_id, WhatsAppLink.phone_number.isnot(None))
        .first()
    )
    if link is None or not link.phone_number:
        return False
    try:
        summary = format_saved_reply(db, result.purchase, was_duplicate=result.status == "duplicate")
        whatsapp_client.get_active_client().send_text(
            link.phone_number, f"📧 Forwarded email processed\n{summary}"
        )
        return True
    except Exception as exc:  # noqa: BLE001 - a failed notification must never fail ingestion
        logger.warning("Could not send WhatsApp confirmation for forwarded email: %s", exc)
        return False

