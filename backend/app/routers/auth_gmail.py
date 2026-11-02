"""
Google OAuth 2.0 endpoints.

Two entry points share one registered redirect URI:

  1. GET /auth/gmail/connect   → the flow the app uses: Google sign-in plus
                                 read-only Gmail access in a single consent.
  2. GET /auth/gmail/callback  → exchange code for tokens, encrypt refresh token,
                                 upsert user record, return user info.
  3. GET /auth/google/login    → optional identity-only sign-in
                                 (openid/email/profile) for clients that do not
                                 need inbox access.

Requesting gmail.readonly means Google shows the restricted-scope consent screen,
and an unverified app is displayed by domain only. That is unavoidable until the
app is served from a custom domain that passes brand verification.

Environment variables required (see .env.example):
  GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI

The Gmail scope requested is gmail.readonly — minimal required privilege.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from datetime import datetime
from urllib.parse import urlencode, urlparse

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, JSONResponse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import EmailConnectRequest, EmailConnectResponse, OAuthCallbackResponse
from app.services.encryption import encrypt_token

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter()

# Identity-only scopes. Google treats these as non-sensitive: the consent screen
# shows the app name and no "wants access to your Google Account" warning.
_BASIC_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

# Sign-in lives at /auth/google/login; Gmail connection stays at
# /auth/gmail/connect. Both reuse the single registered redirect URI below.
signin_router = APIRouter()

_GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"

_GMAIL_SCOPES = [
    _GMAIL_SCOPE,
    *_BASIC_SCOPES,
]

_GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID")
_GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
_GOOGLE_REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/gmail/callback").strip()


# Exact origins allowed to receive the post-OAuth redirect. Do NOT use suffix or
# substring matching here: an attacker can deploy https://vercel.app.evil.com or
# https://anything.vercel.app and steal the workspace token from the redirect.
_SAFE_PRODUCTION_ORIGINS = {
    "https://warranty-agent-nikita-54bd.vercel.app",
    "https://venerable-boba-fb4868.netlify.app",
    # The backend can serve the built SPA (see main.py), so the app is reachable
    # on the same origin as the API.
    "https://warranty-agent.onrender.com",
}

# Public, unprotected frontend. Used when the OAuth state carries no usable
# origin (e.g. the user hit /auth/gmail/connect directly). The Vercel URL is
# deliberately not the default because Deployment Protection blocks visitors.
_DEFAULT_FRONTEND_ORIGIN = "https://venerable-boba-fb4868.netlify.app"


def _normalize_origin(origin: str) -> str | None:
    """Return a canonical scheme://host[:port] origin, or None if invalid."""
    if not origin or not origin.strip():
        return None
    try:
        parsed = urlparse(origin.strip())
        if parsed.scheme not in {"http", "https"}:
            return None
        if parsed.username or parsed.password:
            return None
        if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
            return None
        host = (parsed.hostname or "").strip().lower()
        if not host:
            return None
        port = parsed.port
    except (TypeError, ValueError):
        return None
    netloc = host if port is None else f"{host}:{port}"
    return f"{parsed.scheme}://{netloc}"


def _configured_origins() -> set[str]:
    """Build the exact allowlist from known deployments + environment overrides."""
    origins = set(_SAFE_PRODUCTION_ORIGINS)
    for variable in ("FRONTEND_ORIGIN", "EXTRA_FRONTEND_ORIGINS"):
        raw = os.getenv(variable, "")
        for candidate in raw.split(","):
            normalized = _normalize_origin(candidate)
            if normalized:
                origins.add(normalized)
    return origins


_ALLOWED_ORIGINS = _configured_origins()


def _is_safe_origin(origin: str) -> bool:
    """Validate that the redirect target is an explicitly allowed frontend origin."""
    normalized = _normalize_origin(origin)
    if not normalized:
        return False
    host = (urlparse(normalized).hostname or "").lower()
    if host in {"localhost", "127.0.0.1"}:
        return True
    return normalized in _ALLOWED_ORIGINS


def _fallback_origin() -> str:
    """Safe default frontend when the OAuth state carries no usable origin."""
    configured = _normalize_origin(os.getenv("FRONTEND_ORIGIN", ""))
    if configured and _is_safe_origin(configured):
        return configured
    return _DEFAULT_FRONTEND_ORIGIN


def _encode_state(origin: str | None) -> str:
    payload = {"origin": origin or ""}
    return base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")


def _decode_state(state: str | None) -> str | None:
    if not state:
        return None
    try:
        decoded = base64.urlsafe_b64decode(state.encode("utf-8")).decode("utf-8")
        data = json.loads(decoded)
        origin = data.get("origin", "").strip()
        if _is_safe_origin(origin):
            return origin.rstrip("/")
    except Exception:
        pass
    return None


