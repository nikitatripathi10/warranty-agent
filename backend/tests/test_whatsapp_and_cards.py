"""
Tests for the two newest features:

  1. Credit-card benefit matcher  (app/services/card_benefits.py + routers/card_benefits.py)
  2. WhatsApp bot                 (app/services/whatsapp_*.py + routers/whatsapp.py)

Everything runs offline: SQLite in memory, a fake WhatsApp client, and
monkeypatched extraction - no Meta, Gemini or Gmail calls are made.
"""

import base64
import hashlib
import hmac
import json
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from urllib.parse import urlencode

import httpx
import pytest
from fastapi import BackgroundTasks, HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.datastructures import Headers, URL

from app.database import Base
from app.models import Alert, Purchase, PurchasePaymentMethod, User, WarrantyPeriod, WhatsAppLink
from app.services import alert_engine, whatsapp_bot, whatsapp_client
from app.services.card_benefits import (
    OTHER_CARD_KEY,
    analyze_card_benefit,
    build_card_report,
    detect_payment_card,
    get_payment_method,
    record_detected_card,
    set_manual_card,
)
from app.services.extractor_regex import ExtractionResult
from app.services.whatsapp_bot import (
    IncomingMessage,
    SeenMessageIds,
    SlidingWindowLimiter,
    create_link_code,
    get_user_by_phone,
    link_phone_with_code,
    mask_phone,
    parse_webhook_payload,
    process_incoming,
)
from app.services.whatsapp_client import WhatsAppError, verify_signature

TODAY = date(2026, 11, 21)


# ── Fixtures / helpers ───────────────────────────────────────────────────────

@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(eng, "connect")
    def _fk(dbapi_con, _):
        dbapi_con.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db(engine):
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def make_user(db, email=None):
    user = User(id=uuid.uuid4(), email=email or f"u_{uuid.uuid4().hex[:8]}@example.com")
    db.add(user)
    db.commit()
    return user


def make_purchase(db, user, name="HP Pavilion Laptop", months=12, purchase_date=None):
    pdate = purchase_date or (date.today() - timedelta(days=5))
    p = Purchase(
        id=uuid.uuid4(),
        user_id=user.id,
        product_name=name,
        brand="HP",
        retailer="Amazon.in",
        purchase_date=pdate,
        price=Decimal("54990"),
        source_type="email",
    )
    db.add(p)
    db.flush()
    db.add(
        WarrantyPeriod(
            purchase_id=p.id,
            warranty_end_date=pdate + timedelta(days=months * 30),
            return_window_end_date=pdate + timedelta(days=10),
            confidence_score="high",
            is_estimated=False,
        )
    )
    db.commit()
    return p


def in_memory_purchase(purchase_date, warranty_end, estimated=False):
    """A Purchase + WarrantyPeriod that never touches a database."""
    p = Purchase(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        product_name="Test TV",
        purchase_date=purchase_date,
        source_type="email",
    )
    if warranty_end is not None:
        p.warranty_period = WarrantyPeriod(
            purchase_id=p.id,
            warranty_end_date=warranty_end,
            confidence_score="high",
            is_estimated=estimated,
        )
    return p


def new_phone():
    return "91" + str(uuid.uuid4().int)[:10]


class FakeClient:
    """Stands in for WhatsAppClient: records replies, serves canned media."""

    def __init__(self, media=None, media_error=None):
        self.sent = []
        self._media = media or (b"%PDF-fake", "application/pdf")
        self._media_error = media_error

    def download_media(self, media_id):
        if self._media_error:
            raise self._media_error
        return self._media

    def send_text(self, to, body):
        self.sent.append((to, body))


def good_result(payment_text=None, name="Sony WH-1000XM5 Headphones"):
    return ExtractionResult(
        product_name=name,
        brand="Sony",
        retailer="Amazon.in",
        purchase_date=date.today() - timedelta(days=3),
        price=Decimal("26990"),
        warranty_period_months=12,
        return_window_days=10,
        confidence="high",
        source_snippet="Sony WH-1000XM5",
        payment_text=payment_text,
    )


# ── Card detection ───────────────────────────────────────────────────────────

class TestCardDetection:
    def test_issuer_and_last4(self):
        d = detect_payment_card("Payment Method: HDFC Bank Credit Card ending in 4021")
        assert d is not None
        assert d.issuer == "hdfc"
        assert d.last4 == "4021"
        assert d.card_key is None  # variant unknown

    def test_variant_detected(self):
        d = detect_payment_card("Paid using HDFC Regalia Credit Card XXXX1234 on 12 Oct")
        assert d.card_key == "hdfc_regalia"
        assert d.last4 == "1234"

    def test_axis_magnus(self):
        d = detect_payment_card("Payment: Axis Bank Magnus Credit Card **5566")
        assert d.issuer == "axis"
        assert d.card_key == "axis_magnus"
        assert d.last4 == "5566"

    def test_debit_card_ignored(self):
        assert detect_payment_card("Paid via HDFC Bank Debit Card ending 1111") is None

    def test_upi_and_cod_ignored(self):
        assert detect_payment_card("Payment Method: UPI") is None
        assert detect_payment_card("Cash on Delivery") is None
        assert detect_payment_card("") is None
        assert detect_payment_card(None) is None

    def test_earliest_mention_wins(self):
        text = "Amazon Pay ICICI Bank Credit Card was used. Offer also valid on HDFC Bank Credit Card."
        assert detect_payment_card(text).issuer == "icici"

    def test_variant_of_other_issuer_not_confused(self):
        # 'Reserve' belongs to Axis; an HDFC card must not pick it up.
        d = detect_payment_card("HDFC Bank Credit Card ending 9999 - Reserve Bank of India rules apply")
        assert d.issuer == "hdfc"
        assert d.card_key is None

    def test_multiline_text(self):
        d = detect_payment_card("Payment\nMethod:\nICICI Bank\nCredit Card\nending 7788")
        assert d.issuer == "icici"
        assert d.last4 == "7788"

    def test_charge_card_detected(self):
        d = detect_payment_card("Paid by American Express Platinum Charge Card ending 1002")
        assert d is not None
        assert d.issuer == "amex"
        assert d.card_key == "amex_platinum_charge"
        assert d.last4 == "1002"

    def test_llm_response_extracts_payment_method(self):
        from app.services.extractor_llm import _parse_llm_response

        raw = json.dumps(
            {
                "product_name": "Apple MacBook Air M3",
                "brand": "Apple",
                "retailer": "Amazon.in",
                "purchase_date": "2026-10-10",
                "price": 99900,
                "warranty_period_months": 12,
                "return_window_days": 10,
                "payment_method": "HDFC Regalia Credit Card ending 4321",
                "confidence": "high",
            }
        )
        res = _parse_llm_response(raw)
        assert res is not None
        assert res.payment_text == "HDFC Regalia Credit Card ending 4321"


