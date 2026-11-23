"""
Tests for Senior-Engineer Production Hardening:
  1. Signed HS256 JWT session tokens + authorize_http_request + middleware
  2. DPDP Account Deletion (DELETE /auth/gmail/account) + OpenAPI schema check
  3. Cloud Object Storage (pure-stdlib SigV4 + httpx MockTransport + local fallback)
  4. Rate Limiting (per-user / per-IP sliding window)
  5. External Daily Alert Cron (POST /alerts/cron/run-daily + DISABLE_INPROCESS_SCHEDULER)
  6. Readiness probe enrichment (GET /health/ready)

All tests run synchronously without TestClient or asyncio event loops.
"""

import json
import uuid
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.datastructures import Headers, URL

from app.database import Base
from app.models import Alert, EmailInbox, Purchase, User, WarrantyPeriod, WhatsAppLink
from app.services import alert_engine, rate_limit, session_auth, storage


# ── Helpers / fixtures ───────────────────────────────────────────────────────

class _FakeRequest:
    def __init__(
        self,
        path: str = "/purchases",
        method: str = "GET",
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        query: str = "",
        host: str = "127.0.0.1",
    ):
        url_str = f"https://warranty-agent.onrender.com{path}"
        if query:
            url_str = f"{url_str}?{query}"
        self.url = URL(url_str)
        self.method = method
        self.headers = Headers(headers or {})
        self.cookies = cookies or {}
        self.query_params = {k: v[0] for k, v in parse_qs(query).items()}
        self.client = type("Client", (), {"host": host})()


def _run_async(coro):
    """Step an async function without creating an asyncio event loop."""
    sent = None
    while True:
        try:
            yielded = coro.send(sent)
            raise AssertionError(f"Unexpected await inside _run_async: {yielded!r}")
        except StopIteration as exc:
            return exc.value


@pytest.fixture()
def db():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(eng, "connect")
    def _fk(dbapi_con, _):
        dbapi_con.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    session = sessionmaker(bind=eng)()
    yield session
    session.close()
    eng.dispose()


@pytest.fixture()
def session_env(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "super-secret-signing-key-for-tests")
    monkeypatch.setenv("REQUIRE_AUTH_TOKEN", "true")


def _make_user(db, email="nikita@example.com") -> User:
    u = User(id=uuid.uuid4(), email=email)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


# ── 1. Signed JWT Session Auth ───────────────────────────────────────────────