def _build_flow(scopes: list[str] | None = None) -> Flow:
    """Create an OAuth2 flow from environment variables (never from hardcoded values)."""
    if not _GOOGLE_CLIENT_ID or not _GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail=(
                "Google OAuth credentials are not configured. "
                "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env."
            ),
        )

    client_config = {
        "web": {
            "client_id":     _GOOGLE_CLIENT_ID,
            "client_secret": _GOOGLE_CLIENT_SECRET,
            "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
            "token_uri":     "https://oauth2.googleapis.com/token",
            "redirect_uris": [_GOOGLE_REDIRECT_URI],
        }
    }

    return Flow.from_client_config(
        client_config,
        scopes=scopes or _GMAIL_SCOPES,
        redirect_uri=_GOOGLE_REDIRECT_URI,
    )


def _resolve_caller_origin(request: Request, return_url: str | None) -> str | None:
    """Pick the frontend origin to return to, ignoring anything not on the allowlist."""
    if return_url and _is_safe_origin(return_url):
        return return_url.strip().rstrip("/")

    referer = request.headers.get("referer")
    if referer:
        parsed = urlparse(referer)
        candidate = f"{parsed.scheme}://{parsed.netloc}"
        if _is_safe_origin(candidate):
            return candidate
    return None


@signin_router.get("/login", summary="Sign in with Google (identity only, no Gmail access)")
def google_login(
    request: Request,
    return_url: str | None = Query(None, description="Frontend origin or URL to return to after sign-in"),
):
    """
    Identity-only Google sign-in.

    Requests just openid/email/profile, so Google shows the app name and skips
    the restricted-scope warning screen entirely. Gmail access is requested
    separately from /auth/gmail/connect when the user asks to scan their inbox.
    """
    try:
        flow = _build_flow(_BASIC_SCOPES)
        caller_origin = _resolve_caller_origin(request, return_url)
        auth_url, _ = flow.authorization_url(
            access_type="online",
            prompt="select_account",
            state=_encode_state(caller_origin),
        )
        logger.info(
            "Redirecting user to Google sign-in (caller_origin=%s)",
            caller_origin,
        )
        return RedirectResponse(url=auth_url)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to build Google sign-in URL: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to initiate Google sign-in") from exc


@router.get("/connect", summary="Redirect to Google OAuth consent screen")
def gmail_connect(
    request: Request,
    return_url: str | None = Query(None, description="Frontend origin or URL to return to after auth"),
):
    """
    Build a Google OAuth2 authorization URL and redirect the user to it.
    The state parameter safely encodes the caller's frontend origin so the user
    is returned to the exact website (Vercel, Netlify, or local) they started from.
    """
    try:
        flow = _build_flow(_GMAIL_SCOPES)

        caller_origin = _resolve_caller_origin(request, return_url)
        state_payload = _encode_state(caller_origin)
        auth_url, _ = flow.authorization_url(
            access_type="offline",   # Required to get a refresh token
            include_granted_scopes="true",
            prompt="consent",        # Force consent screen to choose account and return refresh token
            state=state_payload,
        )
        logger.info(
            "Redirecting user to Gmail consent screen (caller_origin=%s)",
            caller_origin,
        )
        return RedirectResponse(url=auth_url)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to build OAuth URL: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to initiate OAuth flow") from exc