# ── Benefit analysis ─────────────────────────────────────────────────────────

class TestBenefitAnalysis:
    def test_extended_warranty_dates(self):
        p = in_memory_purchase(date(2026, 1, 10), date(2027, 1, 10))
        b = analyze_card_benefit(p, "axis_magnus", "axis", today=TODAY)
        assert b.status == "extended_warranty"
        assert b.extension_months == 12
        assert b.manufacturer_warranty_end == "10 Jan 2027"
        assert b.extended_warranty_end == "10 Jan 2028"
        assert b.days_until_extended_end == (date(2028, 1, 10) - TODAY).days
        assert "may add" in b.headline
        assert b.claim_steps and b.conditions
        assert "confirm" in b.disclaimer.lower()

    def test_three_year_cap_trims_extension(self):
        p = in_memory_purchase(date(2026, 1, 1), date(2028, 7, 1))  # ~30 months
        b = analyze_card_benefit(p, "axis_reserve", "axis", today=TODAY)
        assert b.status == "extended_warranty"
        assert b.extension_months == 6

    def test_already_at_cap_not_eligible(self):
        p = in_memory_purchase(date(2026, 1, 1), date(2029, 1, 1))  # 36 months
        b = analyze_card_benefit(p, "axis_magnus", "axis", today=TODAY)
        assert b.status == "not_eligible"
        assert b.extension_months == 0

    def test_short_manufacturer_warranty_not_eligible(self):
        p = in_memory_purchase(date(2026, 1, 1), date(2026, 7, 1))  # 6 months
        b = analyze_card_benefit(p, "axis_magnus", "axis", today=TODAY)
        assert b.status == "not_eligible"
        assert "6 months" in b.headline

    def test_extension_already_over(self):
        p = in_memory_purchase(date(2023, 1, 1), date(2024, 1, 1))
        b = analyze_card_benefit(p, "axis_magnus", "axis", today=TODAY)
        assert b.status == "extended_warranty"
        assert b.days_until_extended_end < 0
        assert "ended" in b.headline

    def test_missing_dates_still_explains(self):
        p = in_memory_purchase(None, None)
        b = analyze_card_benefit(p, "axis_magnus", "axis", today=TODAY)
        assert b.status == "extended_warranty"
        assert b.extended_warranty_end is None
        assert "+12 months" in b.headline

    def test_estimated_warranty_is_flagged(self):
        p = in_memory_purchase(date(2026, 1, 10), date(2027, 1, 10), estimated=True)
        b = analyze_card_benefit(p, "axis_magnus", "axis", today=TODAY)
        assert "estimated" in b.headline

    def test_purchase_protection_only_card(self):
        p = in_memory_purchase(date(2026, 1, 10), date(2027, 1, 10))
        b = analyze_card_benefit(p, "hdfc_regalia", "hdfc", today=TODAY)
        assert b.status == "purchase_protection_only"
        assert b.extension_months == 0
        assert b.insurer == "HDFC ERGO General Insurance"
        assert "not an extended warranty" in b.headline

    def test_needs_card_with_and_without_issuer(self):
        p = in_memory_purchase(date(2026, 1, 10), date(2027, 1, 10))
        with_issuer = analyze_card_benefit(p, None, "hdfc", today=TODAY)
        assert with_issuer.status == "needs_card"
        assert "HDFC Bank" in with_issuer.headline
        assert analyze_card_benefit(p, None, None, today=TODAY).status == "needs_card"

    def test_other_and_unknown_card(self):
        p = in_memory_purchase(date(2026, 1, 10), date(2027, 1, 10))
        assert analyze_card_benefit(p, OTHER_CARD_KEY, "other").status == "no_known_benefit"
        assert analyze_card_benefit(p, "made_up_card", None).status == "no_known_benefit"

    def test_report_without_card_lists_options(self):
        p = in_memory_purchase(date(2026, 1, 10), date(2027, 1, 10))
        report = build_card_report(p, None, today=TODAY)
        assert report.detected_card is None
        assert report.benefit.status == "needs_card"
        keys = {o.key for o in report.options}
        assert {"axis_magnus", "hdfc_regalia", OTHER_CARD_KEY} <= keys


# ── Persistence helpers ──────────────────────────────────────────────────────

