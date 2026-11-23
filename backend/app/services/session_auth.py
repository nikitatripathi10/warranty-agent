"""
Signed HS256 JWT session tokens (pure stdlib — no extra dependencies).

Why:
  Previously, endpoints accepted ``user_id=<uuid>`` without checking who sent
  the request. Now, Google sign-in (/auth/gmail/callback and /auth/google/login)
  and direct workspace creation (/auth/gmail/email-connect) mint a signed 30-day
  JWT. Every protected API call must present it as ``Authorization: Bearer <jwt>``
  or in the ``wa_session`` cookie.

Configuration:
  SESSION_SECRET      dedicated HMAC key (recommended). Falls back to FERNET_KEY
                      if unset so existing deployments work seamlessly.
  REQUIRE_AUTH_TOKEN  'true' (default) to enforce Bearer/cookie auth on API
                      routes; set 'false' temporarily during migration if needed.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
import uuid
from typing import Optional

from fastapi import Request, Response

logger = logging.getLogger(__name__)

SESSION_COOKIE_NAME = "wa_session"
DEFAULT_TTL_SECONDS = 30 * 24 * 3600  # 30 days

_EPHEMERAL_FALLBACK = secrets.token_urlsafe(32)
_WARNED_NO_SECRET = False

# Routes / prefixes that remain reachable without a session token.
_PUBLIC_EXACT = {
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/auth/gmail/connect",
    "/auth/gmail/callback",
    "/auth/gmail/email-connect",
    "/auth/google/login",
    "/whatsapp/webhook",
    "/whatsapp/twilio-webhook",
    "/ingestion/inbound-email",
    "/alerts/recalls",
    "/alerts/cron/run-daily",
    "/extraction/test",
}
_PROTECTED_PREFIXES = (
    "/purchases",
    "/alerts",
    "/agent",
    "/ingestion",
    "/whatsapp",
    "/auth/gmail/account",
)


def _signing_secret() -> bytes:
    global _WARNED_NO_SECRET
    raw = os.getenv("SESSION_SECRET", "").strip() or os.getenv("FERNET_KEY", "").strip()
    if raw:
        return hashlib.sha256(("wa-session:" + raw).encode("utf-8")).digest()
    if not _WARNED_NO_SECRET:
        logger.warning(
            "SESSION_SECRET / FERNET_KEY not set — using an ephemeral signing key "
            "(sessions reset on restart)."
        )
        _WARNED_NO_SECRET = True
    return _EPHEMERAL_FALLBACK.encode("utf-8")


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def create_session_token(
    user_id: uuid.UUID,
    email: str,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    now: Optional[int] = None,
) -> str:
    """Mint a compact HS256 JWT bound to ``user_id`` and ``email``."""
    issued_at = int(time.time()) if now is None else int(now)
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode("utf-8"))
    payload = _b64url_encode(
        json.dumps(
            {
                "sub": str(user_id),
                "email": email,
                "iat": issued_at,
                "exp": issued_at + ttl_seconds,
            },
            separators=(",", ":"),
        ).encode("utf-8")
    )
    signing_input = f"{header}.{payload}".encode("ascii")
    sig = _b64url_encode(hmac.new(_signing_secret(), signing_input, hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"


def verify_session_token(token: Optional[str], now: Optional[int] = None) -> Optional[dict]:
    """Validate signature, algorithm and expiry; return payload dict or None."""
    if not token or not isinstance(token, str):
        return None
    parts = token.strip().split(".")
    if len(parts) != 3:
        return None
    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = _b64url_encode(
        hmac.new(_signing_secret(), signing_input, hashlib.sha256).digest()
    )
    if not hmac.compare_digest(expected_sig, sig_b64):
        return None

    try:
        header = json.loads(_b64url_decode(header_b64).decode("utf-8"))
        if header.get("alg") != "HS256":
            return None
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        uuid.UUID(str(payload.get("sub", "")))
        exp = int(payload.get("exp", 0))
    except Exception:
        return None

    current = int(time.time()) if now is None else int(now)
    if exp <= current:
        return None
    return payload


def extract_token_from_request(request: Request) -> Optional[str]:
    """Read Bearer token from Authorization header, falling back to HttpOnly cookie."""
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        tok = auth[7:].strip()
        if tok:
            return tok
    cookies = getattr(request, "cookies", None) or {}
    cookie_tok = cookies.get(SESSION_COOKIE_NAME)
    return cookie_tok.strip() if isinstance(cookie_tok, str) and cookie_tok.strip() else None


def is_auth_enforced() -> bool:
    val = os.getenv("REQUIRE_AUTH_TOKEN", "true").strip().lower()
    return val not in {"0", "false", "no", "off"}


def set_session_cookie(response: Response, token: str, secure: bool = True) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=DEFAULT_TTL_SECONDS,
        httponly=True,
        secure=secure,
        samesite="none" if secure else "lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")


def is_protected_api_path(path: str, method: str) -> bool:
    if (method or "").upper() == "OPTIONS":
        return False
    clean = path.rstrip("/") or "/"
    if clean in _PUBLIC_EXACT or clean.startswith("/health"):
        return False
    return any(clean == prefix or clean.startswith(prefix + "/") for prefix in _PROTECTED_PREFIXES)


def authorize_http_request(request: Request) -> tuple[Optional[uuid.UUID], Optional[tuple[int, str]]]:
    """
    Validate session auth for an incoming HTTP request.

    Returns ``(authenticated_user_id, None)`` when allowed, or
    ``(None, (status_code, detail))`` when rejected.
    """
    path = getattr(getattr(request, "url", None), "path", "/") or "/"
    method = getattr(request, "method", "GET")
    if not is_protected_api_path(path, method):
        return None, None

    token = extract_token_from_request(request)
    if token:
        payload = verify_session_token(token)
        if payload is None:
            return None, (401, "Invalid or expired session token. Please sign in again.")
        token_uid = uuid.UUID(payload["sub"])
        query_params = getattr(request, "query_params", None) or {}
        claimed_uid = (query_params.get("user_id") or "").strip() if hasattr(query_params, "get") else ""
        if claimed_uid:
            try:
                if uuid.UUID(claimed_uid) != token_uid:
                    return None, (403, "Session does not match requested user_id.")
            except ValueError:
                return None, (403, "Invalid user_id for session.")
        return token_uid, None

    clean = path.rstrip("/") or "/"
    if clean == "/auth/gmail/account" or is_auth_enforced():
        return None, (401, "Authentication required. Please sign in.")
    return None, None