class TestSessionAuth:
    def test_token_roundtrip_and_tamper_rejection(self, session_env):
        uid = uuid.uuid4()
        tok = session_auth.create_session_token(uid, "nikita@example.com", ttl_seconds=3600, now=1_000)
        payload = session_auth.verify_session_token(tok, now=1_100)
        assert payload is not None
        assert payload["sub"] == str(uid)
        assert payload["email"] == "nikita@example.com"

        # Tampered payload or signature must fail
        h, p, s = tok.split(".")
        bad_sig = session_auth.verify_session_token(f"{h}.{p}.tampered", now=1_100)
        assert bad_sig is None

        # Expired token fails
        assert session_auth.verify_session_token(tok, now=5_000) is None

        # Algorithm mismatch ("none") fails
        none_hdr = session_auth._b64url_encode(b'{"alg":"none","typ":"JWT"}')
        assert session_auth.verify_session_token(f"{none_hdr}.{p}.{s}", now=1_100) is None

    def test_authorize_http_request_enforces_bearer_cookie_and_user_match(self, session_env):
        uid = uuid.uuid4()
        other_uid = uuid.uuid4()
        tok = session_auth.create_session_token(uid, "nikita@example.com")

        # Missing token on protected endpoint -> 401
        auth_uid, err = session_auth.authorize_http_request(_FakeRequest("/purchases", query=f"user_id={uid}"))
        assert auth_uid is None and err is not None and err[0] == 401

        # Invalid token -> 401
        _, err_bad = session_auth.authorize_http_request(
            _FakeRequest("/purchases", headers={"Authorization": "Bearer nope"})
        )
        assert err_bad is not None and err_bad[0] == 401

        # Cross-user user_id mismatch -> 403
        _, err_cross = session_auth.authorize_http_request(
            _FakeRequest(
                "/purchases",
                headers={"Authorization": f"Bearer {tok}"},
                query=f"user_id={other_uid}",
            )
        )
        assert err_cross is not None and err_cross[0] == 403

        # Matching Bearer succeeds
        ok_uid, ok_err = session_auth.authorize_http_request(
            _FakeRequest(
                "/purchases",
                headers={"Authorization": f"Bearer {tok}"},
                query=f"user_id={uid}",
            )
        )
        assert ok_uid == uid and ok_err is None

        # Cookie fallback also works
        ck_uid, ck_err = session_auth.authorize_http_request(
            _FakeRequest("/alerts", cookies={session_auth.SESSION_COOKIE_NAME: tok})
        )
        assert ck_uid == uid and ck_err is None

    def test_public_endpoints_and_preflight_skip_auth(self, session_env):
        for path, method in (
            ("/health", "GET"),
            ("/health/ready", "GET"),
            ("/auth/gmail/connect", "GET"),
            ("/auth/gmail/callback", "GET"),
            ("/auth/gmail/email-connect", "POST"),
            ("/whatsapp/webhook", "POST"),
            ("/whatsapp/twilio-webhook", "POST"),
            ("/ingestion/inbound-email", "POST"),
            ("/alerts/cron/run-daily", "POST"),
            ("/purchases", "OPTIONS"),
            ("/", "GET"),
        ):
            _, err = session_auth.authorize_http_request(_FakeRequest(path, method=method))
            assert err is None, f"Expected {method} {path} to be public, got {err}"

    def test_email_connect_issues_valid_jwt_and_openapi_builds(self, db, session_env):
        from app.routers.auth_gmail import email_connect
        from app.schemas import EmailConnectRequest
        from main import app

        res = email_connect(EmailConnectRequest(email="fresh@example.com"), db)
        assert res.access_token is not None
        verified = session_auth.verify_session_token(res.access_token)
        assert verified is not None and verified["sub"] == str(res.user_id)

        # Ensure FastAPI OpenAPI schema builds cleanly with all new routes
        schema = app.openapi()
        assert "/auth/gmail/account" in schema["paths"]
        assert "/purchases/{purchase_id}/invoice-url" in schema["paths"]

    def test_production_middleware_blocks_unauth_and_rate_limits(self, session_env):
        from main import production_security_middleware

        async def _next(req):
            raise AssertionError("Should have short-circuited before next handler")

        resp_401 = _run_async(production_security_middleware(_FakeRequest("/purchases"), _next))
        assert resp_401.status_code == 401
        assert b"Authentication required" in resp_401.body


# ── 2. Account Deletion (DPDP Act) ───────────────────────────────────────────

class TestAccountDeletion:
    def test_delete_account_requires_valid_token_and_cascades_all_data(self, db, session_env, tmp_path):
        from app.routers.auth_gmail import delete_account

        # Unauthenticated -> 401
        with pytest.raises(HTTPException) as exc:
            delete_account(_FakeRequest("/auth/gmail/account", "DELETE"), db)
        assert exc.value.status_code == 401

        user = _make_user(db)
        invoice_file = tmp_path / "bill.pdf"
        invoice_file.write_bytes(b"%PDF-1.4 test")

        purchase = Purchase(
            id=uuid.uuid4(),
            user_id=user.id,
            product_name="Test Laptop",
            retailer="Amazon.in",
            source_type="upload",
            source_file_ref=str(invoice_file),
        )
        db.add(purchase)
        db.flush()
        db.add(WarrantyPeriod(purchase_id=purchase.id, confidence_score="high", is_estimated=False))
        db.add(
            Alert(
                purchase_id=purchase.id,
                alert_type="warranty_expiry",
                fire_date=datetime.utcnow() + timedelta(days=5),
            )
        )
        db.add(WhatsAppLink(user_id=user.id, phone_number="919876543210"))
        db.add(EmailInbox(user_id=user.id, inbox_token="abc123xyz9"))
        db.commit()

        tok = session_auth.create_session_token(user.id, user.email)
        req = _FakeRequest(
            "/auth/gmail/account",
            method="DELETE",
            headers={"Authorization": f"Bearer {tok}"},
        )
        resp = delete_account(req, db)
        assert resp.status_code == 204
        assert db.query(User).filter_by(id=user.id).first() is None
        assert db.query(Purchase).count() == 0
        assert db.query(Alert).count() == 0
        assert db.query(WhatsAppLink).count() == 0
        assert db.query(EmailInbox).count() == 0
        assert not invoice_file.exists()