@router.get("/callback", summary="Handle Google OAuth callback")
def gmail_callback(
    code: str,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Exchange the authorization code for tokens, encrypt the refresh token,
    and upsert the user record.

    Returns the user's UUID and email so the frontend can store the user_id
    locally for subsequent API calls.
    """
    # -- Handle user-denied consent --
    if error:
        logger.warning("OAuth callback returned error: %s", error)
        raise HTTPException(
            status_code=400,
            detail=f"Google OAuth was denied or failed: {error}",
        )

    # -- Exchange code for tokens --
    try:
        # Relax scope checking so users can sign in even if optional scopes are omitted
        os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
        flow = _build_flow()
        flow.fetch_token(code=code)
        credentials: Credentials = flow.credentials
    except Exception as exc:
        logger.error("Token exchange failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=f"Failed to exchange authorization code for tokens. Reason: {exc}",
        ) from exc

    # Check whether the user granted the Gmail scope. Identity-only sign-ins
    # (from /auth/google/login) never grant it, so we must not touch the stored
    # refresh token in that case.
    has_gmail_scope = False
    try:
        has_gmail_scope = credentials.has_scopes([_GMAIL_SCOPE])
    except Exception:
        has_gmail_scope = False

    # -- Fetch user's Gmail address & profile name from Google --
    full_name: str = ""
    try:
        user_info_service = build("oauth2", "v2", credentials=credentials, cache_discovery=False)
        user_info = user_info_service.userinfo().get().execute()
        email: str = user_info.get("email", "").lower().strip()
        full_name = (user_info.get("name") or user_info.get("given_name") or "").strip()
        if not email:
            raise ValueError("Google did not return an email address")
    except Exception as exc:
        logger.error("Failed to fetch user info from Google: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Could not retrieve your Gmail address from Google. Please try again.",
        ) from exc

    # -- Encrypt refresh token --
    refresh_token: str | None = credentials.refresh_token
    if not refresh_token:
        # This can happen if the user previously granted access and Google didn't
        # re-issue a refresh token. We'll keep the existing token in the DB.
        logger.warning(
            "Google did not return a refresh token for %s — using existing token if present",
            email,
        )

    encrypted_token: str | None = None
    if refresh_token:
        try:
            encrypted_token = encrypt_token(refresh_token)
        except Exception as exc:
            logger.error("Failed to encrypt refresh token: %s", exc)
            raise HTTPException(
                status_code=500,
                detail="Internal error: could not secure your credentials.",
            ) from exc

    # -- Upsert user record --
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(email=email)
        db.add(user)
        logger.info("Created new user record for %s", email)
    else:
        logger.info("Existing user record found for %s (id=%s)", email, user.id)

    if encrypted_token and has_gmail_scope:
        user.google_oauth_token_encrypted = encrypted_token

    try:
        db.commit()
        db.refresh(user)
    except Exception as exc:
        db.rollback()
        logger.error("Database error when upserting user %s: %s", email, exc)
        raise HTTPException(
            status_code=500,
            detail="Database error — please try again.",
        ) from exc

    logger.info("OAuth flow complete for user %s (id=%s)", email, user.id)

    # Return user to the exact frontend origin they initiated auth from (Vercel, Netlify, or local)
    target_origin = _decode_state(state) or _fallback_origin()

    params = {
        "user_id": str(user.id),
        "email": user.email,
        # Lets the frontend prompt "Connect Gmail to scan" instead of failing a
        # scan call when the user signed in with identity-only Google scopes.
        "gmail_connected": "1" if user.google_oauth_token_encrypted else "0",
    }
    if full_name:
        params["name"] = full_name
    redirect_url = f"{target_origin}/?" + urlencode(params)
    # Never log the full redirect URL: it contains the workspace token.
    logger.info("Redirecting authenticated user %s to %s", email, target_origin)
    return RedirectResponse(url=redirect_url)


@router.post(
    "/email-connect",
    response_model=EmailConnectResponse,
    summary="Directly connect or sign in with any email address",
)
def email_connect(
    body: EmailConnectRequest,
    db: Session = Depends(get_db),
) -> EmailConnectResponse:
    """
    Create a new workspace for an unused email, or reopen an existing workspace
    only when the caller presents the workspace token issued to that browser.

    Email alone is never enough to reopen an existing workspace: otherwise anyone
    who knows a user's address could read their receipts and warranty records.
    Users who lost their browser token can recover through Google sign-in, which
    proves ownership of the email address.
    """
    import re
    email = body.email.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(email=email)
        db.add(user)
        try:
            db.commit()
            db.refresh(user)
            logger.info("Created new user via direct email-connect: %s (id=%s)", email, user.id)
        except Exception as exc:
            db.rollback()
            logger.error("DB error creating user for %s: %s", email, exc)
            raise HTTPException(status_code=500, detail="Database error — please try again.") from exc
    else:
        if body.user_id is None or body.user_id != user.id:
            logger.warning(
                "Blocked direct email sign-in for existing workspace %s "
                "(workspace token missing or mismatched)",
                email,
            )
            raise HTTPException(
                status_code=403,
                detail=(
                    "This email already has a workspace. Open it from the browser where "
                    "you created it, or use “Connect with Google” to verify ownership."
                ),
            )
        logger.info("Existing user reopened via direct email-connect: %s (id=%s)", email, user.id)

    name = (body.name or "").strip()
    if not name:
        local_part = email.split("@")[0]
        cleaned = re.sub(r"\d+[a-zA-Z]?", " ", local_part)
        cleaned = re.sub(r"[._\-+]+", " ", cleaned).strip()
        words = [w.capitalize() for w in cleaned.split() if w]
        name = " ".join(words) if words else local_part.capitalize()

    return EmailConnectResponse(
        user_id=user.id,
        email=user.email,
        name=name,
        has_gmail_connected=bool(user.google_oauth_token_encrypted),
        message="Workspace ready",
    )
