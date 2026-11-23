"""
WhatsApp bot endpoints.

GET    /whatsapp/webhook              Meta webhook verification handshake
POST   /whatsapp/webhook              incoming messages (signature-verified)
GET    /whatsapp/status?user_id=      is the bot enabled / is this workspace linked?
POST   /whatsapp/link-code?user_id=   issue the code the user sends as "LINK <code>"
DELETE /whatsapp/link?user_id=        disconnect the linked number

The webhook answers Meta immediately and does the slow work (media download,
OCR / Gemini extraction, reply) in a background task, because Meta retries
deliveries that take more than a few seconds.
"""

from __future__ import annotations

import hmac
import json
import logging
import os
import uuid
from datetime import datetime
from urllib.parse import parse_qsl, quote

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models import User, WhatsAppLink
from app.schemas import WhatsAppLinkCodeOut, WhatsAppStatusOut
from app.services.whatsapp_bot import (
    LINK_CODE_TTL_MINUTES,
    IncomingMessage,
    create_link_code,
    mask_phone,
    parse_twilio_payload,
    parse_webhook_payload,
    process_incoming,
    seen_messages,
    unlink_user,
)
from app.services.whatsapp_client import (
    TwilioWhatsAppClient,
    WhatsAppClient,
    active_provider,
    bot_number,
    is_configured,
    is_meta_configured,
    is_twilio_configured,
    twilio_join_code,
    verify_signature,
    verify_twilio_signature,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return user


# ── Meta webhook ─────────────────────────────────────────────────────────────

@router.get("/webhook", summary="WhatsApp webhook verification handshake", include_in_schema=False)
def verify_webhook(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
) -> PlainTextResponse:
    expected = os.getenv("WHATSAPP_VERIFY_TOKEN", "").strip()
    if (
        hub_mode == "subscribe"
        and expected
        and hmac.compare_digest(hub_verify_token or "", expected)
    ):
        return PlainTextResponse(hub_challenge or "")
    raise HTTPException(status_code=403, detail="Webhook verification failed")


def _handle_in_background(msg: IncomingMessage) -> None:
    """Runs after the HTTP response: own DB session, own client."""
    db = SessionLocal()
    try:
        process_incoming(db, msg, WhatsAppClient.from_env())
    except Exception:  # noqa: BLE001
        logger.exception("Background handling of WhatsApp message %s failed", msg.message_id)
    finally:
        db.close()


@router.post("/webhook", summary="Receive WhatsApp messages", include_in_schema=False)
async def receive_webhook(request: Request, background_tasks: BackgroundTasks) -> dict:
    app_secret = os.getenv("WHATSAPP_APP_SECRET", "").strip()
    if not app_secret or not is_meta_configured():
        raise HTTPException(status_code=503, detail="Meta WhatsApp bot is not configured")

    raw_body = await request.body()
    if not verify_signature(raw_body, request.headers.get("X-Hub-Signature-256"), app_secret):
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        payload = json.loads(raw_body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Body is not valid JSON") from exc

    for msg in parse_webhook_payload(payload):
        if seen_messages.seen_before(msg.message_id):
            continue
        background_tasks.add_task(_handle_in_background, msg)
    return {"status": "received"}


# ── Twilio WhatsApp webhook (Sandbox & Production, no Facebook needed) ───────

def _twilio_candidate_urls(request: Request) -> list[str]:
    """Build URL candidates matching what Twilio signed behind Render/Railway proxies."""
    candidates: list[str] = []
    explicit = os.getenv("TWILIO_WEBHOOK_URL", "").strip()
    if explicit:
        candidates.append(explicit)

    req_url = getattr(request, "url", None)
    path = getattr(req_url, "path", None) or "/whatsapp/twilio-webhook"
    query = getattr(req_url, "query", None) or ""
    suffix = f"{path}?{query}" if query else path

    proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip()
    host = (
        request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
    ).split(",")[0].strip()
    if host:
        candidates.append(f"{proto or 'https'}://{host}{suffix}")
        if not proto:
            candidates.append(f"http://{host}{suffix}")
    if req_url is not None:
        candidates.append(str(req_url))
    return list(dict.fromkeys(candidates))


def _handle_twilio_in_background(msg: IncomingMessage) -> None:
    """Runs after the HTTP response: own DB session, own Twilio client."""
    db = SessionLocal()
    try:
        process_incoming(db, msg, TwilioWhatsAppClient.from_env())
    except Exception:  # noqa: BLE001
        logger.exception("Background handling of Twilio message %s failed", msg.message_id)
    finally:
        db.close()


@router.post(
    "/twilio-webhook",
    summary="Receive WhatsApp messages from Twilio",
    include_in_schema=False,
)
async def receive_twilio_webhook(request: Request, background_tasks: BackgroundTasks) -> Response:
    if not is_twilio_configured():
        raise HTTPException(status_code=503, detail="Twilio WhatsApp bot is not configured")

    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    raw_body = await request.body()
    try:
        decoded = raw_body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Body must be UTF-8 form data") from exc

    pairs = parse_qsl(decoded, keep_blank_values=True)
    params = dict(pairs)
    signature = request.headers.get("X-Twilio-Signature")
    if not any(verify_twilio_signature(url, params, signature, auth_token) for url in _twilio_candidate_urls(request)):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    msg = parse_twilio_payload(params)
    if msg and not seen_messages.seen_before(msg.message_id):
        background_tasks.add_task(_handle_twilio_in_background, msg)
    return Response(content="<Response/>", media_type="application/xml", status_code=200)


# ── Workspace linking (called by the web app) ────────────────────────────────

def _sandbox_join_info(
    provider: str | None, number: str | None
) -> tuple[str | None, str | None]:
    if provider != "twilio":
        return None, None
    join_code = twilio_join_code()
    if not join_code:
        return None, None
    join_link = f"https://wa.me/{number}?text={quote(join_code)}" if number else None
    return join_code, join_link


@router.get("/status", response_model=WhatsAppStatusOut, summary="WhatsApp link status for a workspace")
def whatsapp_status(
    user_id: uuid.UUID = Query(..., description="UUID of the user"),
    db: Session = Depends(get_db),
) -> WhatsAppStatusOut:
    _get_user_or_404(db, user_id)
    link = db.query(WhatsAppLink).filter(WhatsAppLink.user_id == user_id).first()
    pending = bool(
        link
        and link.link_code
        and link.link_code_expires_at
        and link.link_code_expires_at > datetime.utcnow()
    )
    provider = active_provider()
    number = bot_number()
    join_code, join_link = _sandbox_join_info(provider, number)
    return WhatsAppStatusOut(
        configured=is_configured(),
        linked=bool(link and link.phone_number),
        phone_masked=mask_phone(link.phone_number) if link else None,
        bot_number=number,
        pending_code=pending,
        provider=provider,
        sandbox_join_code=join_code,
        sandbox_join_link=join_link,
    )


@router.post("/link-code", response_model=WhatsAppLinkCodeOut, summary="Create a code to link WhatsApp")
def new_link_code(
    user_id: uuid.UUID = Query(..., description="UUID of the user"),
    db: Session = Depends(get_db),
) -> WhatsAppLinkCodeOut:
    if not is_configured():
        raise HTTPException(
            status_code=503, detail="The WhatsApp bot is not enabled on this server yet."
        )
    user = _get_user_or_404(db, user_id)
    code, _expires = create_link_code(db, user)
    provider = active_provider()
    number = bot_number()
    join_code, join_link = _sandbox_join_info(provider, number)
    deep_link = f"https://wa.me/{number}?text={quote(f'LINK {code}')}" if number else None
    return WhatsAppLinkCodeOut(
        code=code,
        expires_in_minutes=LINK_CODE_TTL_MINUTES,
        bot_number=number,
        deep_link=deep_link,
        provider=provider,
        sandbox_join_code=join_code,
        sandbox_join_link=join_link,
    )


@router.delete("/link", status_code=204, response_class=Response, summary="Disconnect WhatsApp")
def delete_link(
    user_id: uuid.UUID = Query(..., description="UUID of the user"),
    db: Session = Depends(get_db),
) -> Response:
    _get_user_or_404(db, user_id)
    unlink_user(db, user_id)
    return Response(status_code=204)