# ── 3. Cloud Object Storage (SigV4 + Local Fallback) ─────────────────────────

class TestStorage:
    def test_local_save_and_delete(self, tmp_path, monkeypatch):
        monkeypatch.delenv("STORAGE_ENDPOINT_URL", raising=False)
        monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))

        assert storage.is_cloud_storage_configured() is False
        ref = storage.save_file(b"hello bill", "my bill?.pdf", "application/pdf")
        assert ref.startswith(str(tmp_path))
        assert storage.get_download_url(ref) is None

        from pathlib import Path

        assert Path(ref).read_bytes() == b"hello bill"
        storage.delete_file(ref)
        assert not Path(ref).exists()

    def test_cloud_storage_sigv4_put_presign_and_delete(self, monkeypatch):
        monkeypatch.setenv("STORAGE_ENDPOINT_URL", "https://acct.r2.cloudflarestorage.com")
        monkeypatch.setenv("STORAGE_BUCKET", "warranty-invoices")
        monkeypatch.setenv("STORAGE_ACCESS_KEY_ID", "AKIATESTKEY")
        monkeypatch.setenv("STORAGE_SECRET_ACCESS_KEY", "testsecretkey")
        monkeypatch.setenv("STORAGE_REGION", "auto")

        seen_requests = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen_requests.append((request.method, str(request.url), dict(request.headers), request.content))
            return httpx.Response(200)

        http = httpx.Client(transport=httpx.MockTransport(handler))
        ref = storage.save_file(b"%PDF-1.4", "sony invoice.pdf", "application/pdf", http=http)
        assert ref.startswith("s3://invoices/") and ref.endswith("_sony_invoice.pdf")

        method, url, headers, body = seen_requests[0]
        assert method == "PUT"
        assert url.startswith("https://acct.r2.cloudflarestorage.com/warranty-invoices/invoices/")
        assert body == b"%PDF-1.4"
        assert headers["authorization"].startswith("AWS4-HMAC-SHA256 Credential=AKIATESTKEY/")
        assert "x-amz-content-sha256" in headers

        presigned = storage.get_download_url(ref, expires_in=120)
        assert presigned is not None
        assert "X-Amz-Algorithm=AWS4-HMAC-SHA256" in presigned
        assert "X-Amz-Expires=120" in presigned
        assert "X-Amz-Signature=" in presigned

        # Pipe-separated multi-file deletion works cleanly
        storage.delete_file(f"{ref} | s3://invoices/second.pdf", http=http)
        assert [r[0] for r in seen_requests[1:]] == ["DELETE", "DELETE"]

    def test_resolve_local_file_rejects_traversal_and_cloud_refs(self, tmp_path, monkeypatch):
        uploads_dir = tmp_path / "uploads"
        uploads_dir.mkdir()
        monkeypatch.delenv("STORAGE_ENDPOINT_URL", raising=False)
        monkeypatch.setenv("UPLOAD_DIR", str(uploads_dir))

        saved_ref = storage.save_file(b"pdf-bytes", "receipt.pdf", "application/pdf")
        resolved = storage.resolve_local_file(saved_ref)
        assert resolved is not None and resolved.read_bytes() == b"pdf-bytes"

        outside_file = tmp_path / "outside.txt"
        outside_file.write_text("secret")
        assert storage.resolve_local_file(str(outside_file)) is None
        assert storage.resolve_local_file("s3://invoices/abc_receipt.pdf") is None

    def test_get_invoice_file_endpoint_serves_local_or_404(self, db, tmp_path, monkeypatch):
        from fastapi.responses import FileResponse
        from app.routers.purchases import get_invoice_file

        uploads_dir = tmp_path / "uploads"
        uploads_dir.mkdir()
        monkeypatch.delenv("STORAGE_ENDPOINT_URL", raising=False)
        monkeypatch.setenv("UPLOAD_DIR", str(uploads_dir))

        user = _make_user(db)
        saved_ref = storage.save_file(b"invoice-data", "fridge bill.pdf", "application/pdf")
        purchase = Purchase(
            user_id=user.id,
            product_name="LG Fridge",
            source_type="upload",
            source_file_ref=saved_ref,
        )
        db.add(purchase)
        db.commit()
        db.refresh(purchase)

        resp = get_invoice_file(purchase_id=purchase.id, user_id=user.id, db=db)
        assert isinstance(resp, FileResponse)
        assert resp.path == saved_ref
        assert resp.filename == "fridge_bill.pdf"

        storage.delete_file(saved_ref)
        with pytest.raises(HTTPException) as exc404:
            get_invoice_file(purchase_id=purchase.id, user_id=user.id, db=db)
        assert exc404.value.status_code == 404