class TestCardPersistence:
    def test_record_then_update_detected(self, db):
        user = make_user(db)
        p = make_purchase(db, user)
        row = record_detected_card(db, p.id, "HDFC Bank Credit Card ending 4021")
        assert row.issuer == "hdfc" and row.last4 == "4021" and row.source == "detected"

        row2 = record_detected_card(db, p.id, "Axis Bank Magnus Credit Card ending 5566")
        assert row2.id == row.id
        assert row2.card_key == "axis_magnus" and row2.last4 == "5566"
        assert db.query(PurchasePaymentMethod).count() == 1

    def test_no_card_in_text_stores_nothing(self, db):
        user = make_user(db)
        p = make_purchase(db, user)
        assert record_detected_card(db, p.id, "Paid by UPI") is None
        assert get_payment_method(db, p.id) is None

    def test_manual_choice_is_never_overwritten(self, db):
        user = make_user(db)
        p = make_purchase(db, user)
        set_manual_card(db, p.id, "axis_magnus", "1234")
        record_detected_card(db, p.id, "HDFC Bank Credit Card ending 4021")
        row = get_payment_method(db, p.id)
        assert row.card_key == "axis_magnus" and row.source == "manual" and row.last4 == "1234"

    def test_manual_clear_and_invalid_key(self, db):
        user = make_user(db)
        p = make_purchase(db, user)
        set_manual_card(db, p.id, OTHER_CARD_KEY)
        assert get_payment_method(db, p.id).card_key == OTHER_CARD_KEY
        assert set_manual_card(db, p.id, None) is None
        assert get_payment_method(db, p.id) is None
        with pytest.raises(ValueError):
            set_manual_card(db, p.id, "not_a_card")

    def test_deleting_purchase_removes_card_row(self, db):
        user = make_user(db)
        p = make_purchase(db, user)
        set_manual_card(db, p.id, "axis_magnus")
        db.delete(p)
        db.commit()
        assert db.query(PurchasePaymentMethod).count() == 0

    def test_ingestion_records_card_automatically(self, db):
        from app.routers.ingestion import _persist_purchase

        user = make_user(db)
        result = good_result(payment_text="Payment: Axis Bank Magnus Credit Card ending 5566")
        purchase = _persist_purchase(db, user.id, result, source_type="email")
        row = get_payment_method(db, purchase.id)
        assert row is not None and row.card_key == "axis_magnus"


# ── WhatsApp: signature, parsing, helpers ────────────────────────────────────

SECRET = "topsecret"


