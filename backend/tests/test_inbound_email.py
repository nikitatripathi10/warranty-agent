"""
Tests for forward-to-email ingestion (app/services/inbound_email.py +
app/routers/inbound_email.py).

Everything runs offline: SQLite in memory, monkeypatched extraction and a fake
WhatsApp client. Route handlers are called directly (no TestClient), matching the
rest of the suite.
"""

import base64
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import EmailInbox, Purchase, PurchasePaymentMethod, User
from app.routers import inbound_email as router
from app.schemas import InboundAttachment, InboundEmailPayload
from app.services import inbound_email as svc
from app.services import whatsapp_client
from app.services.extractor_regex import ExtractionResult
from app.services.whatsapp_bot import SlidingWindowLimiter, create_link_code, link_phone_with_code

SECRET = "s3cret-value"
DOMAIN = "warrantyagent.in"


# ── Fixtures / helpers ───────────────────────────────────────────────────────

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
def inbound_env(monkeypatch):
    monkeypatch.setenv("INBOUND_EMAIL_DOMAIN", DOMAIN)
    monkeypatch.setenv("INBOUND_EMAIL_SECRET", SECRET)
    # Fresh limiter per test so tests never starve each other.
    monkeypatch.setattr(svc, "inbound_limiter", SlidingWindowLimiter(limit=60, window_seconds=3600))


def make_user(db):
    user = User(id=uuid.uuid4(), email=f"u_{uuid.uuid4().hex[:8]}@example.com")
    db.add(user)
    db.commit()
    return user


def result(name="Sony WH-1000XM5 Headphones", payment_text=None, **overrides):
    values = dict(
        product_name=name,
        brand="Sony",
        retailer="Amazon.in",
        purchase_date=(datetime.utcnow() - timedelta(days=3)).date(),
        price=Decimal("26990"),
        warranty_period_months=12,
        return_window_days=10,
        confidence="high",
        payment_text=payment_text,
    )
    values.update(overrides)
    return ExtractionResult(**values)


def address_for(db, user):
    return svc.build_address(svc.get_or_create_inbox(db, user).inbox_token)


def post(db, to, **fields):
    fields.setdefault("message_id", f"<{uuid.uuid4().hex}@mail.example>")
    return router.receive_inbound_email(
        body=InboundEmailPayload(to=to, **fields), x_inbound_email_secret=SECRET, db=db
    )


class FakeClient:
    def __init__(self):
        self.sent = []

    def send_text(self, to, body):
        self.sent.append((to, body))


# ── Addresses and tokens ─────────────────────────────────────────────────────

class TestAddresses:
    def test_token_extraction_variants(self, inbound_env):
        assert svc.extract_token_from_address("bills+abc123xyz9@warrantyagent.in") == "abc123xyz9"
        assert svc.extract_token_from_address("Bills <Bills+ABC123XYZ9@WarrantyAgent.in>") == "abc123xyz9"
        assert (
            svc.extract_token_from_address("other@x.com, bills+abc123xyz9@warrantyagent.in") == "abc123xyz9"
        )

    def test_rejects_wrong_domain_prefix_or_short_token(self, inbound_env):
        assert svc.extract_token_from_address("bills+abc123xyz9@evil.com") is None
        assert svc.extract_token_from_address("hello+abc123xyz9@warrantyagent.in") is None
        assert svc.extract_token_from_address("bills+abc@warrantyagent.in") is None
        assert svc.extract_token_from_address("bills@warrantyagent.in") is None
        assert svc.extract_token_from_address("") is None
        assert svc.extract_token_from_address(None) is None

    def test_domain_not_enforced_when_unset(self, monkeypatch):
        monkeypatch.delenv("INBOUND_EMAIL_DOMAIN", raising=False)
        assert svc.extract_token_from_address("bills+abc123xyz9@anywhere.com") == "abc123xyz9"

    def test_build_address_and_token_shape(self, inbound_env):
        token = svc.generate_inbox_token()
        assert len(token) == svc.TOKEN_LENGTH and token == token.lower() and token.isalnum()
        assert svc.build_address("abc123xyz9") == "bills+abc123xyz9@warrantyagent.in"

    def test_inbox_is_stable_and_rotation_replaces_it(self, db, inbound_env):
        user = make_user(db)
        first = svc.get_or_create_inbox(db, user)
        assert svc.get_or_create_inbox(db, user).inbox_token == first.inbox_token
        old = first.inbox_token

        rotated = svc.rotate_inbox(db, user)
        assert rotated.inbox_token != old
        assert svc.find_user_by_token(db, old) is None
        assert svc.find_user_by_token(db, rotated.inbox_token.upper()).id == user.id
        assert db.query(EmailInbox).count() == 1

    def test_deleting_user_removes_inbox(self, db, inbound_env):
        user = make_user(db)
        svc.get_or_create_inbox(db, user)
        db.delete(user)
        db.commit()
        assert db.query(EmailInbox).count() == 0


