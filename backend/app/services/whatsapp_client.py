"""
Thin client for the WhatsApp Business Cloud API (Meta Graph API).

Only what the Warranty Agent bot needs:
  - verify the X-Hub-Signature-256 header on incoming webhooks;
  - download a media file (a forwarded bill photo / PDF) by media id;
  - send a plain text reply.

Configuration comes from environment variables (read at call time, so tests and
deployments can change them without re-importing):

  WHATSAPP_ACCESS_TOKEN     permanent / system-user access token
  WHATSAPP_PHONE_NUMBER_ID  id of the business phone number that receives bills
  WHATSAPP_APP_SECRET       Meta app secret, used to verify webhook signatures
  WHATSAPP_VERIFY_TOKEN     any string you also enter in Meta's webhook setup
  WHATSAPP_BOT_NUMBER       the bot's number as digits (e.g. 919876543210),
                            shown to users for the wa.me deep link
  WHATSAPP_GRAPH_VERSION    optional, defaults to v21.0
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

MAX_MEDIA_BYTES = 20 * 1024 * 1024  # same hard limit as web uploads
_TIMEOUT = httpx.Timeout(20.0, connect=10.0)
_MAX_TEXT_LEN = 4000  # WhatsApp text bodies are limited to 4096 characters
_TWILIO_MAX_TEXT_LEN = 1600  # Twilio WhatsApp single message limit
_DEFAULT_TWILIO_SANDBOX_NUMBER = "14155238886"
_TWILIO_MEDIA_PREFIX = "https://api.twilio.com/"


class WhatsAppError(RuntimeError):
    """Raised when the Graph API or Twilio call fails or returns something unusable."""


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def is_meta_configured() -> bool:
    """True when Meta WhatsApp Cloud API credentials are set."""
    return bool(
        _env("WHATSAPP_ACCESS_TOKEN")
        and _env("WHATSAPP_PHONE_NUMBER_ID")
        and _env("WHATSAPP_APP_SECRET")
        and _env("WHATSAPP_VERIFY_TOKEN")
    )


def is_twilio_configured() -> bool:
    """True when Twilio Account SID and Auth Token are set."""
    return bool(_env("TWILIO_ACCOUNT_SID") and _env("TWILIO_AUTH_TOKEN"))


def active_provider() -> Optional[str]:
    """Return 'meta' or 'twilio' when configured (honours optional WHATSAPP_PROVIDER)."""
    pref = _env("WHATSAPP_PROVIDER").lower()
    if pref == "twilio" and is_twilio_configured():
        return "twilio"
    if pref == "meta" and is_meta_configured():
        return "meta"
    if is_meta_configured():
        return "meta"
    if is_twilio_configured():
        return "twilio"
    return None


def is_configured() -> bool:
    """True when either Meta Cloud API or Twilio WhatsApp is ready."""
    return active_provider() is not None


def bot_number() -> Optional[str]:
    if active_provider() == "twilio":
        raw = _env("TWILIO_WHATSAPP_NUMBER") or _DEFAULT_TWILIO_SANDBOX_NUMBER
    else:
        raw = _env("WHATSAPP_BOT_NUMBER")
    digits = "".join(ch for ch in raw if ch.isdigit())
    return digits or None


def twilio_join_code() -> Optional[str]:
    """Sandbox join phrase (e.g. 'join quick-tiger'), if configured."""
    return _env("TWILIO_SANDBOX_JOIN_CODE") or None


def verify_signature(raw_body: bytes, header: Optional[str], app_secret: str) -> bool:
    """
    Validate Meta's ``X-Hub-Signature-256: sha256=<hex>`` header.

    Uses a constant-time comparison. Anything malformed or missing is rejected.
    """
    if not header or not app_secret or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header[len("sha256="):].strip())


def verify_twilio_signature(
    url: str,
    params: dict[str, str] | list[tuple[str, str]],
    header: Optional[str],
    auth_token: str,
) -> bool:
    """
    Validate Twilio's base64 HMAC-SHA1 ``X-Twilio-Signature`` header.

    Twilio signs the full webhook URL concatenated with sorted POST parameter
    key-value pairs using the account's Auth Token.
    """
    if not url or not header or not auth_token:
        return False
    items = list(params.items()) if isinstance(params, dict) else list(params)
    payload = url + "".join(f"{k}{v}" for k, v in sorted(items, key=lambda kv: kv[0]))
    digest = hmac.new(auth_token.encode("utf-8"), payload.encode("utf-8"), hashlib.sha1).digest()
    expected = base64.b64encode(digest).decode("ascii")
    return hmac.compare_digest(expected, header.strip())


class WhatsAppClient:
    """Sends replies and downloads media through the Meta Graph API."""

    def __init__(
        self,
        access_token: str,
        phone_number_id: str,
        graph_version: str = "v21.0",
        http: Optional[httpx.Client] = None,
    ) -> None:
        self._token = access_token
        self._phone_number_id = phone_number_id
        self._base = f"https://graph.facebook.com/{graph_version}"
        self._http = http or httpx.Client(timeout=_TIMEOUT)

    @classmethod
    def from_env(cls) -> "WhatsAppClient":
        if not is_meta_configured():
            raise WhatsAppError("Meta WhatsApp is not configured (missing WHATSAPP_* variables).")
        return cls(
            access_token=_env("WHATSAPP_ACCESS_TOKEN"),
            phone_number_id=_env("WHATSAPP_PHONE_NUMBER_ID"),
            graph_version=_env("WHATSAPP_GRAPH_VERSION") or "v21.0",
        )

    @property
    def _auth(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    def download_media(self, media_id: str) -> tuple[bytes, str]:
        """Return (file_bytes, mime_type) for a media id from an incoming message."""
        try:
            meta = self._http.get(f"{self._base}/{media_id}", headers=self._auth)
            meta.raise_for_status()
            info = meta.json()
            url = info.get("url")
            if not url:
                raise WhatsAppError("Media metadata had no download URL.")
            size = int(info.get("file_size") or 0)
            if size > MAX_MEDIA_BYTES:
                raise WhatsAppError("That file is larger than the 20 MB limit.")

            blob = self._http.get(url, headers=self._auth)
            blob.raise_for_status()
        except httpx.HTTPError as exc:
            raise WhatsAppError(f"Could not download the file from WhatsApp: {exc}") from exc

        content = blob.content
        if len(content) > MAX_MEDIA_BYTES:
            raise WhatsAppError("That file is larger than the 20 MB limit.")
        return content, info.get("mime_type") or blob.headers.get("content-type", "")

    def send_text(self, to: str, body: str) -> None:
        """Send a plain text message to a WhatsApp number (digits only)."""
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body[:_MAX_TEXT_LEN], "preview_url": False},
        }
        try:
            resp = self._http.post(
                f"{self._base}/{self._phone_number_id}/messages",
                headers=self._auth,
                json=payload,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise WhatsAppError(f"Could not send the WhatsApp reply: {exc}") from exc


class TwilioWhatsAppClient:
    """Sends replies and downloads media through Twilio's REST API (Sandbox & Production)."""

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        http: Optional[httpx.Client] = None,
    ) -> None:
        self._sid = account_sid
        self._token = auth_token
        self._from = "".join(ch for ch in (from_number or "") if ch.isdigit())
        self._http = http or httpx.Client(timeout=_TIMEOUT)

    @classmethod
    def from_env(cls) -> "TwilioWhatsAppClient":
        if not is_twilio_configured():
            raise WhatsAppError("Twilio WhatsApp is not configured (missing TWILIO_* variables).")
        from_num = _env("TWILIO_WHATSAPP_NUMBER") or _DEFAULT_TWILIO_SANDBOX_NUMBER
        return cls(
            account_sid=_env("TWILIO_ACCOUNT_SID"),
            auth_token=_env("TWILIO_AUTH_TOKEN"),
            from_number=from_num,
        )

    def download_media(self, media_url: str) -> tuple[bytes, str]:
        """Download a Twilio-hosted bill photo / PDF using Basic Auth."""
        if not (media_url or "").startswith(_TWILIO_MEDIA_PREFIX):
            raise WhatsAppError("Untrusted media URL from webhook payload.")
        try:
            resp = self._http.get(
                media_url,
                auth=(self._sid, self._token),
                follow_redirects=True,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise WhatsAppError(f"Could not download the file from Twilio: {exc}") from exc

        content = resp.content
        if len(content) > MAX_MEDIA_BYTES:
            raise WhatsAppError("That file is larger than the 20 MB limit.")
        content_type = (resp.headers.get("content-type") or "").split(";")[0].strip()
        return content, content_type

    def send_text(self, to: str, body: str) -> None:
        """Send a WhatsApp message via Twilio's Messages API."""
        to_digits = "".join(ch for ch in (to or "") if ch.isdigit())
        truncated = (body[:1580] + "…") if len(body) > 1590 else body[:_TWILIO_MAX_TEXT_LEN]
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self._sid}/Messages.json"
        try:
            resp = self._http.post(
                url,
                auth=(self._sid, self._token),
                data={
                    "From": f"whatsapp:+{self._from}",
                    "To": f"whatsapp:+{to_digits}",
                    "Body": truncated,
                },
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise WhatsAppError(f"Could not send the WhatsApp reply via Twilio: {exc}") from exc


def get_active_client() -> WhatsAppClient | TwilioWhatsAppClient:
    """Return an initialized WhatsApp client matching the active provider."""
    if active_provider() == "twilio":
        return TwilioWhatsAppClient.from_env()
    return WhatsAppClient.from_env()

