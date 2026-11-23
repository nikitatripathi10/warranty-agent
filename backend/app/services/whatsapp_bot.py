"""
WhatsApp bot — forward a bill, get it tracked.

Flow
----
1. In the web app the user taps "Link WhatsApp"; the API issues a short-lived
   code. The user sends ``LINK <code>`` to the bot's number. Sending the code
   from the phone proves they control both the chat and the account.
2. After that, any photo / PDF of a bill, or pasted order text, sent from that
   number runs through the same extraction pipeline as web uploads
   (regex -> Gemini Vision / OCR fallback), is de-duplicated, saved with
   ``source_type='whatsapp'`` and answered with a short summary.
3. ``LIST`` shows what expires soonest; ``UNLINK`` disconnects the chat.

Numbers that are not linked can only receive linking instructions - nothing is
stored or extracted for them.

This module is transport-agnostic: ``process_incoming`` takes any client with
``download_media`` and ``send_text`` (the real one is in whatsapp_client.py,
tests use a fake).
"""

from __future__ import annotations

import logging
import re
import secrets
import threading
import uuid
from collections import OrderedDict, deque
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional, Protocol

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Purchase, User, WhatsAppLink
from app.routers.ingestion import (
    _find_existing_duplicate_purchase,
    _is_valid_extracted_purchase,
    _persist_purchase,
    _run_extraction_pipeline,
    process_file_bytes,
)
from app.services.card_benefits import build_card_report, get_payment_method
from app.services.extractor_regex import ExtractionResult
from app.services.whatsapp_client import WhatsAppError

logger = logging.getLogger(__name__)

LINK_CODE_TTL_MINUTES = 15
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I to avoid typos
_MIN_TEXT_LEN_FOR_BILL = 25
_ALLOWED_MEDIA = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class MessagingClient(Protocol):
    def download_media(self, media_id: str) -> tuple[bytes, str]: ...
    def send_text(self, to: str, body: str) -> None: ...


# ── Incoming message model + webhook parsing ─────────────────────────────────

@dataclass
class IncomingMessage:
    message_id: str
    from_number: str  # digits only, with country code
    type: str  # 'text' | 'image' | 'document' | anything else WhatsApp sends
    text: Optional[str] = None
    media_id: Optional[str] = None
    mime_type: Optional[str] = None
    filename: Optional[str] = None
    caption: Optional[str] = None


def _digits(value: str) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def parse_webhook_payload(payload: dict) -> list[IncomingMessage]:
    """Extract user messages from a WhatsApp Cloud API webhook body (ignores status updates)."""
    messages: list[IncomingMessage] = []
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            for raw in value.get("messages") or []:
                mtype = raw.get("type", "")
                msg = IncomingMessage(
                    message_id=str(raw.get("id", "")),
                    from_number=_digits(str(raw.get("from", ""))),
                    type=mtype,
                )
                if mtype == "text":
                    msg.text = (raw.get("text") or {}).get("body")
                elif mtype in ("image", "document"):
                    media = raw.get(mtype) or {}
                    msg.media_id = media.get("id")
                    msg.mime_type = media.get("mime_type")
                    msg.filename = media.get("filename")
                    msg.caption = media.get("caption")
                if msg.message_id and msg.from_number:
                    messages.append(msg)
    return messages


def parse_twilio_payload(params: dict[str, str]) -> Optional[IncomingMessage]:
    """Extract an IncomingMessage from a Twilio WhatsApp webhook form body."""
    message_id = (params.get("MessageSid") or params.get("SmsMessageSid") or "").strip()
    from_number = _digits(params.get("From", ""))
    if not message_id or not from_number:
        return None

    try:
        num_media = int(params.get("NumMedia") or "0")
    except ValueError:
        num_media = 0

    media_url = (params.get("MediaUrl0") or "").strip()
    if num_media >= 1 and media_url:
        mime = (params.get("MediaContentType0") or "").split(";")[0].strip().lower()
        mtype = "image" if mime.startswith("image/") else "document"
        caption = (params.get("Body") or "").strip() or None
        return IncomingMessage(
            message_id=message_id,
            from_number=from_number,
            type=mtype,
            media_id=media_url,
            mime_type=mime,
            caption=caption,
        )

    return IncomingMessage(
        message_id=message_id,
        from_number=from_number,
        type="text",
        text=params.get("Body") or "",
    )