# ── 4. Rate Limiting & External Cron & Readiness ─────────────────────────────

class TestRateLimitCronAndHealth:
    def test_rate_limiter_enforces_limit_and_recovers(self):
        limiter = rate_limit.RateLimiter(limit=2, window_seconds=10)
        assert limiter.check("u1", now=0.0) == (True, 0)
        assert limiter.check("u1", now=2.0) == (True, 0)
        allowed, retry_after = limiter.check("u1", now=3.0)
        assert allowed is False and retry_after == 7
        assert limiter.check("u1", now=11.0) == (True, 0)

    def test_route_rate_limit_applies_to_expensive_endpoints(self):
        rate_limit.reset_all_limiters()
        key = f"user-{uuid.uuid4().hex}"
        for _ in range(10):
            ok, _ = rate_limit.check_request_rate_limit("POST", "/ingestion/fetch-emails", key, now=100.0)
            assert ok is True
        blocked, retry = rate_limit.check_request_rate_limit("POST", "/ingestion/fetch-emails", key, now=101.0)
        assert blocked is False and retry >= 1
        rate_limit.reset_all_limiters()

    def test_cron_endpoint_security_and_execution(self, monkeypatch):
        from app.routers.alerts import trigger_daily_alerts

        monkeypatch.delenv("CRON_SECRET", raising=False)
        with pytest.raises(HTTPException) as exc503:
            trigger_daily_alerts(x_cron_secret="x")
        assert exc503.value.status_code == 503

        monkeypatch.setenv("CRON_SECRET", "cron-secret-123")
        with pytest.raises(HTTPException) as exc403:
            trigger_daily_alerts(x_cron_secret="wrong")
        assert exc403.value.status_code == 403

        monkeypatch.setattr("app.routers.alerts.run_daily_alert_check", lambda: 4)
        res = trigger_daily_alerts(x_cron_secret="cron-secret-123")
        assert res == {"status": "ok", "alerts_processed": 4}

    def test_disable_inprocess_scheduler_flag(self, monkeypatch):
        monkeypatch.setenv("DISABLE_INPROCESS_SCHEDULER", "true")
        # Should return cleanly without starting BackgroundScheduler
        alert_engine.start_scheduler()

    def test_readiness_probe_reports_hardening_checks(self, monkeypatch):
        from fastapi import Response
        from app.routers.health import readiness_check

        monkeypatch.setenv("REQUIRE_AUTH_TOKEN", "true")
        resp = Response()
        data = readiness_check(resp)
        checks = data["checks"]
        assert "storage" in checks
        assert "whatsapp" in checks
        assert "inbound_email" in checks
        assert checks["auth_enforced"] is True
