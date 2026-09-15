"""
Gmail API client — search and fetch order-confirmation emails.

Design principles:
- Never stores raw email bodies in the database. Bodies are used transiently
  during extraction and then discarded.
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

# Narrowed query — matches order/invoice/shipped emails from major Indian retailers
# Updated to include quick-commerce and fashion platforms (Enhancement 1)
GMAIL_SEARCH_QUERY = (
    "from:("
    "amazon.in OR flipkart.com OR myntra.com OR nykaa.com OR meesho.com "
    "OR ajio.com OR jiomart.com OR blinkit.com OR zeptonow.com OR swiggy.com"
    ") "
    "subject:(order OR invoice OR shipped OR confirmed OR confirmation OR delivered)"
)


def build_gmail_service(credentials: Credentials):
    """
    Build and return an authenticated Gmail API service object.

    Args:
        credentials: google.oauth2.credentials.Credentials with a valid access token.

    Returns:
        googleapiclient Resource object for Gmail v1.

    Raises:
        RuntimeError: If the service cannot be built.
    """
    try:
        service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        return service
    except Exception as exc:
        logger.error("Failed to build Gmail service: %s", exc)
        raise RuntimeError(f"Could not build Gmail service: {exc}") from exc


def search_order_emails(service, max_results: int = 50) -> list[dict]:
    """
    Search the user's Gmail inbox for order-confirmation emails.

    Args:
        service: Authenticated Gmail API service (from build_gmail_service).
        max_results: Maximum number of message stubs to return (default 50).

    Returns:
        List of message stubs: [{"id": "<gmail_message_id>", "threadId": "..."}, ...]
        Returns empty list on error.
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
    Fetch the plain-text (or HTML fallback) body of a Gmail message.

    The raw body is returned as a plain string — it is NOT persisted anywhere.
    Only the message_id is stored long-term.

    Args:
        service: Authenticated Gmail API service.
        message_id: Gmail message ID (short form).

    Returns:
        Decoded email body as a string, or None on failure.
    """
    try:
        message = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        return _extract_body_from_payload(message.get("payload", {}))
    except HttpError as exc:
        logger.error(
            "Failed to fetch Gmail message %s (HTTP %s): %s", message_id, exc.status_code, exc
        )
        return None
    except Exception as exc:
        logger.error("Unexpected error fetching Gmail message %s: %s", message_id, exc)
        return None


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
        # HTML fallback — return as-is; extractor can handle basic HTML
        return _decode_base64(body_data)

    # Multipart — search parts recursively, prefer plain text
    plain_result: Optional[str] = None
    html_result: Optional[str] = None

    for part in parts:
        part_mime = part.get("mimeType", "")
        part_data = part.get("body", {}).get("data")
        if part_mime == "text/plain" and part_data:
            plain_result = _decode_base64(part_data)
        elif part_mime == "text/html" and part_data:
            html_result = _decode_base64(part_data)
        elif part.get("parts"):
            # Nested multipart
            nested = _extract_body_from_payload(part)
            if nested:
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