# ── Abuse protection (in-memory, per process) ────────────────────────────────

class SlidingWindowLimiter:
    """Allow at most ``limit`` events per ``window_seconds`` for each key."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self._limit = limit
        self._window = window_seconds
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, now: Optional[float] = None) -> bool:
        import time

        now = time.monotonic() if now is None else now
        with self._lock:
            events = self._events.setdefault(key, deque())
            while events and now - events[0] > self._window:
                events.popleft()
            if len(events) >= self._limit:
                return False
            events.append(now)
            return True


class SeenMessageIds:
    """Remember recent WhatsApp message ids so retried deliveries are not processed twice."""

    def __init__(self, max_size: int = 2000) -> None:
        self._max = max_size
        self._ids: OrderedDict[str, None] = OrderedDict()
        self._lock = threading.Lock()

    def seen_before(self, message_id: str) -> bool:
        with self._lock:
            if message_id in self._ids:
                return True
            self._ids[message_id] = None
            while len(self._ids) > self._max:
                self._ids.popitem(last=False)
            return False


message_limiter = SlidingWindowLimiter(limit=30, window_seconds=3600)
link_attempt_limiter = SlidingWindowLimiter(limit=5, window_seconds=3600)
seen_messages = SeenMessageIds()


# ── Account linking ──────────────────────────────────────────────────────────

def mask_phone(phone: Optional[str]) -> Optional[str]:
    digits = _digits(phone or "")
    if len(digits) < 6:
        return None
    return f"+{digits[:2]} {'•' * max(0, len(digits) - 6)}{digits[-4:]}"


def create_link_code(db: Session, user: User) -> tuple[str, datetime]:
    """Create (or replace) the user's pending link code. Valid for 15 minutes."""
    link = db.query(WhatsAppLink).filter(WhatsAppLink.user_id == user.id).first()
    if link is None:
        link = WhatsAppLink(user_id=user.id)
        db.add(link)

    now = datetime.utcnow()
    code = ""
    for _ in range(20):
        candidate = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))
        clash = (
            db.query(WhatsAppLink)
            .filter(
                WhatsAppLink.link_code == candidate,
                WhatsAppLink.link_code_expires_at > now,
                WhatsAppLink.user_id != user.id,
            )
            .first()
        )
        if clash is None:
            code = candidate
            break
    if not code:  # pragma: no cover - 32^6 codes; practically unreachable
        raise RuntimeError("Could not allocate a unique link code")

    link.link_code = code
    link.link_code_expires_at = now + timedelta(minutes=LINK_CODE_TTL_MINUTES)
    db.commit()
    return code, link.link_code_expires_at


def link_phone_with_code(db: Session, phone: str, code: str) -> Optional[User]:
    """Bind ``phone`` to the account that issued ``code``. Returns the User, or None if invalid/expired."""
    code = (code or "").strip().upper()
    if not code:
        return None
    now = datetime.utcnow()
    link = (
        db.query(WhatsAppLink)
        .filter(WhatsAppLink.link_code == code, WhatsAppLink.link_code_expires_at > now)
        .first()
    )
    if link is None:
        return None

    # One number belongs to one account: moving it frees it from any previous account.
    previous = (
        db.query(WhatsAppLink)
        .filter(WhatsAppLink.phone_number == phone, WhatsAppLink.id != link.id)
        .first()
    )
    if previous is not None:
        previous.phone_number = None
        db.flush()

    link.phone_number = phone
    link.link_code = None
    link.link_code_expires_at = None
    link.linked_at = now
    db.commit()
    return db.get(User, link.user_id)


def get_user_by_phone(db: Session, phone: str) -> Optional[User]:
    link = db.query(WhatsAppLink).filter(WhatsAppLink.phone_number == phone).first()
    return db.get(User, link.user_id) if link else None


def unlink_user(db: Session, user_id: uuid.UUID) -> bool:
    link = db.query(WhatsAppLink).filter(WhatsAppLink.user_id == user_id).first()
    if link is None:
        return False
    db.delete(link)
    db.commit()
    return True


# ── Replies ──────────────────────────────────────────────────────────────────

