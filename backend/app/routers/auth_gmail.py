"""
Gmail OAuth 2.0 connect + callback endpoints.

Flow:
  1. GET /auth/gmail/connect  → redirect user to Google's consent screen
  2. GET /auth/gmail/callback → exchange code for tokens, encrypt refresh token,
                                upsert user record, return user info

Environment variables required (see .env.example):
  GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI

The Gmail scope requested is gmail.readonly — minimal required privilege.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import OAuthCallbackResponse
from app.services.encryption import encrypt_token

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter()

_GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

_GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID")
_GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
_GOOGLE_REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/gmail/callback")


def _build_flow() -> Flow:
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
        scopes=_GMAIL_SCOPES,
        redirect_uri=_GOOGLE_REDIRECT_URI,
    )


@router.get("/connect", summary="Redirect to Google OAuth consent screen")
def gmail_connect():
    """
    Build a Google OAuth2 authorization URL and redirect the user to it.
    The state parameter is set to a placeholder — extend with CSRF protection
    in a later milestone when session management is added.
    """
    try:
        flow = _build_flow()
        auth_url, state = flow.authorization_url(
            access_type="offline",   # Required to get a refresh token
            include_granted_scopes="true",
            prompt="consent",        # Force consent screen to always return refresh token
        )
        logger.info("Redirecting user to Google OAuth consent screen (state=%s)", state)
        return RedirectResponse(url=auth_url)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to build OAuth URL: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to initiate OAuth flow") from exc


@router.get("/callback", response_model=OAuthCallbackResponse, summary="Handle Google OAuth callback")
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
        flow = _build_flow()
        flow.fetch_token(code=code)
        credentials: Credentials = flow.credentials
    except Exception as exc:
        logger.error("Token exchange failed: %s", exc)
        raise HTTPException(
            status_code=400,
            detail="Failed to exchange authorization code for tokens. Try connecting again.",
        ) from exc

    # -- Fetch user's Gmail address from Google --
    try:
        user_info_service = build("oauth2", "v2", credentials=credentials, cache_discovery=False)
        user_info = user_info_service.userinfo().get().execute()
        email: str = user_info.get("email", "").lower().strip()
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

    if encrypted_token:
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
    return OAuthCallbackResponse(user_id=user.id, email=user.email)