def sign(body: bytes, secret=SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class TestWebhookPrimitives:
    def test_signature_valid_and_invalid(self):
        body = b'{"a":1}'
        assert verify_signature(body, sign(body), SECRET)
        assert not verify_signature(body, sign(body, "other"), SECRET)
        assert not verify_signature(b'{"a":2}', sign(body), SECRET)
        assert not verify_signature(body, None, SECRET)
        assert not verify_signature(body, "sha1=abc", SECRET)
        assert not verify_signature(body, sign(body), "")

    def test_parse_text_and_media(self):
        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {"id": "m1", "from": "919876543210", "type": "text", "text": {"body": "hello"}},
                                    {
                                        "id": "m2",
                                        "from": "919876543210",
                                        "type": "image",
                                        "image": {"id": "media1", "mime_type": "image/jpeg", "caption": "bill"},
                                    },
                                    {
                                        "id": "m3",
                                        "from": "919876543210",
                                        "type": "document",
                                        "document": {"id": "media2", "mime_type": "application/pdf", "filename": "inv.pdf"},
                                    },
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        msgs = parse_webhook_payload(payload)
        assert [m.type for m in msgs] == ["text", "image", "document"]
        assert msgs[0].text == "hello"
        assert msgs[1].media_id == "media1" and msgs[1].caption == "bill"
        assert msgs[2].filename == "inv.pdf"

    def test_parse_ignores_status_updates_and_garbage(self):
        assert parse_webhook_payload({"entry": [{"changes": [{"value": {"statuses": [{"id": "x"}]}}]}]}) == []
        assert parse_webhook_payload({}) == []
        assert parse_webhook_payload({"entry": [{"changes": [{"value": {"messages": [{"type": "text"}]}}]}]}) == []

    def test_mask_phone(self):
        assert mask_phone("919876543210") == "+91 ••••••3210"
        assert mask_phone("123") is None
        assert mask_phone(None) is None

    def test_sliding_window_limiter(self):
        lim = SlidingWindowLimiter(limit=2, window_seconds=10)
        assert lim.allow("a", now=0) and lim.allow("a", now=1)
        assert not lim.allow("a", now=2)
        assert lim.allow("b", now=2)  # separate key
        assert lim.allow("a", now=12)  # window slid

    def test_seen_message_ids(self):
        seen = SeenMessageIds(max_size=2)
        assert not seen.seen_before("a")
        assert seen.seen_before("a")
        seen.seen_before("b")
        seen.seen_before("c")  # evicts 'a'
        assert not seen.seen_before("a")


# ── WhatsApp: account linking ────────────────────────────────────────────────

class TestLinking:
    def test_code_links_phone(self, db):
        user = make_user(db)
        code, expires = create_link_code(db, user)
        assert len(code) == 6 and expires > datetime.utcnow()
        phone = new_phone()
        assert link_phone_with_code(db, phone, code).id == user.id
        assert get_user_by_phone(db, phone).id == user.id
        # single use
        assert link_phone_with_code(db, new_phone(), code) is None

    def test_code_is_case_insensitive(self, db):
        user = make_user(db)
        code, _ = create_link_code(db, user)
        assert link_phone_with_code(db, new_phone(), code.lower()) is not None

    def test_expired_code_rejected(self, db):
        user = make_user(db)
        code, _ = create_link_code(db, user)
        link = db.query(WhatsAppLink).filter_by(user_id=user.id).one()
        link.link_code_expires_at = datetime.utcnow() - timedelta(minutes=1)
        db.commit()
        assert link_phone_with_code(db, new_phone(), code) is None

    def test_number_moves_between_accounts(self, db):
        a, b = make_user(db), make_user(db)
        phone = new_phone()
        link_phone_with_code(db, phone, create_link_code(db, a)[0])
        link_phone_with_code(db, phone, create_link_code(db, b)[0])
        assert get_user_by_phone(db, phone).id == b.id
        assert db.query(WhatsAppLink).filter_by(user_id=a.id).one().phone_number is None

    def test_new_code_replaces_old(self, db):
        user = make_user(db)
        old, _ = create_link_code(db, user)
        new, _ = create_link_code(db, user)
        assert db.query(WhatsAppLink).count() == 1
        if old != new:
            assert link_phone_with_code(db, new_phone(), old) is None


# ── WhatsApp: conversation flows ─────────────────────────────────────────────

def text_msg(phone, text, mid=None):
    return IncomingMessage(message_id=mid or uuid.uuid4().hex, from_number=phone, type="text", text=text)


def linked_user(db):
    user = make_user(db)
    phone = new_phone()
    link_phone_with_code(db, phone, create_link_code(db, user)[0])
    return user, phone


class TestBotConversations:
    def test_unlinked_number_gets_instructions_and_nothing_is_saved(self, db, monkeypatch):
        called = []
        monkeypatch.setattr(whatsapp_bot, "_run_extraction_pipeline", lambda *a, **k: called.append(1))
        client = FakeClient()
        reply = process_incoming(db, text_msg(new_phone(), "Order: Sony headphones from Amazon on 3 Nov for Rs 26990 warranty 1 year"), client)
        assert "LINK" in reply and "Upload" in reply
        assert called == []
        assert db.query(Purchase).count() == 0
        assert client.sent and client.sent[0][1] == reply

    def test_link_command_flow(self, db):
        user = make_user(db, "nikita@example.com")
        code, _ = create_link_code(db, user)
        phone = new_phone()
        client = FakeClient()
        reply = process_incoming(db, text_msg(phone, f"link {code}"), client)
        assert "Linked to nikita@example.com" in reply
        assert get_user_by_phone(db, phone).id == user.id

    def test_bad_link_code(self, db):
        reply = process_incoming(db, text_msg(new_phone(), "LINK ZZZZZZ"), FakeClient())
        assert "invalid or has expired" in reply

    def test_link_attempts_are_rate_limited(self, db):
        phone = new_phone()
        replies = [process_incoming(db, text_msg(phone, "LINK ZZZZZZ"), FakeClient()) for _ in range(7)]
        assert "invalid or has expired" in replies[0]
        assert "Too many link attempts" in replies[-1]

    def test_help_and_short_text(self, db):
        _, phone = linked_user(db)
        assert "LIST" in process_incoming(db, text_msg(phone, "hi"), FakeClient())
        assert "LIST" in process_incoming(db, text_msg(phone, "ok thanks"), FakeClient())

    def test_text_bill_is_saved_with_whatsapp_source(self, db, monkeypatch):
        user, phone = linked_user(db)
        monkeypatch.setattr(whatsapp_bot, "_run_extraction_pipeline", lambda text, **k: good_result())
        reply = process_incoming(
            db, text_msg(phone, "Order confirmed: Sony WH-1000XM5 from Amazon.in, Rs 26,990, 1 year warranty"), FakeClient()
        )
        assert "Saved to your vault" in reply
        assert "Sony WH-1000XM5" in reply
        assert "day(s) left" in reply
        p = db.query(Purchase).filter_by(user_id=user.id).one()
        assert p.source_type == "whatsapp"

    def test_same_bill_twice_does_not_duplicate(self, db, monkeypatch):
        user, phone = linked_user(db)
        monkeypatch.setattr(whatsapp_bot, "_run_extraction_pipeline", lambda text, **k: good_result())
        msg = "Order confirmed: Sony WH-1000XM5 from Amazon.in, Rs 26,990, 1 year warranty"
        process_incoming(db, text_msg(phone, msg), FakeClient())
        reply = process_incoming(db, text_msg(phone, msg), FakeClient())
        assert "Already in your vault" in reply
        assert db.query(Purchase).filter_by(user_id=user.id).count() == 1

    def test_unreadable_text_is_politely_rejected(self, db, monkeypatch):
        user, phone = linked_user(db)
        monkeypatch.setattr(
            whatsapp_bot, "_run_extraction_pipeline", lambda text, **k: ExtractionResult(confidence="low")
        )
        reply = process_incoming(
            db, text_msg(phone, "just some long chatter that is clearly not a bill at all"), FakeClient()
        )
        assert "couldn't find a product" in reply
        assert db.query(Purchase).count() == 0

    def test_card_benefit_mentioned_in_reply(self, db, monkeypatch):
        _, phone = linked_user(db)
        result = good_result(payment_text="Payment: Axis Bank Magnus Credit Card ending 5566")
        monkeypatch.setattr(whatsapp_bot, "_run_extraction_pipeline", lambda text, **k: result)
        reply = process_incoming(
            db, text_msg(phone, "Order confirmed: Sony WH-1000XM5 from Amazon.in, Rs 26,990, 1 year warranty"), FakeClient()
        )
        assert "Axis Bank Magnus" in reply and "+12 months" in reply

    def test_card_variant_prompt_when_only_issuer_known(self, db, monkeypatch):
        _, phone = linked_user(db)
        result = good_result(payment_text="Payment Method: HDFC Bank Credit Card ending in 4021")
        monkeypatch.setattr(whatsapp_bot, "_run_extraction_pipeline", lambda text, **k: result)
        reply = process_incoming(
            db, text_msg(phone, "Order confirmed: Sony WH-1000XM5 from Amazon.in, Rs 26,990, 1 year warranty"), FakeClient()
        )
        assert "HDFC Bank credit card" in reply and "pick your card" in reply

    def test_list_command(self, db, monkeypatch):
        user, phone = linked_user(db)
        assert "empty" in process_incoming(db, text_msg(phone, "LIST"), FakeClient())
        make_purchase(db, user, "LG Fridge", months=12)
        reply = process_incoming(db, text_msg(phone, "list"), FakeClient())
        assert "LG Fridge" in reply and "day(s) left" in reply

    def test_unlink_command(self, db):
        user, phone = linked_user(db)
        process_incoming(db, text_msg(phone, "UNLINK"), FakeClient())
        assert get_user_by_phone(db, phone) is None

    def test_image_bill_flow(self, db, monkeypatch):
        user, phone = linked_user(db)
        seen = {}

        def fake_process(data, filename, content_type):
            seen.update(filename=filename, content_type=content_type, size=len(data))
            return "uploads/x.jpg", "x.jpg", good_result(), True

        monkeypatch.setattr(whatsapp_bot, "process_file_bytes", fake_process)
        msg = IncomingMessage(
            message_id="wamid.ABCDEFGH12345678", from_number=phone, type="image",
            media_id="m1", mime_type="image/jpeg",
        )
        reply = process_incoming(db, msg, FakeClient(media=(b"jpegbytes", "image/jpeg")))
        assert "Saved to your vault" in reply
        assert seen["content_type"] == "image/jpeg" and seen["filename"].endswith(".jpg")
        assert db.query(Purchase).filter_by(user_id=user.id).one().source_file_ref == "uploads/x.jpg"

    def test_unsupported_media_type(self, db):
        _, phone = linked_user(db)
        msg = IncomingMessage(message_id="m9", from_number=phone, type="document", media_id="m", mime_type="application/zip")
        assert "photos" in process_incoming(db, msg, FakeClient())
        audio = IncomingMessage(message_id="m10", from_number=phone, type="audio")
        assert "photos" in process_incoming(db, audio, FakeClient())

    def test_media_download_failure_is_reported(self, db):
        _, phone = linked_user(db)
        msg = IncomingMessage(message_id="m11", from_number=phone, type="image", media_id="m", mime_type="image/png")
        reply = process_incoming(db, msg, FakeClient(media_error=WhatsAppError("File is larger than the 20 MB limit.")))
        assert reply.startswith("⚠️") and "20 MB" in reply

    def test_unexpected_error_still_answers(self, db, monkeypatch):
        _, phone = linked_user(db)

        def boom(*a, **k):
            raise RuntimeError("gemini exploded")

        monkeypatch.setattr(whatsapp_bot, "_run_extraction_pipeline", boom)
        client = FakeClient()
        reply = process_incoming(
            db, text_msg(phone, "Order confirmed: Sony WH-1000XM5 from Amazon.in, Rs 26,990, 1 year warranty"), client
        )
        assert "something went wrong" in reply
        assert client.sent  # the user still got a reply


# ── HTTP routes (direct handler calls; avoids asyncio socketpair in sandbox) ─

class _FakeRequest:
    def __init__(
        self,
        raw_body: bytes,
        headers: dict[str, str] | None = None,
        url: str = "https://warranty-agent.onrender.com/whatsapp/twilio-webhook",
    ):
        self._body = raw_body
        self.headers = Headers(headers or {})
        self.url = URL(url)

    async def body(self) -> bytes:
        return self._body


def _run_coro(coro):
    """Drive a coroutine without creating an asyncio ProactorEventLoop."""
    try:
        coro.send(None)
    except StopIteration as exc:
        return exc.value
    raise AssertionError("Coroutine suspended unexpectedly")


@pytest.fixture()
def wa_env(monkeypatch):
    for key, value in {
        "WHATSAPP_ACCESS_TOKEN": "tok",
        "WHATSAPP_PHONE_NUMBER_ID": "123",
        "WHATSAPP_APP_SECRET": SECRET,
        "WHATSAPP_VERIFY_TOKEN": "verify-me",
        "WHATSAPP_BOT_NUMBER": "+91 90000 00000",
    }.items():
        monkeypatch.setenv(key, value)


class TestWhatsAppRoutes:
    def test_routes_registered_on_app(self):
        from main import app

        route_methods: dict[str, set[str]] = {}
        for route in app.routes:
            path = getattr(route, "path", None)
            methods = getattr(route, "methods", None) or set()
            if path:
                route_methods.setdefault(path, set()).update(methods)

        assert {"GET", "POST"} <= route_methods.get("/whatsapp/webhook", set())
        assert "POST" in route_methods.get("/whatsapp/twilio-webhook", set())
        assert "GET" in route_methods.get("/whatsapp/status", set())
        assert "POST" in route_methods.get("/whatsapp/link-code", set())
        assert "DELETE" in route_methods.get("/whatsapp/link", set())
        assert "GET" in route_methods.get("/purchases/{purchase_id}/card-benefits", set())
        assert "PUT" in route_methods.get("/purchases/{purchase_id}/payment-card", set())

    def test_webhook_verification(self, wa_env):
        from app.routers.whatsapp import verify_webhook

        ok = verify_webhook(hub_mode="subscribe", hub_challenge="1234", hub_verify_token="verify-me")
        assert ok.status_code == 200 and ok.body == b"1234"
        with pytest.raises(HTTPException) as exc:
            verify_webhook(hub_mode="subscribe", hub_challenge="1234", hub_verify_token="nope")
        assert exc.value.status_code == 403

    def test_webhook_rejects_bad_signature(self, wa_env):
        from app.routers.whatsapp import receive_webhook

        body = json.dumps({"entry": []}).encode()
        with pytest.raises(HTTPException) as exc1:
            _run_coro(receive_webhook(_FakeRequest(body), BackgroundTasks()))
        assert exc1.value.status_code == 403
        with pytest.raises(HTTPException) as exc2:
            _run_coro(
                receive_webhook(
                    _FakeRequest(body, {"X-Hub-Signature-256": "sha256=deadbeef"}),
                    BackgroundTasks(),
                )
            )
        assert exc2.value.status_code == 403

    def test_webhook_503_when_not_configured(self, wa_env, monkeypatch):
        from app.routers.whatsapp import receive_webhook

        monkeypatch.delenv("WHATSAPP_APP_SECRET")
        with pytest.raises(HTTPException) as exc:
            _run_coro(receive_webhook(_FakeRequest(b"{}"), BackgroundTasks()))
        assert exc.value.status_code == 503

    def test_webhook_dispatches_each_message_once(self, wa_env, monkeypatch):
        from app.routers import whatsapp as wa_router

        handled = []
        monkeypatch.setattr(wa_router, "_handle_in_background", lambda msg: handled.append(msg.message_id))
        mid = "wamid." + uuid.uuid4().hex
        body = json.dumps(
            {
                "entry": [
                    {
                        "changes": [
                            {
                                "value": {
                                    "messages": [
                                        {
                                            "id": mid,
                                            "from": "919876543210",
                                            "type": "text",
                                            "text": {"body": "hi"},
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ]
            }
        ).encode()
        headers = {"X-Hub-Signature-256": sign(body)}

        bg1 = BackgroundTasks()
        res1 = _run_coro(wa_router.receive_webhook(_FakeRequest(body, headers), bg1))
        assert res1 == {"status": "received"}
        assert len(bg1.tasks) == 1
        for task in bg1.tasks:
            task.func(*task.args, **task.kwargs)

        bg2 = BackgroundTasks()
        res2 = _run_coro(wa_router.receive_webhook(_FakeRequest(body, headers), bg2))
        assert res2 == {"status": "received"}
        assert bg2.tasks == []  # Meta retry ignored
        assert handled == [mid]

    def test_webhook_invalid_json(self, wa_env):
        from app.routers.whatsapp import receive_webhook

        body = b"not json"
        with pytest.raises(HTTPException) as exc:
            _run_coro(
                receive_webhook(
                    _FakeRequest(body, {"X-Hub-Signature-256": sign(body)}),
                    BackgroundTasks(),
                )
            )
        assert exc.value.status_code == 400

    def test_status_link_code_and_unlink(self, db, wa_env):
        from app.routers.whatsapp import delete_link, new_link_code, whatsapp_status

        user = make_user(db)
        status = whatsapp_status(user_id=user.id, db=db)
        assert status.configured is True and status.linked is False
        assert status.bot_number == "919000000000"

        code = new_link_code(user_id=user.id, db=db)
        assert len(code.code) == 6 and code.expires_in_minutes == 15
        assert code.deep_link.startswith("https://wa.me/919000000000?text=LINK%20")
        assert whatsapp_status(user_id=user.id, db=db).pending_code is True

        link_phone_with_code(db, "919876543210", code.code)
        status = whatsapp_status(user_id=user.id, db=db)
        assert status.linked is True and status.phone_masked.endswith("3210")

        resp = delete_link(user_id=user.id, db=db)
        assert resp.status_code == 204
        assert whatsapp_status(user_id=user.id, db=db).linked is False

    def test_link_code_503_when_not_configured(self, db, wa_env, monkeypatch):
        from app.routers.whatsapp import new_link_code

        user = make_user(db)
        monkeypatch.delenv("WHATSAPP_ACCESS_TOKEN")
        with pytest.raises(HTTPException) as exc:
            new_link_code(user_id=user.id, db=db)
        assert exc.value.status_code == 503

    def test_unknown_user_404(self, db, wa_env):
        from app.routers.whatsapp import whatsapp_status

        with pytest.raises(HTTPException) as exc:
            whatsapp_status(user_id=uuid.uuid4(), db=db)
        assert exc.value.status_code == 404


class TestCardBenefitRoutes:
    def test_get_put_roundtrip(self, db):
        from app.routers.card_benefits import get_card_benefits, put_payment_card
        from app.schemas import PaymentCardRequest

        user = make_user(db)
        purchase = make_purchase(db, user, months=12)

        first = get_card_benefits(purchase_id=purchase.id, user_id=user.id, db=db)
        assert first.detected_card is None
        assert first.benefit.status == "needs_card"
        assert any(o.key == "axis_magnus" for o in first.options)

        put = put_payment_card(
            purchase_id=purchase.id,
            body=PaymentCardRequest(user_id=user.id, card_key="axis_magnus", last4="5566"),
            db=db,
        )
        assert put.detected_card.source == "manual"
        assert put.detected_card.last4 == "5566"
        assert put.benefit.status == "extended_warranty"
        assert put.benefit.extension_months == 12

        again = get_card_benefits(purchase_id=purchase.id, user_id=user.id, db=db)
        assert again.benefit.status == "extended_warranty"

        cleared = put_payment_card(
            purchase_id=purchase.id,
            body=PaymentCardRequest(user_id=user.id, card_key=None),
            db=db,
        )
        assert cleared.detected_card is None and cleared.benefit.status == "needs_card"

    def test_invalid_card_and_foreign_user(self, db):
        from app.routers.card_benefits import get_card_benefits, put_payment_card
        from app.schemas import PaymentCardRequest

        owner, other = make_user(db), make_user(db)
        purchase = make_purchase(db, owner)

        with pytest.raises(HTTPException) as exc:
            put_payment_card(
                purchase_id=purchase.id,
                body=PaymentCardRequest(user_id=owner.id, card_key="nope"),
                db=db,
            )
        assert exc.value.status_code == 422

        with pytest.raises(ValidationError):
            PaymentCardRequest(user_id=owner.id, card_key="axis_magnus", last4="12")

        # another user must not read or change this purchase
        with pytest.raises(HTTPException) as exc_get:
            get_card_benefits(purchase_id=purchase.id, user_id=other.id, db=db)
        assert exc_get.value.status_code == 404

        with pytest.raises(HTTPException) as exc_put:
            put_payment_card(
                purchase_id=purchase.id,
                body=PaymentCardRequest(user_id=other.id, card_key="axis_magnus"),
                db=db,
            )
        assert exc_put.value.status_code == 404


# ── Proactive WhatsApp expiry alerts ─────────────────────────────────────────

class TestProactiveWhatsAppAlerts:
    def _setup_due_alert(self, db, user, alert_type="warranty_expiry"):
        purchase = make_purchase(db, user, "Sony Bravia 55 TV", months=12)
        alert = Alert(
            id=uuid.uuid4(),
            purchase_id=purchase.id,
            alert_type=alert_type,
            fire_date=datetime.utcnow() - timedelta(hours=1),
            sent=False,
        )
        db.add(alert)
        db.commit()
        return purchase, alert

    def test_daily_alert_notifies_linked_whatsapp_with_card_hint(self, db, wa_env, monkeypatch):
        user, phone = linked_user(db)
        purchase, alert = self._setup_due_alert(db, user, "warranty_expiry")
        alert_id = alert.id
        set_manual_card(db, purchase.id, "axis_magnus")

        fake = FakeClient()
        monkeypatch.setattr(alert_engine, "SessionLocal", lambda: db)
        monkeypatch.setattr(whatsapp_client.WhatsAppClient, "from_env", classmethod(lambda cls: fake))

        alert_engine.run_daily_alert_check()

        assert len(fake.sent) == 1
        to, text = fake.sent[0]
        assert to == phone
        assert "Sony Bravia 55 TV" in text
        assert "Axis Bank Magnus" in text and "+12 months" in text
        assert db.query(Alert).filter_by(id=alert_id).one().sent is True

    def test_daily_alert_skips_when_unconfigured_or_unlinked(self, db, monkeypatch):
        user = make_user(db)
        _, alert = self._setup_due_alert(db, user, "return_window_expiry")
        alert_id = alert.id

        fake = FakeClient()
        monkeypatch.delenv("WHATSAPP_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
        monkeypatch.setattr(alert_engine, "SessionLocal", lambda: db)
        monkeypatch.setattr(whatsapp_client.WhatsAppClient, "from_env", classmethod(lambda cls: fake))

        alert_engine.run_daily_alert_check()
        assert fake.sent == []
        assert db.query(Alert).filter_by(id=alert_id).one().sent is True

    def test_daily_alert_notifies_via_twilio_when_configured(self, db, twilio_env, monkeypatch):
        user, phone = linked_user(db)
        _, alert = self._setup_due_alert(db, user, "return_window_expiry")
        alert_id = alert.id

        fake = FakeClient()
        monkeypatch.setattr(alert_engine, "SessionLocal", lambda: db)
        monkeypatch.setattr(
            whatsapp_client.TwilioWhatsAppClient, "from_env", classmethod(lambda cls: fake)
        )

        alert_engine.run_daily_alert_check()
        assert len(fake.sent) == 1
        assert fake.sent[0][0] == phone
        assert "Sony Bravia 55 TV" in fake.sent[0][1]
        assert db.query(Alert).filter_by(id=alert_id).one().sent is True


# ── Twilio WhatsApp Sandbox support ──────────────────────────────────────────

TWILIO_SID = "AC00000000000000000000000000000001"
TWILIO_TOKEN = "twilio_auth_secret_token"


def sign_twilio(url: str, params: dict[str, str], token: str = TWILIO_TOKEN) -> str:
    payload = url + "".join(f"{k}{v}" for k, v in sorted(params.items(), key=lambda kv: kv[0]))
    digest = hmac.new(token.encode("utf-8"), payload.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("ascii")


@pytest.fixture()
def twilio_env(monkeypatch):
    for key in (
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_PHONE_NUMBER_ID",
        "WHATSAPP_APP_SECRET",
        "WHATSAPP_VERIFY_TOKEN",
        "WHATSAPP_PROVIDER",
        "TWILIO_WEBHOOK_URL",
        "TWILIO_WHATSAPP_NUMBER",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", TWILIO_SID)
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", TWILIO_TOKEN)
    monkeypatch.setenv("TWILIO_SANDBOX_JOIN_CODE", "join quick-tiger")


class TestTwilioSupport:
    def test_twilio_signature_verification(self):
        url = "https://warranty-agent.onrender.com/whatsapp/twilio-webhook"
        params = {"Body": "hello", "From": "whatsapp:+919876543210", "To": "whatsapp:+14155238886"}
        sig = sign_twilio(url, params)

        assert whatsapp_client.verify_twilio_signature(url, params, sig, TWILIO_TOKEN)
        # parameter insertion order must not affect signature (keys are sorted)
        reordered = {"To": params["To"], "Body": params["Body"], "From": params["From"]}
        assert whatsapp_client.verify_twilio_signature(url, reordered, sig, TWILIO_TOKEN)
        assert not whatsapp_client.verify_twilio_signature(
            url, {**params, "Body": "tampered"}, sig, TWILIO_TOKEN
        )
        assert not whatsapp_client.verify_twilio_signature(url, params, sig, "wrong_token")
        assert not whatsapp_client.verify_twilio_signature(url, params, None, TWILIO_TOKEN)

    def test_parse_twilio_payload_variants(self):
        text_msg = whatsapp_bot.parse_twilio_payload(
            {"MessageSid": "SM1", "From": "whatsapp:+919876543210", "Body": "LIST", "NumMedia": "0"}
        )
        assert text_msg and text_msg.type == "text" and text_msg.text == "LIST"
        assert text_msg.from_number == "919876543210"

        img_msg = whatsapp_bot.parse_twilio_payload(
            {
                "MessageSid": "SM2",
                "From": "whatsapp:+919876543210",
                "Body": "TV bill",
                "NumMedia": "1",
                "MediaUrl0": "https://api.twilio.com/media/ME1",
                "MediaContentType0": "image/jpeg",
            }
        )
        assert img_msg and img_msg.type == "image" and img_msg.caption == "TV bill"
        assert img_msg.media_id == "https://api.twilio.com/media/ME1"

        pdf_msg = whatsapp_bot.parse_twilio_payload(
            {
                "MessageSid": "SM3",
                "From": "whatsapp:+919876543210",
                "NumMedia": "1",
                "MediaUrl0": "https://api.twilio.com/media/ME2",
                "MediaContentType0": "application/pdf",
            }
        )
        assert pdf_msg and pdf_msg.type == "document" and pdf_msg.mime_type == "application/pdf"

        assert whatsapp_bot.parse_twilio_payload({}) is None
        assert whatsapp_bot.parse_twilio_payload({"MessageSid": "SM4"}) is None

    def test_twilio_client_send_truncation_and_media_safety(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["auth"] = request.headers.get("Authorization")
            if request.method == "POST":
                captured["body"] = request.content.decode("utf-8")
                return httpx.Response(201, json={"sid": "SM_OUT"})
            if "huge" in str(request.url):
                return httpx.Response(
                    200,
                    content=b"x" * (whatsapp_client.MAX_MEDIA_BYTES + 1),
                    headers={"content-type": "application/pdf"},
                )
            return httpx.Response(200, content=b"%PDF-1.4", headers={"content-type": "application/pdf"})

        http = httpx.Client(transport=httpx.MockTransport(handler))
        client = whatsapp_client.TwilioWhatsAppClient(TWILIO_SID, TWILIO_TOKEN, "14155238886", http=http)

        # send_text: Basic Auth, whatsapp:+ prefix, and 1600-char truncation
        long_reply = "A" * 2000
        client.send_text("919876543210", long_reply)
        assert captured["auth"].startswith("Basic ")
        assert "whatsapp%3A%2B919876543210" in captured["body"]
        assert "A" * 1580 in captured["body"] and "A" * 1591 not in captured["body"]

        # download_media: success + >20 MB rejection + non-Twilio SSRF rejection
        data, mime = client.download_media("https://api.twilio.com/2010-04-01/Accounts/AC/Messages/MM/Media/ME")
        assert data == b"%PDF-1.4" and mime == "application/pdf"

        with pytest.raises(WhatsAppError, match="20 MB"):
            client.download_media("https://api.twilio.com/2010-04-01/Accounts/huge")

        with pytest.raises(WhatsAppError, match="Untrusted"):
            client.download_media("https://evil.example.com/steal-creds")

    def test_twilio_webhook_routes_and_proxy_verification(self, twilio_env, monkeypatch):
        from app.routers import whatsapp as wa_router

        params = {
            "MessageSid": "SM_" + uuid.uuid4().hex,
            "From": "whatsapp:+919876543210",
            "Body": "hi",
            "NumMedia": "0",
        }
        raw = urlencode(params).encode("utf-8")

        # 403 when signature missing or wrong
        with pytest.raises(HTTPException) as bad:
            _run_coro(
                wa_router.receive_twilio_webhook(
                    _FakeRequest(raw, {"X-Twilio-Signature": "wrong"}), BackgroundTasks()
                )
            )
        assert bad.value.status_code == 403

        # Proxy URL reconstruction: local URL is http://, Twilio signed https:// via proxy
        signed_url = "https://warranty-agent.onrender.com/whatsapp/twilio-webhook"
        sig = sign_twilio(signed_url, params)
        proxy_req = _FakeRequest(
            raw,
            headers={
                "X-Twilio-Signature": sig,
                "X-Forwarded-Proto": "https",
                "Host": "warranty-agent.onrender.com",
            },
            url="http://127.0.0.1:8000/whatsapp/twilio-webhook",
        )
        handled = []
        monkeypatch.setattr(
            wa_router, "_handle_twilio_in_background", lambda m: handled.append(m.message_id)
        )

        bg = BackgroundTasks()
        res = _run_coro(wa_router.receive_twilio_webhook(proxy_req, bg))
        assert res.status_code == 200 and res.body == b"<Response/>"
        assert len(bg.tasks) == 1
        for task in bg.tasks:
            task.func(*task.args, **task.kwargs)

        # Duplicate retry is ignored
        bg_retry = BackgroundTasks()
        _run_coro(wa_router.receive_twilio_webhook(proxy_req, bg_retry))
        assert bg_retry.tasks == []
        assert handled == [params["MessageSid"]]

        # 503 when unconfigured
        monkeypatch.delenv("TWILIO_AUTH_TOKEN")
        with pytest.raises(HTTPException) as uncfg:
            _run_coro(wa_router.receive_twilio_webhook(_FakeRequest(raw), BackgroundTasks()))
        assert uncfg.value.status_code == 503

    def test_status_and_link_code_include_twilio_sandbox_info(self, db, twilio_env):
        from app.routers.whatsapp import new_link_code, whatsapp_status

        user = make_user(db)
        status = whatsapp_status(user_id=user.id, db=db)
        assert status.configured is True
        assert status.provider == "twilio"
        assert status.bot_number == "14155238886"
        assert status.sandbox_join_code == "join quick-tiger"
        assert status.sandbox_join_link == "https://wa.me/14155238886?text=join%20quick-tiger"

        code = new_link_code(user_id=user.id, db=db)
        assert code.provider == "twilio"
        assert code.bot_number == "14155238886"
        assert code.sandbox_join_code == "join quick-tiger"
        assert code.sandbox_join_link == "https://wa.me/14155238886?text=join%20quick-tiger"
        assert code.deep_link.startswith("https://wa.me/14155238886?text=LINK%20")

