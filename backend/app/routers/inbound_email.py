"""
Forward-to-email endpoints (mounted under /ingestion).

POST /ingestion/inbound-email                     called by the Cloudflare Email Worker
GET  /ingestion/forwarding-address?user_id=       the user's private bills+<token>@domain address
POST /ingestion/forwarding-address/rotate?user_id= replace the token (old address stops working)
"""

from __future__ import annotations

import hmac
import logging
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import ForwardingAddressOut, InboundEmailPayload, InboundEmailResponse
from app.services import inbound_email as svc

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return user


def _address_response(db: Session, user: User, create: bool) -> ForwardingAddressOut:
    if not svc.is_enabled():
        return ForwardingAddressOut(enabled=False)
    inbox = svc.get_or_create_inbox(db, user) if create else None
    if inbox is None:
        return ForwardingAddressOut(enabled=True, domain=svc.inbound_domain())
    return ForwardingAddressOut(
        enabled=True,
        address=svc.build_address(inbox.inbox_token),
        domain=svc.inbound_domain(),
        verification_code=svc.active_verification_code(inbox),
    )


@router.post(
    "/inbound-email",
    response_model=InboundEmailResponse,
    summary="Receive a forwarded email from the Cloudflare Email Worker",
    include_in_schema=False,
)
def receive_inbound_email(
    body: InboundEmailPayload,
    x_inbound_email_secret: str | None = Header(None),
    db: Session = Depends(get_db),
) -> InboundEmailResponse:
    secret = svc.inbound_secret()
    if not secret or not svc.inbound_domain():
        raise HTTPException(status_code=503, detail="Forward-to-email is not configured")
    if not x_inbound_email_secret or not hmac.compare_digest(x_inbound_email_secret, secret):
        raise HTTPException(status_code=403, detail="Invalid secret")

    token = svc.extract_token_from_address(body.to)
    user = svc.find_user_by_token(db, token) if token else None
    if user is None:
        # Never reveal whether an address exists; 200 stops the worker from retrying.
        return InboundEmailResponse(status="ignored")

    if not svc.inbound_limiter.allow(str(user.id)):
        raise HTTPException(status_code=429, detail="Too many forwarded emails; try again later")

    attachments = svc.decode_attachments(
        [(a.filename, a.content_type, a.content_base64) for a in body.attachments]
    )
    result = svc.process_inbound_email(
        db,
        user,
        sender=body.sender,
        subject=body.subject,
        text=body.text,
        html=body.html,
        message_id=body.message_id,
        attachments=attachments,
    )
    if result.purchase is not None:
        svc.notify_whatsapp(db, user.id, result)
    return InboundEmailResponse(
        status=result.status,
        product_name=result.purchase.product_name if result.purchase else None,
    )


@router.get(
    "/forwarding-address",
    response_model=ForwardingAddressOut,
    summary="Get (or create) the user's private forwarding address",
)
def get_forwarding_address(
    user_id: uuid.UUID = Query(..., description="UUID of the user"),
    db: Session = Depends(get_db),
) -> ForwardingAddressOut:
    user = _get_user_or_404(db, user_id)
    return _address_response(db, user, create=True)


@router.post(
    "/forwarding-address/rotate",
    response_model=ForwardingAddressOut,
    summary="Replace the forwarding address; the old one stops working immediately",
)
def rotate_forwarding_address(
    user_id: uuid.UUID = Query(..., description="UUID of the user"),
    db: Session = Depends(get_db),
) -> ForwardingAddressOut:
    user = _get_user_or_404(db, user_id)
    if not svc.is_enabled():
        raise HTTPException(status_code=503, detail="Forward-to-email is not enabled on this server yet.")
    svc.rotate_inbox(db, user)
    return _address_response(db, user, create=True)

