"""
test_db.py -- End-to-end schema smoke test.

Inserts a User, a linked Purchase, and a WarrantyPeriod, reads them back,
prints a summary, then deletes the test rows. Run this AFTER running:

    alembic upgrade head

Usage (from backend/):
    python scripts/test_db.py

Requires DATABASE_URL to be set in backend/.env.
"""

from __future__ import annotations

import sys
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

# Force UTF-8 output on Windows so non-ASCII characters don't crash cp1252
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure backend/ is on sys.path so we can import app.*
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.database import SessionLocal, engine
from app.models import Purchase, User, WarrantyPeriod


def run_smoke_test() -> None:
    db = SessionLocal()

    try:
        print("=" * 60)
        print("Warranty Radar -- DB Smoke Test")
        print("=" * 60)

        # -- 1. Verify all five tables exist --
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        expected = {"users", "purchases", "warranty_periods", "alerts", "recalls"}
        missing = expected - tables
        if missing:
            print(f"\n[FAIL] Missing tables: {missing}")
            print("   Run: alembic upgrade head")
            sys.exit(1)
        print(f"\n[OK] All expected tables present: {sorted(expected)}")

        # -- 2. Insert test user --
        test_email = f"smoke-test-{uuid.uuid4().hex[:8]}@example.com"
        user = User(email=test_email, google_oauth_token_encrypted="test-encrypted-token")
        db.add(user)
        db.flush()
        print(f"\n[OK] Inserted User        : id={user.id}  email={user.email}")

        # -- 3. Insert test purchase --
        purchase = Purchase(
            user_id=user.id,
            product_name="Sony WH-1000XM5 Headphones",
            brand="Sony",
            retailer="Amazon.in",
            purchase_date=date(2025, 8, 15),
            price=Decimal("28990.00"),
            source_type="email",
            source_email_id="FAKE_GMAIL_MESSAGE_ID_12345",
        )
        db.add(purchase)
        db.flush()
        print(f"[OK] Inserted Purchase     : id={purchase.id}  product={purchase.product_name!r}")

        # -- 4. Insert warranty period --
        warranty = WarrantyPeriod(
            purchase_id=purchase.id,
            warranty_end_date=date(2026, 8, 15),
            return_window_end_date=date(2025, 9, 14),
            confidence_score="high",
            source_snippet="1-year manufacturer warranty. Return within 30 days.",
            is_estimated=False,
        )
        db.add(warranty)
        db.commit()
        print(
            f"[OK] Inserted WarrantyPeriod: warranty_end={warranty.warranty_end_date}  "
            f"return_end={warranty.return_window_end_date}  confidence={warranty.confidence_score}"
        )

        # -- 5. Query back and verify --
        fetched_user = db.query(User).filter(User.id == user.id).one()
        fetched_purchase = db.query(Purchase).filter(Purchase.user_id == user.id).first()
        fetched_warranty = (
            db.query(WarrantyPeriod)
            .filter(WarrantyPeriod.purchase_id == fetched_purchase.id)
            .one()
        )

        print("\n-- Query results --")
        print(f"   User email   : {fetched_user.email}")
        print(f"   Product      : {fetched_purchase.product_name}")
        print(f"   Price        : Rs. {fetched_purchase.price}")
        print(f"   Source type  : {fetched_purchase.source_type}")
        print(f"   Warranty end : {fetched_warranty.warranty_end_date}")
        print(f"   Confidence   : {fetched_warranty.confidence_score}")

        # -- 6. Cleanup (cascade delete) --
        db.delete(fetched_user)
        db.commit()
        print("\n[OK] Test rows deleted (cascade worked)")

        print("\n*** Smoke test PASSED -- schema is live and working correctly. ***")
        print("=" * 60)

    except Exception as exc:
        db.rollback()
        print(f"\n[FAIL] Smoke test FAILED: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    run_smoke_test()
