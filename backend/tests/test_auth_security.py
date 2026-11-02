"""Security regression tests for OAuth redirects and direct email sign-in."""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from app.models import User
from app.routers import auth_gmail
from app.routers.auth_gmail import (
    _BASIC_SCOPES,
    _DEFAULT_FRONTEND_ORIGIN,
    _GMAIL_SCOPES,
    _decode_state,
    _fallback_origin,
    _is_safe_origin,
    email_connect,
    google_login,
)
from app.schemas import EmailConnectRequest


# ── OAuth redirect allowlist ──────────────────────────────────────────────────

@pytest.mark.parametrize(
    "origin",
    [
        "https://venerable-boba-fb4868.netlify.app",
        "https://venerable-boba-fb4868.netlify.app/",
        "https://warranty-agent-nikita-54bd.vercel.app",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
    ],
)
def test_allowed_oauth_origins(origin: str) -> None:
    assert _is_safe_origin(origin) is True


@pytest.mark.parametrize(
    "origin",
    [
        "",
        "https://vercel.app.evil.com",
        "https://evil-vercel.app",
        "https://venerable-boba-fb4868.netlify.app.evil.com",
        "https://venerable-boba-fb4868.netlify.app/steal",
        "https://venerable-boba-fb4868.netlify.app?x=1",
        "https://user:pass@venerable-boba-fb4868.netlify.app",
        "javascript:alert(1)",
        "not-a-url",
    ],
)
def test_rejected_oauth_origins(origin: str) -> None:
    assert _is_safe_origin(origin) is False


def test_fallback_origin_defaults_to_public_netlify(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FRONTEND_ORIGIN", raising=False)
    assert _fallback_origin() == _DEFAULT_FRONTEND_ORIGIN
    assert _DEFAULT_FRONTEND_ORIGIN == "https://venerable-boba-fb4868.netlify.app"


def test_fallback_origin_uses_configured_safe_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://localhost:5173")
    assert _fallback_origin() == "http://localhost:5173"


def test_fallback_origin_ignores_unsafe_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://evil.example.com")
    assert _fallback_origin() == _DEFAULT_FRONTEND_ORIGIN


# ── Google sign-in vs Gmail connection (scope split) ──────────────────────────

_GMAIL_READONLY = "https://www.googleapis.com/auth/gmail.readonly"


class _FakeRequest:
    """Only `headers` is read by the OAuth entry points."""

    def __init__(self, headers: dict[str, str] | None = None) -> None:
        self.headers = headers or {}


@pytest.fixture
def oauth_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_gmail, "_GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setattr(auth_gmail, "_GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setattr(
        auth_gmail, "_GOOGLE_REDIRECT_URI", "https://example.com/auth/gmail/callback"
    )


def _authorization_params(response) -> tuple[list[str], dict[str, list[str]]]:  # noqa: ANN001
    from urllib.parse import parse_qs, urlparse

    location = response.headers["location"]
    parsed = urlparse(location)
    scopes = parse_qs(parsed.query).get("scope", [""])[0].split()
    return scopes, parse_qs(parsed.query)


def test_signin_requests_identity_scopes_only(oauth_configured: None) -> None:
    response = google_login(_FakeRequest(), return_url=None)
    scopes, params = _authorization_params(response)

    assert _GMAIL_READONLY not in scopes
    assert scopes == _BASIC_SCOPES
    assert params["prompt"] == ["select_account"]
    assert params["access_type"] == ["online"]


def test_gmail_connect_still_requests_readonly_scope(oauth_configured: None) -> None:
    response = auth_gmail.gmail_connect(_FakeRequest(), return_url=None)
    scopes, params = _authorization_params(response)

    assert _GMAIL_READONLY in scopes
    assert set(scopes) == set(_GMAIL_SCOPES)
    assert params["prompt"] == ["consent"]
    assert params["access_type"] == ["offline"]


def test_signin_state_keeps_only_allowlisted_origins(oauth_configured: None) -> None:
    allowed = google_login(_FakeRequest(), return_url="https://venerable-boba-fb4868.netlify.app/")
    _, params = _authorization_params(allowed)
    assert _decode_state(params["state"][0]) == "https://venerable-boba-fb4868.netlify.app"

    blocked = google_login(_FakeRequest(), return_url="https://evil.example.com")
    _, blocked_params = _authorization_params(blocked)
    assert _decode_state(blocked_params["state"][0]) is None


def test_signin_does_not_use_referer_outside_allowlist(oauth_configured: None) -> None:
    response = google_login(
        _FakeRequest({"referer": "https://vercel.app.evil.com/signin"}), return_url=None
    )
    _, params = _authorization_params(response)
    assert _decode_state(params["state"][0]) is None


# ── Direct email sign-in ──────────────────────────────────────────────────────

class _FakeQuery:
    def __init__(self, user: User | None) -> None:
        self._user = user

    def filter(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return self

    def first(self):
        return self._user


class _FakeSession:
    """Minimal Session stand-in; no database required for these branches."""

    def __init__(self, user: User | None = None) -> None:
        self.user = user
        self.added: list[User] = []

    def query(self, model):  # noqa: ANN001
        return _FakeQuery(self.user)

    def add(self, obj: User) -> None:
        self.added.append(obj)
        self.user = obj

    def commit(self) -> None:
        pass

    def refresh(self, obj: User) -> None:
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()

    def rollback(self) -> None:
        pass


def _existing_user(email: str = "owner@example.com") -> User:
    user = User(email=email)
    user.id = uuid.uuid4()
    user.google_oauth_token_encrypted = None
    return user


def test_existing_workspace_cannot_be_opened_with_email_alone() -> None:
    user = _existing_user()
    with pytest.raises(HTTPException) as exc:
        email_connect(EmailConnectRequest(email="OWNER@example.com"), _FakeSession(user))
    assert exc.value.status_code == 403


def test_existing_workspace_rejects_a_different_workspace_token() -> None:
    user = _existing_user()
    with pytest.raises(HTTPException) as exc:
        email_connect(
            EmailConnectRequest(email="owner@example.com", user_id=uuid.uuid4()),
            _FakeSession(user),
        )
    assert exc.value.status_code == 403


def test_existing_workspace_reopens_with_its_browser_token() -> None:
    user = _existing_user()
    response = email_connect(
        EmailConnectRequest(email="owner@example.com", user_id=user.id),
        _FakeSession(user),
    )
    assert response.user_id == user.id
    assert response.email == "owner@example.com"


def test_new_email_still_creates_a_workspace() -> None:
    db = _FakeSession(None)
    response = email_connect(EmailConnectRequest(email="new@example.com"), db)
    assert response.email == "new@example.com"
    assert response.user_id is not None
    assert db.added and db.added[0].email == "new@example.com"