_HELP_REPLY = (
    "👋 I'm Warranty Agent. Send me a bill and I'll track the warranty for you.\n\n"
    "• A photo or PDF of an invoice / warranty card\n"
    "• Or paste the order details as text\n\n"
    "Commands:\n"
    "LIST – what expires soonest\n"
    "UNLINK – disconnect this chat\n"
    "HELP – show this message"
)
_UNLINKED_REPLY = (
    "👋 Hi! I'm Warranty Agent, your warranty & refund assistant.\n\n"
    "To save bills from this chat, link it to your account:\n"
    "1. Open Warranty Agent → Upload → “Link WhatsApp”\n"
    "2. Send me the code it shows, like:  LINK ABC123"
)
_NOT_FOUND_REPLY = (
    "🤔 I couldn't find a product and store in that. Please send a clear photo or PDF of the "
    "invoice, or paste the order details (product, store, date, price)."
)
_UNSUPPORTED_REPLY = (
    "I can read text, photos (JPG/PNG/WEBP) and PDFs. Please send the bill in one of those formats."
)

_LINK_RE = re.compile(r"^\s*link\s+([A-Za-z0-9]{4,12})\s*$", re.I)
_HELP_WORDS = {"hi", "hello", "hey", "help", "menu", "start", "?"}
_LIST_WORDS = {"list", "status", "warranties", "my warranties", "expiring"}
_UNLINK_WORDS = {"unlink", "disconnect"}


def _fmt_date(d: date) -> str:
    return d.strftime("%d %b %Y")


def build_summary(db: Session, user: User, today: Optional[date] = None) -> str:
    today = today or date.today()
    purchases = db.query(Purchase).filter(Purchase.user_id == user.id).all()
    if not purchases:
        return "Your vault is empty. Send a bill photo, PDF or the order details to add your first item."

    dated: list[tuple[int, Purchase]] = []
    for p in purchases:
        wp = p.warranty_period
        if wp and wp.warranty_end_date:
            dated.append(((wp.warranty_end_date - today).days, p))

    upcoming = sorted((d for d in dated if d[0] >= 0), key=lambda d: d[0])[:5]
    expired = sum(1 for d in dated if d[0] < 0)

    lines = [f"📋 {len(purchases)} item(s) in your vault."]
    if upcoming:
        lines.append("\nExpiring soonest:")
        for days, p in upcoming:
            lines.append(f"• {p.product_name} — {days} day(s) left")
    else:
        lines.append("\nNo active warranties with a known end date.")
    if expired:
        lines.append(f"\n{expired} item(s) are out of warranty.")
    return "\n".join(lines)


def format_saved_reply(
    db: Session,
    purchase: Purchase,
    was_duplicate: bool,
    today: Optional[date] = None,
) -> str:
    today = today or date.today()
    wp = purchase.warranty_period
    lines = [
        "🔁 Already in your vault — details refreshed:" if was_duplicate else "✅ Saved to your vault:",
        f"📦 {purchase.product_name}",
    ]

    vendor = purchase.retailer or purchase.brand
    price = f"₹{float(purchase.price):,.0f}" if purchase.price is not None else None
    detail = " · ".join(part for part in (vendor, price) if part)
    if detail:
        lines.append(f"🏬 {detail}")

    if wp and wp.warranty_end_date:
        days = (wp.warranty_end_date - today).days
        suffix = " (estimated)" if wp.is_estimated else ""
        if days >= 0:
            lines.append(f"🛡️ Warranty until {_fmt_date(wp.warranty_end_date)} — {days} day(s) left{suffix}")
        else:
            lines.append(f"🛡️ Warranty ended {_fmt_date(wp.warranty_end_date)}{suffix}")
    if wp and wp.return_window_end_date:
        days = (wp.return_window_end_date - today).days
        lines.append(
            f"↩️ Return window closes in {days} day(s)" if days >= 0 else "↩️ Return window has closed"
        )

    card_line = _card_hint(db, purchase)
    if card_line:
        lines.append(card_line)

    lines.append("\nReply LIST to see what expires soonest.")
    return "\n".join(lines)


def _card_hint(db: Session, purchase: Purchase) -> Optional[str]:
    row = get_payment_method(db, purchase.id)
    if row is None:
        return None
    report = build_card_report(purchase, row)
    benefit = report.benefit
    if benefit.status == "extended_warranty" and benefit.extension_months and (
        benefit.days_until_extended_end is None or benefit.days_until_extended_end >= 0
    ):
        until = f" (until {benefit.extended_warranty_end})" if benefit.extended_warranty_end else ""
        return (
            f"💳 Your {benefit.card_label} card may add +{benefit.extension_months} months free"
            f"{until} — open the app for claim steps."
        )
    if benefit.status == "needs_card" and report.detected_card and report.detected_card.issuer_label:
        return (
            f"💳 Paid with a {report.detected_card.issuer_label} credit card — open the app and pick "
            "your card to check for free warranty perks."
        )
    return None