# ── Gmail forwarding confirmation ────────────────────────────────────────────

class TestForwardingConfirmation:
    def test_code_from_body_and_subject(self):
        assert (
            svc.detect_forwarding_confirmation(
                "Gmail Team <forwarding-noreply@google.com>",
                "Gmail Forwarding Confirmation",
                "Confirmation code: 123456789",
            )
            == "123456789"
        )
        assert (
            svc.detect_forwarding_confirmation(
                "forwarding-noreply@google.com", "(#987654321) Gmail Forwarding Confirmation - x", ""
            )
            == "987654321"
        )

    def test_ordinary_mail_is_not_a_confirmation(self):
        assert svc.detect_forwarding_confirmation("orders@amazon.in", "Your order", "code 123456") is None
        assert svc.detect_forwarding_confirmation("", "", "") is None

    def test_code_is_stored_shown_and_expires(self, db, inbound_env, monkeypatch):
        user = make_user(db)
        to = address_for(db, user)
        reply = post(
            db,
            to,
            sender="Gmail Team <forwarding-noreply@google.com>",
            subject="(#123456789) Gmail Forwarding Confirmation - Receive Mail from a@gmail.com",
            text="Confirmation code: 123456789",
        )
        assert reply.status == "forwarding_confirmation"
        assert db.query(Purchase).count() == 0
        assert router.get_forwarding_address(user_id=user.id, db=db).verification_code == "123456789"

        inbox = db.query(EmailInbox).one()
        inbox.verification_received_at = datetime.utcnow() - timedelta(hours=25)
        db.commit()
        assert router.get_forwarding_address(user_id=user.id, db=db).verification_code is None


# ── Processing forwarded emails ──────────────────────────────────────────────

