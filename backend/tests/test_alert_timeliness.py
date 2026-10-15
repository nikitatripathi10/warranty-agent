"""
Milestone 4 — Alert Timeliness Tests (pytest)

Tests the alert engine for:
  1. Correct alert creation (return_window, warranty_expiry types)
  2. Timeliness — alert fire_date is set to exactly N days before deadline
  3. Idempotency — calling create_alerts twice doesn't create duplicates
  4. Overdue detection — `get_upcoming_alerts` correctly flags is_overdue
  5. Daily check marks due alerts as sent

All tests use SQLite in-memory DB (no PostgreSQL required).

Run:
    cd backend
    venv\\Scripts\\pytest tests/test_alert_timeliness.py -v --tb=short
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Alert, Purchase, User, WarrantyPeriod
from app.services.alert_engine import (
    RETURN_WINDOW_LEAD_DAYS,
    WARRANTY_EXPIRY_LEAD_DAYS,
    backfill_alerts_for_user,
    create_alerts_for_purchase,
    get_upcoming_alerts,
    run_daily_alert_check,
)


# ── In-memory SQLite fixtures ─────────────────────────────────────────────────

@pytest.fixture(scope="module")
def engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    # SQLite doesn't enforce FK constraints by default
    @event.listens_for(eng, "connect")
    def enable_fk(dbapi_con, _):
        dbapi_con.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def db(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture()
def test_user(db):
    user = User(
        id=uuid.uuid4(),
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        google_oauth_token_encrypted="fake_encrypted_token",
    )
    db.add(user)
    db.commit()
    return user


def _make_purchase(db, user_id, product_name="Test Product"):
    p = Purchase(
        id=uuid.uuid4(),
        user_id=user_id,
        product_name=product_name,
        brand="TestBrand",
        retailer="Amazon",
        purchase_date=date.today() - timedelta(days=5),
        price=Decimal("9999"),
        source_type="email",
    )
    db.add(p)
    db.commit()
    return p


def _make_warranty(db, purchase_id, warranty_end_offset_days=365, return_end_offset_days=30):
    today = date.today()
    wp = WarrantyPeriod(
        id=uuid.uuid4(),
        purchase_id=purchase_id,
        warranty_end_date=today + timedelta(days=warranty_end_offset_days),
        return_window_end_date=today + timedelta(days=return_end_offset_days),
        confidence_score="high",
        is_estimated=False,
    )
    db.add(wp)
    db.commit()
    return wp


# ── Alert creation tests ──────────────────────────────────────────────────────

class TestAlertCreation:

    def test_creates_return_window_alert(self, db, test_user):
        """A purchase with a return window should get a return_window_expiry alert."""
        purchase = _make_purchase(db, test_user.id)
        warranty = _make_warranty(db, purchase.id, return_end_offset_days=10)

        created = create_alerts_for_purchase(db, purchase, warranty)

        assert created >= 1
        alert = db.query(Alert).filter(
            Alert.purchase_id == purchase.id,
            Alert.alert_type == "return_window_expiry"
        ).first()
        assert alert is not None

    def test_creates_warranty_expiry_alert(self, db, test_user):
        """A purchase with a warranty end date should get a warranty_expiry alert."""
        purchase = _make_purchase(db, test_user.id)
        warranty = _make_warranty(db, purchase.id, warranty_end_offset_days=60)

        create_alerts_for_purchase(db, purchase, warranty)

        alert = db.query(Alert).filter(
            Alert.purchase_id == purchase.id,
            Alert.alert_type == "warranty_expiry"
        ).first()
        assert alert is not None

    def test_creates_both_alerts(self, db, test_user):
        """A purchase with both dates should get two alerts."""
        purchase = _make_purchase(db, test_user.id)
        warranty = _make_warranty(db, purchase.id)

        created = create_alerts_for_purchase(db, purchase, warranty)

        assert created == 2

    def test_no_alerts_for_no_warranty(self, db, test_user):
        """A purchase with no warranty period should create zero alerts."""
        purchase = _make_purchase(db, test_user.id)
        created = create_alerts_for_purchase(db, purchase, None)
        assert created == 0


# ── Alert timeliness tests ────────────────────────────────────────────────────

class TestAlertTimeliness:

    def test_return_window_fire_date_is_correct(self, db, test_user):
        """
        Return window alert must fire exactly RETURN_WINDOW_LEAD_DAYS before
        the return window end date.
        """
        return_days = 14  # 14 days from today
        purchase = _make_purchase(db, test_user.id)
        warranty = _make_warranty(db, purchase.id, return_end_offset_days=return_days)
        create_alerts_for_purchase(db, purchase, warranty)

        alert = db.query(Alert).filter(
            Alert.purchase_id == purchase.id,
            Alert.alert_type == "return_window_expiry"
        ).first()

        expected_fire = (
            warranty.return_window_end_date - timedelta(days=RETURN_WINDOW_LEAD_DAYS)
        )
        assert alert.fire_date.date() == expected_fire, (
            f"fire_date={alert.fire_date.date()} expected={expected_fire} "
            f"(deadline={warranty.return_window_end_date}, lead={RETURN_WINDOW_LEAD_DAYS}d)"
        )

    def test_warranty_expiry_fire_date_is_correct(self, db, test_user):
        """
        Warranty expiry alert must fire exactly WARRANTY_EXPIRY_LEAD_DAYS before
        the warranty end date.
        """
        warranty_days = 365
        purchase = _make_purchase(db, test_user.id)
        warranty = _make_warranty(db, purchase.id, warranty_end_offset_days=warranty_days)
        create_alerts_for_purchase(db, purchase, warranty)

        alert = db.query(Alert).filter(
            Alert.purchase_id == purchase.id,
            Alert.alert_type == "warranty_expiry"
        ).first()

        expected_fire = (
            warranty.warranty_end_date - timedelta(days=WARRANTY_EXPIRY_LEAD_DAYS)
        )
        assert alert.fire_date.date() == expected_fire, (
            f"fire_date={alert.fire_date.date()} expected={expected_fire}"
        )

    def test_lead_time_constants_are_sensible(self):
        """Sanity check: lead times must be positive and sensible."""
        assert 1 <= RETURN_WINDOW_LEAD_DAYS <= 7, (
            f"RETURN_WINDOW_LEAD_DAYS={RETURN_WINDOW_LEAD_DAYS} is outside [1,7]"
        )
        assert 7 <= WARRANTY_EXPIRY_LEAD_DAYS <= 30, (
            f"WARRANTY_EXPIRY_LEAD_DAYS={WARRANTY_EXPIRY_LEAD_DAYS} is outside [7,30]"
        )


# ── Idempotency tests ─────────────────────────────────────────────────────────

class TestAlertIdempotency:

    def test_double_create_does_not_duplicate(self, db, test_user):
        """Calling create_alerts_for_purchase twice should not create duplicates."""
        purchase = _make_purchase(db, test_user.id)
        warranty = _make_warranty(db, purchase.id)

        create_alerts_for_purchase(db, purchase, warranty)
        created_second = create_alerts_for_purchase(db, purchase, warranty)

        assert created_second == 0, (
            f"Second call created {created_second} alerts (expected 0)"
        )

        total_alerts = (
            db.query(Alert).filter(Alert.purchase_id == purchase.id).count()
        )
        assert total_alerts == 2  # Only the original 2

    def test_backfill_is_idempotent(self, db, test_user):
        """backfill_alerts_for_user called repeatedly should not grow the table."""
        purchase = _make_purchase(db, test_user.id)
        _make_warranty(db, purchase.id)

        first = backfill_alerts_for_user(db, test_user.id)
        second = backfill_alerts_for_user(db, test_user.id)

        assert first >= 1
        assert second == 0, (
            f"Backfill on second call created {second} new alerts (expected 0)"
        )


# ── Overdue / upcoming detection ──────────────────────────────────────────────

class TestUpcomingAlerts:

    def test_upcoming_alerts_contains_near_deadline(self, db, test_user):
        """get_upcoming_alerts should include alerts within the look-ahead window."""
        purchase = _make_purchase(db, test_user.id)
        warranty = _make_warranty(db, purchase.id, return_end_offset_days=5)
        create_alerts_for_purchase(db, purchase, warranty)

        alerts = get_upcoming_alerts(db, test_user.id, days_ahead=30)
        assert len(alerts) >= 1

    def test_upcoming_alerts_excludes_far_future(self, db, test_user):
        """get_upcoming_alerts should not include alerts far in the future."""
        purchase = _make_purchase(db, test_user.id)
        # Warranty expires in 2 years (730 days) — fire date is 730-14 = 716 days from now
        warranty = _make_warranty(db, purchase.id, warranty_end_offset_days=730, return_end_offset_days=730)
        create_alerts_for_purchase(db, purchase, warranty)

        alerts = get_upcoming_alerts(db, test_user.id, days_ahead=30)
        # Filter to only this purchase's alerts
        purchase_alerts = [a for a in alerts if a["purchase_id"] == str(purchase.id)]
        assert len(purchase_alerts) == 0, (
            f"Alerts far in the future should not appear in 30-day window"
        )

    def test_overdue_alerts_are_flagged(self, db, test_user):
        """An alert with fire_date in the past should have is_overdue=True."""
        purchase = _make_purchase(db, test_user.id)

        # Manually create an overdue alert
        overdue_alert = Alert(
            id=uuid.uuid4(),
            purchase_id=purchase.id,
            alert_type="return_window_expiry",
            fire_date=datetime.utcnow() - timedelta(days=5),
            sent=False,
        )
        db.add(overdue_alert)
        db.commit()

        alerts = get_upcoming_alerts(db, test_user.id, days_ahead=30)
        overdue = [a for a in alerts if a["purchase_id"] == str(purchase.id) and a["alert_type"] == "return_window_expiry"]
        assert len(overdue) >= 1
        assert overdue[0]["is_overdue"] is True
        assert overdue[0]["days_until"] < 0


# ── Daily check marks alerts as sent ─────────────────────────────────────────

class TestDailyAlertCheck:

    def test_daily_check_marks_due_alerts_sent(self, db, test_user):
        """
        run_daily_alert_check should mark alerts with fire_date <= now as sent.
        This is a unit test using a mock-free approach: we create a due alert,
        monkeypatch SessionLocal, run the check, and verify the alert is marked.
        """
        import app.services.alert_engine as ae_module

        purchase = _make_purchase(db, test_user.id)

        alert_id = uuid.uuid4()
        due_alert = Alert(
            id=alert_id,
            purchase_id=purchase.id,
            alert_type="warranty_expiry",
            fire_date=datetime.utcnow() - timedelta(hours=1),
            sent=False,
        )
        db.add(due_alert)
        db.commit()

        # Monkeypatch SessionLocal to use our test db session
        original_session = ae_module.SessionLocal

        class FakeSessionLocal:
            def __call__(self):
                return db

        ae_module.SessionLocal = FakeSessionLocal()
        try:
            run_daily_alert_check()
        finally:
            ae_module.SessionLocal = original_session

        # Re-query the alert using the captured UUID (original object may be detached)
        refreshed = db.query(Alert).filter(Alert.id == alert_id).first()
        assert refreshed is not None, "Alert row disappeared after daily check"
        assert refreshed.sent is True, "Due alert should be marked as sent after daily check"
