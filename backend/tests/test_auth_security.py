"""Security regression tests for OAuth redirects and direct email sign-in."""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from app.models import User
from app.routers.auth_gmail import (
    _DEFAULT_FRONTEND_ORIGIN,
    _fallback_origin,
    _is_safe_origin,
    email_connect,
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