class TestProcessing:
    def test_forwarded_order_is_saved(self, db, inbound_env, monkeypatch):
        user = make_user(db)
        monkeypatch.setattr(
            svc,
            "_run_extraction_pipeline",
            lambda text, **k: result(payment_text="Payment: Axis Bank Magnus Credit Card ending 5566"),
        )
        reply = post(
            db,
            address_for(db, user),
            sender="orders@amazon.in",
            subject="Your Amazon.in order",
            text="Order confirmed: Sony WH-1000XM5, Rs 26,990, 1 year warranty",
            message_id="<abc@amazon>",
        )
        assert reply.status == "saved"
        assert reply.product_name == "Sony WH-1000XM5 Headphones"

        purchase = db.query(Purchase).filter_by(user_id=user.id).one()
        assert purchase.source_type == "email"
        assert purchase.source_email_id == "fwd:<abc@amazon>"
        card = db.query(PurchasePaymentMethod).one()
        assert card.card_key == "axis_magnus" and card.last4 == "5566"

    def test_html_only_email_is_used(self, db, inbound_env, monkeypatch):
        user = make_user(db)
        seen = {}

        def fake_pipeline(text, **k):
            seen["text"] = text
            return result()

        monkeypatch.setattr(svc, "_run_extraction_pipeline", fake_pipeline)
        post(db, address_for(db, user), subject="Invoice", html="<p>Sony headphones Rs 26990</p>")
        assert "Subject: Invoice" in seen["text"] and "<p>Sony headphones" in seen["text"]

    def test_same_message_or_same_product_is_not_duplicated(self, db, inbound_env, monkeypatch):
        user = make_user(db)
        monkeypatch.setattr(svc, "_run_extraction_pipeline", lambda text, **k: result())
        to = address_for(db, user)

        assert post(db, to, text="order", message_id="<one>").status == "saved"
        assert post(db, to, text="order", message_id="<one>").status == "duplicate"  # redelivery
        assert post(db, to, text="order again", message_id="<two>").status == "duplicate"  # same product
        assert db.query(Purchase).filter_by(user_id=user.id).count() == 1

    def test_unreadable_email_saves_nothing(self, db, inbound_env, monkeypatch):
        user = make_user(db)
        monkeypatch.setattr(svc, "_run_extraction_pipeline", lambda text, **k: ExtractionResult(confidence="low"))
        reply = post(db, address_for(db, user), subject="Hello", text="Lunch tomorrow?")
        assert reply.status == "unreadable" and reply.product_name is None
        assert db.query(Purchase).count() == 0

    def test_empty_email_is_unreadable(self, db, inbound_env):
        user = make_user(db)
        assert post(db, address_for(db, user)).status == "unreadable"

    def test_attachment_is_used_and_missing_fields_filled_from_body(self, db, inbound_env, monkeypatch):
        user = make_user(db)
        monkeypatch.setattr(
            svc,
            "_run_extraction_pipeline",
            lambda text, **k: ExtractionResult(retailer="Amazon.in", price=Decimal("999"), confidence="low"),
        )
        monkeypatch.setattr(
            svc,
            "process_file_bytes",
            lambda data, name, ctype: (
                "uploads/inv.pdf",
                "inv.pdf",
                ExtractionResult(
                    product_name="boAt Airdopes 141",
                    brand="boAt",
                    purchase_date=datetime.utcnow().date(),
                    warranty_period_months=12,
                    confidence="high",
                ),
                False,
            ),
        )
        reply = post(
            db,
            address_for(db, user),
            subject="Invoice attached",
            text="see attached",
            attachments=[
                InboundAttachment(
                    filename="inv.pdf",
                    content_type="application/pdf",
                    content_base64=base64.b64encode(b"%PDF-fake").decode(),
                )
            ],
        )
        assert reply.status == "saved"
        purchase = db.query(Purchase).one()
        assert purchase.product_name == "boAt Airdopes 141"
        assert purchase.price == Decimal("999.00")
        assert purchase.source_file_ref == "uploads/inv.pdf"

    def test_bad_attachment_is_skipped_and_next_one_used(self, db, inbound_env, monkeypatch):
        user = make_user(db)
        monkeypatch.setattr(svc, "_run_extraction_pipeline", lambda text, **k: ExtractionResult(confidence="low"))

        def fake_process(data, name, ctype):
            if name == "huge.pdf":
                raise HTTPException(status_code=413, detail="too large")
            return "uploads/ok.pdf", name, result("LG Washing Machine"), False

        monkeypatch.setattr(svc, "process_file_bytes", fake_process)
        b64 = base64.b64encode(b"data").decode()
        reply = post(
            db,
            address_for(db, user),
            text="bill",
            attachments=[
                InboundAttachment(filename="huge.pdf", content_type="application/pdf", content_base64=b64),
                InboundAttachment(filename="ok.pdf", content_type="application/pdf", content_base64=b64),
            ],
        )
        assert reply.status == "saved"
        assert db.query(Purchase).one().source_file_ref == "uploads/ok.pdf"

    def test_decode_attachments_skips_corrupt_empty_and_extra(self):
        good = base64.b64encode(b"hello").decode()
        items = [("a.pdf", "application/pdf", good), ("empty.pdf", "", ""), ("c.pdf", "", good)] + [
            (f"x{i}.pdf", "", good) for i in range(10)
        ]
        decoded = svc.decode_attachments(items)
        # Only the first 5 incoming items are considered; the empty one among them is dropped.
        assert [d.filename for d in decoded] == ["a.pdf", "c.pdf", "x0.pdf", "x1.pdf"]


# ── WhatsApp confirmation ────────────────────────────────────────────────────

class TestWhatsAppConfirmation:
    def test_linked_user_gets_a_whatsapp_confirmation(self, db, inbound_env, monkeypatch):
        user = make_user(db)
        phone = "91" + str(uuid.uuid4().int)[:10]
        link_phone_with_code(db, phone, create_link_code(db, user)[0])
        monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC1")
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "tok")
        monkeypatch.delenv("WHATSAPP_ACCESS_TOKEN", raising=False)
        fake = FakeClient()
        monkeypatch.setattr(whatsapp_client, "get_active_client", lambda: fake)
        monkeypatch.setattr(svc, "_run_extraction_pipeline", lambda text, **k: result())

        assert post(db, address_for(db, user), text="order").status == "saved"
        assert len(fake.sent) == 1
        to, body = fake.sent[0]
        assert to == phone
        assert "Forwarded email processed" in body and "Sony WH-1000XM5" in body

    def test_no_message_when_not_linked_or_not_configured(self, db, inbound_env, monkeypatch):
        user = make_user(db)
        fake = FakeClient()
        monkeypatch.setattr(whatsapp_client, "get_active_client", lambda: fake)
        monkeypatch.setattr(svc, "_run_extraction_pipeline", lambda text, **k: result())
        monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
        monkeypatch.delenv("WHATSAPP_ACCESS_TOKEN", raising=False)

        assert post(db, address_for(db, user), text="order").status == "saved"
        assert fake.sent == []

    def test_failed_notification_never_fails_ingestion(self, db, inbound_env, monkeypatch):
        user = make_user(db)
        phone = "91" + str(uuid.uuid4().int)[:10]
        link_phone_with_code(db, phone, create_link_code(db, user)[0])
        monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC1")
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "tok")

        def boom():
            raise RuntimeError("twilio down")

        monkeypatch.setattr(whatsapp_client, "get_active_client", boom)
        monkeypatch.setattr(svc, "_run_extraction_pipeline", lambda text, **k: result())
        assert post(db, address_for(db, user), text="order").status == "saved"