# ── Ingestion from chat ──────────────────────────────────────────────────────

def _save_extraction(
    db: Session, user: User, result: ExtractionResult, source_file_ref: Optional[str]
) -> str:
    duplicate = _find_existing_duplicate_purchase(db, user.id, result, source_file_ref)
    purchase = _persist_purchase(
        db,
        user_id=user.id,
        result=result,
        source_type="whatsapp",
        source_file_ref=source_file_ref,
    )
    return format_saved_reply(db, purchase, was_duplicate=duplicate is not None)


def _ingest_text(db: Session, user: User, text: str) -> str:
    result = _run_extraction_pipeline(text)
    if not _is_valid_extracted_purchase(result):
        return _NOT_FOUND_REPLY
    return _save_extraction(db, user, result, None)


def _ingest_media(db: Session, user: User, msg: IncomingMessage, client: MessagingClient) -> str:
    mime = (msg.mime_type or "").split(";")[0].strip().lower()
    if not msg.media_id or mime not in _ALLOWED_MEDIA:
        return _UNSUPPORTED_REPLY

    try:
        data, real_mime = client.download_media(msg.media_id)
    except WhatsAppError as exc:
        return f"⚠️ {exc}"

    filename = msg.filename or f"whatsapp_{msg.message_id[-8:]}{_ALLOWED_MEDIA[mime]}"
    try:
        ref, _name, result, _ocr = process_file_bytes(data, filename, real_mime or mime)
    except HTTPException as exc:
        return f"⚠️ {exc.detail}"

    if not _is_valid_extracted_purchase(result):
        return _NOT_FOUND_REPLY
    return _save_extraction(db, user, result, ref)


def _compute_reply(db: Session, msg: IncomingMessage, client: MessagingClient) -> str:
    if not message_limiter.allow(msg.from_number):
        return "⏳ You're sending messages very quickly. Please wait a little and try again."

    text = (msg.text or "").strip() if msg.type == "text" else ""

    link_match = _LINK_RE.match(text) if text else None
    if link_match:
        if not link_attempt_limiter.allow(msg.from_number):
            return "Too many link attempts. Please wait an hour or generate a new code in the app."
        user = link_phone_with_code(db, msg.from_number, link_match.group(1))
        if user is None:
            return "That code is invalid or has expired. Generate a new one in Warranty Agent → Upload → “Link WhatsApp”."
        return (
            f"✅ Linked to {user.email}!\n\n"
            "Now forward me any bill — a photo, a PDF, or the order details as text — and I'll "
            "track its warranty."
        )

    user = get_user_by_phone(db, msg.from_number)
    if user is None:
        return _UNLINKED_REPLY

    lowered = text.lower()
    if lowered in _HELP_WORDS:
        return _HELP_REPLY
    if lowered in _LIST_WORDS:
        return build_summary(db, user)
    if lowered in _UNLINK_WORDS:
        unlink_user(db, user.id)
        return "🔌 This chat is disconnected. Link it again any time from the app."

    if msg.type in ("image", "document"):
        return _ingest_media(db, user, msg, client)
    if msg.type == "text":
        if len(text) < _MIN_TEXT_LEN_FOR_BILL:
            return _HELP_REPLY
        return _ingest_text(db, user, text)
    return _UNSUPPORTED_REPLY


def process_incoming(db: Session, msg: IncomingMessage, client: MessagingClient) -> str:
    """Handle one incoming WhatsApp message end to end and send the reply. Returns the reply text."""
    try:
        reply = _compute_reply(db, msg, client)
    except Exception:  # noqa: BLE001 - the user should always get an answer
        db.rollback()
        logger.exception("WhatsApp message %s failed", msg.message_id)
        reply = "Sorry, something went wrong while reading that. Please try again in a moment."

    try:
        client.send_text(msg.from_number, reply)
    except Exception:  # noqa: BLE001
        logger.exception("Could not send WhatsApp reply to ...%s", msg.from_number[-4:])
    return reply

