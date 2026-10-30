"""
Gmail API client — search and fetch order-confirmation and warranty emails.

Design principles:
- Never stores raw email bodies in the database. Bodies and attachments are used
  transiently during extraction and then discarded.
- All API calls are wrapped in try/except with logging; failures are surfaced
  as return values, not exceptions, so the caller can decide how to handle them.
- gmail_message_id (the short ID from the API) is stored in purchases.source_email_id.
"""

import base64
import logging
from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Matches:
# 1. Order / invoice / shipped / warranty emails from major Indian retailers
# 2. Direct or forwarded purchase confirmations, warranty cards, and tax invoices
GMAIL_SEARCH_QUERY = (
    "("
    "from:("
    "amazon.in OR flipkart.com OR myntra.com OR nykaa.com OR meesho.com "
    "OR ajio.com OR jiomart.com OR blinkit.com OR zeptonow.com OR swiggy.com "
    "OR croma.com OR reliancedigital.in"
    ") "
    "subject:(order OR invoice OR shipped OR confirmed OR confirmation OR delivered OR warranty OR receipt)"
    ") OR ("
    "subject:(\"purchase confirmation\" OR \"order confirmation\" OR \"warranty card\" "
    "OR \"warranty registration\" OR \"tax invoice\" OR \"order receipt\" "
    "OR \"invoice for your order\" OR \"warranty details\" OR \"warranty claim\") "
    "-from:(internshala.com OR unstop.news OR linkedin.com OR vercel.com OR medium.com OR substack.com OR google.com)"
    ")"
)

_ALLOWED_ATTACHMENT_MIMES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/tiff",
}


def build_gmail_service(credentials: Credentials):
    """
    Build and return an authenticated Gmail API service object.
    """
    try:
        service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        return service
    except Exception as exc:
        logger.error("Failed to build Gmail service: %s", exc)
        raise RuntimeError(f"Could not build Gmail service: {exc}") from exc


def search_order_emails(service, max_results: int = 50) -> list[dict]:
    """
    Search the user's Gmail inbox for order-confirmation and warranty emails.
    """
    try:
        response = (
            service.users()
            .messages()
            .list(userId="me", q=GMAIL_SEARCH_QUERY, maxResults=max_results)
            .execute()
        )
        messages = response.get("messages", [])
        logger.info("Gmail search returned %d message stubs", len(messages))
        return messages
    except HttpError as exc:
        logger.error("Gmail API search failed (HTTP %s): %s", exc.status_code, exc)
        return []
    except Exception as exc:
        logger.error("Unexpected error during Gmail search: %s", exc)
        return []


def fetch_message_body(service, message_id: str) -> Optional[str]:
    """
    Fetch the plain-text (or HTML fallback) body of a Gmail message, prefixed
    with the Subject header if available so subject-line product names are
    visible to the extractor.

    The raw body is returned as a plain string — it is NOT persisted anywhere.
    Only the message_id is stored long-term.
    """
    try:
        message = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        payload = message.get("payload", {})
        body_text = _extract_body_from_payload(payload) or ""
        return body_text.strip() or None
    except HttpError as exc:
        logger.error(
            "Failed to fetch Gmail message %s (HTTP %s): %s", message_id, exc.status_code, exc
        )
        return None
    except Exception as exc:
        logger.error("Unexpected error fetching Gmail message %s: %s", message_id, exc)
        return None


def fetch_message_attachments(service, message_id: str) -> list[tuple[str, str, bytes]]:
    """
    Fetch any supported PDF or image attachments from a Gmail message.

    Returns:
        List of tuples: [(filename, mime_type, raw_bytes), ...]
    """
    try:
        message = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        payload = message.get("payload", {})
        attachment_specs: list[tuple[str, str, str]] = []
        _collect_attachment_specs(payload, attachment_specs)

        results: list[tuple[str, str, bytes]] = []
        for filename, mime_type, att_id in attachment_specs:
            try:
                att = (
                    service.users()
                    .messages()
                    .attachments()
                    .get(userId="me", messageId=message_id, id=att_id)
                    .execute()
                )
                data_b64 = att.get("data", "")
                if data_b64:
                    raw_bytes = base64.urlsafe_b64decode(data_b64 + "==")
                    results.append((filename, mime_type, raw_bytes))
            except Exception as exc:
                logger.warning(
                    "Failed to download attachment %r from message %s: %s",
                    filename,
                    message_id,
                    exc,
                )
        return results
    except Exception as exc:
        logger.warning("Could not inspect attachments for message %s: %s", message_id, exc)
        return []


def _collect_attachment_specs(
    payload: dict, out: list[tuple[str, str, str]]
) -> None:
    """Recursively find MIME parts that have an attachmentId and supported MIME type."""
    mime_type = (payload.get("mimeType") or "").lower()
    filename = payload.get("filename") or ""
    body = payload.get("body") or {}
    att_id = body.get("attachmentId")

    is_supported = (
        mime_type in _ALLOWED_ATTACHMENT_MIMES
        or filename.lower().endswith((".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tiff"))
    )
    if att_id and is_supported:
        out.append((filename or "attachment", mime_type, att_id))

    for part in payload.get("parts", []):
        _collect_attachment_specs(part, out)


def _extract_body_from_payload(payload: dict) -> Optional[str]:
    """
    Recursively walk the MIME payload tree and return the best text content.

    Priority: text/plain > text/html
    """
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")
    parts = payload.get("parts", [])

    if mime_type == "text/plain" and body_data:
        return _decode_base64(body_data)

    if mime_type == "text/html" and body_data and not parts:
        return _decode_base64(body_data)

    plain_result: Optional[str] = None
    html_result: Optional[str] = None

    for part in parts:
        part_mime = part.get("mimeType", "")
        part_data = part.get("body", {}).get("data")
        if part_mime == "text/plain" and part_data:
            decoded = _decode_base64(part_data)
            if decoded.strip():
                plain_result = decoded
        elif part_mime == "text/html" and part_data:
            decoded = _decode_base64(part_data)
            if decoded.strip():
                html_result = decoded
        elif part.get("parts"):
            nested = _extract_body_from_payload(part)
            if nested and nested.strip():
                plain_result = plain_result or nested

    return plain_result or html_result


def _decode_base64(data: str) -> str:
    """Decode URL-safe base64 Gmail body data to a UTF-8 string."""
    try:
        decoded_bytes = base64.urlsafe_b64decode(data + "==")
        return decoded_bytes.decode("utf-8", errors="replace")
    except Exception as exc:
        logger.warning("Base64 decode failed: %s", exc)
        return ""