# ── Endpoint security and behaviour ──────────────────────────────────────────

class TestEndpoints:
    def test_routes_registered(self):
        from main import app

        methods = {}
        for route in app.routes:
            path = getattr(route, "path", None)
            if path:
                methods.setdefault(path, set()).update(getattr(route, "methods", None) or set())
        assert "POST" in methods.get("/ingestion/inbound-email", set())
        assert "GET" in methods.get("/ingestion/forwarding-address", set())
        assert "POST" in methods.get("/ingestion/forwarding-address/rotate", set())

    def test_503_when_not_configured(self, db, monkeypatch):
        monkeypatch.delenv("INBOUND_EMAIL_SECRET", raising=False)
        monkeypatch.delenv("INBOUND_EMAIL_DOMAIN", raising=False)
        with pytest.raises(HTTPException) as exc:
            router.receive_inbound_email(
                body=InboundEmailPayload(to="bills+abc123xyz9@x.com"), x_inbound_email_secret="x", db=db
            )
        assert exc.value.status_code == 503

    def test_wrong_or_missing_secret_is_403(self, db, inbound_env):
        body = InboundEmailPayload(to="bills+abc123xyz9@warrantyagent.in")
        for header in (None, "", "wrong"):
            with pytest.raises(HTTPException) as exc:
                router.receive_inbound_email(body=body, x_inbound_email_secret=header, db=db)
            assert exc.value.status_code == 403

    def test_unknown_inbox_is_ignored_silently(self, db, inbound_env):
        reply = post(db, "bills+zzzzzzzzzz@warrantyagent.in", text="order")
        assert reply.status == "ignored"
        assert post(db, "someone@warrantyagent.in", text="order").status == "ignored"

    def test_rotated_address_stops_working(self, db, inbound_env, monkeypatch):
        user = make_user(db)
        monkeypatch.setattr(svc, "_run_extraction_pipeline", lambda text, **k: result())
        old = address_for(db, user)
        router.rotate_forwarding_address(user_id=user.id, db=db)
        assert post(db, old, text="order").status == "ignored"
        assert db.query(Purchase).count() == 0

    def test_per_inbox_rate_limit(self, db, inbound_env, monkeypatch):
        user = make_user(db)
        monkeypatch.setattr(svc, "inbound_limiter", SlidingWindowLimiter(limit=1, window_seconds=3600))
        monkeypatch.setattr(svc, "_run_extraction_pipeline", lambda text, **k: result())
        to = address_for(db, user)
        assert post(db, to, text="order").status == "saved"
        with pytest.raises(HTTPException) as exc:
            post(db, to, text="order 2")
        assert exc.value.status_code == 429

    def test_forwarding_address_endpoints(self, db, inbound_env):
        user = make_user(db)
        info = router.get_forwarding_address(user_id=user.id, db=db)
        assert info.enabled is True and info.domain == DOMAIN
        assert info.address.startswith("bills+") and info.address.endswith("@warrantyagent.in")
        assert router.get_forwarding_address(user_id=user.id, db=db).address == info.address

        rotated = router.rotate_forwarding_address(user_id=user.id, db=db)
        assert rotated.address != info.address

    def test_forwarding_address_when_disabled(self, db, monkeypatch):
        monkeypatch.delenv("INBOUND_EMAIL_SECRET", raising=False)
        monkeypatch.delenv("INBOUND_EMAIL_DOMAIN", raising=False)
        user = make_user(db)
        info = router.get_forwarding_address(user_id=user.id, db=db)
        assert info.enabled is False and info.address is None
        assert db.query(EmailInbox).count() == 0  # nothing created while disabled
        with pytest.raises(HTTPException) as exc:
            router.rotate_forwarding_address(user_id=user.id, db=db)
        assert exc.value.status_code == 503

    def test_unknown_user_is_404(self, db, inbound_env):
        with pytest.raises(HTTPException) as exc:
            router.get_forwarding_address(user_id=uuid.uuid4(), db=db)
        assert exc.value.status_code == 404
