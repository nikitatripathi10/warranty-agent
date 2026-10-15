"""
Milestone 4 â€” Validation Metric Runner

Standalone script that runs the full Extraction Precision and Alert Timeliness
measurements and produces a structured validation report.

Usage:
    cd backend
    python scripts/run_validation.py

This script does NOT require a database connection â€” it runs purely against
the labeled dataset and in-memory SQLite.
"""

from __future__ import annotations

import json
import pathlib
import sys
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from difflib import SequenceMatcher
from typing import Optional

# Add backend/ to sys.path so imports work without pip install -e
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from app.services.extractor_regex import run_regex_pass
from app.services.vendor_normalizer import normalize_vendor
from app.services.category_fallback import apply_category_fallback
from app.services.alert_engine import (
    RETURN_WINDOW_LEAD_DAYS,
    WARRANTY_EXPIRY_LEAD_DAYS,
    create_alerts_for_purchase,
)

# â”€â”€ In-memory SQLite setup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import Alert, Purchase, User, WarrantyPeriod

_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

@event.listens_for(_engine, "connect")
def _enable_fk(dbapi_con, _):
    dbapi_con.execute("PRAGMA foreign_keys=ON")

Base.metadata.create_all(_engine)
_Session = sessionmaker(bind=_engine)

# â”€â”€ Load labeled dataset â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
DATASET_PATH = pathlib.Path(__file__).parent.parent / "tests" / "labeled_dataset.json"
with open(DATASET_PATH, encoding="utf-8") as _f:
    DATASET = json.load(_f)

# â”€â”€ Field matching helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _product_match(e, t):
    if t is None: return True
    if e is None: return False
    e, t = e.lower().strip(), t.lower().strip()
    if t in e or e in t: return True
    return SequenceMatcher(None, e, t).ratio() >= 0.50


def _retailer_match(e, t):
    if t is None: return True
    if e is None: return False
    ne = normalize_vendor(e) or e
    nt = normalize_vendor(t) or t
    return ne.lower().strip() == nt.lower().strip()


def _date_match(e, t):
    return True if t is None else (str(e) == t if e else False)


def _price_match(e, t):
    if t is None: return True
    if e is None: return False
    try: return abs(float(e) - float(t)) <= 1.0
    except: return False


def _int_match(e, t):
    if t is None: return True
    if e is None: return False
    return int(e) == int(t)


def _brand_match(e, t):
    if t is None: return True
    if e is None: return False
    return e.strip().lower() == t.strip().lower()


MATCHERS = {
    "product_name":           _product_match,
    "brand":                  _brand_match,
    "retailer":               _retailer_match,
    "purchase_date":          _date_match,
    "price":                  _price_match,
    "warranty_period_months": _int_match,
    "return_window_days":     _int_match,
}


def _score(result, gt):
    correct = total = 0
    details = {}
    for field, matcher in MATCHERS.items():
        gv = gt.get(field)
        ev = getattr(result, field, None)
        if gv is not None and ev is not None:
            total += 1
            ok = matcher(ev, gv)
            correct += int(ok)
            details[field] = {"extracted": ev, "expected": gv, "ok": ok}
    return correct, total, details


# â”€â”€ Metric 1: Extraction Precision â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def run_extraction_precision():
    print("\n" + "=" * 64)
    print("METRIC 1: EXTRACTION PRECISION (Pass 1 Regex)")
    print("=" * 64)

    total_c = total_t = 0
    failed_cases = []
    conf_counts = {"high": 0, "medium": 0, "low": 0}

    for case in DATASET:
        result = run_regex_pass(case["text"], hint=case.get("retailer_hint"))
        gt = case["ground_truth"]
        c, t, details = _score(result, gt)
        total_c += c
        total_t += t
        conf_counts[result.confidence] = conf_counts.get(result.confidence, 0) + 1

        if t > 0 and c < t:
            failed_cases.append({
                "id": case["id"],
                "precision": c / t,
                "details": {k: v for k, v in details.items() if not v["ok"]},
            })

    precision = total_c / total_t if total_t else 0.0

    print(f"\n  Dataset size:          {len(DATASET)} cases")
    print(f"  Total fields matched:  {total_t}")
    print(f"  Total correct:         {total_c}")
    print(f"  Extraction Precision:  {precision:.1%}  {'âœ… PASS' if precision >= 0.60 else 'âŒ BELOW TARGET'}")
    print(f"\n  Confidence distribution:")
    for conf, count in conf_counts.items():
        pct = 100 * count / len(DATASET)
        print(f"    {conf:8s}: {count:2d} cases ({pct:.0f}%)")

    if failed_cases:
        print(f"\n  Cases with field mismatches ({len(failed_cases)} total):")
        for fc in failed_cases[:8]:
            print(f"    [{fc['id']}] precision={fc['precision']:.0%}")
            for field, info in fc["details"].items():
                print(f"      {field}: extracted={info['extracted']!r} â‰  expected={info['expected']!r}")

    print(f"\n  Target: â‰¥ 60% | Result: {precision:.1%}")
    return precision


# â”€â”€ Metric 2: Alert Timeliness â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def run_alert_timeliness():
    print("\n" + "=" * 64)
    print("METRIC 2: ALERT TIMELINESS")
    print("=" * 64)

    db = _Session()
    test_cases = [
        # (label, warranty_days_offset, return_days_offset)
        ("Near-term return (7 days)",   365, 7),
        ("Mid-term return (14 days)",   365, 14),
        ("Near-term warranty (30d)",    30,  365),
        ("Standard warranty (365d)",    365, 30),
        ("Long warranty (2yr)",         730, 30),
    ]

    all_pass = True
    print(f"\n  Lead times: return={RETURN_WINDOW_LEAD_DAYS}d, warranty={WARRANTY_EXPIRY_LEAD_DAYS}d\n")

    for label, w_offset, r_offset in test_cases:
        uid = uuid.uuid4()
        user = User(id=uid, email=f"{uid.hex[:8]}@test.com", google_oauth_token_encrypted="x")
        db.add(user)
        db.commit()

        purchase = Purchase(
            id=uuid.uuid4(), user_id=uid,
            product_name="Test Product", brand="TestBrand",
            retailer="Amazon", purchase_date=date.today() - timedelta(days=5),
            price=Decimal("9999"), source_type="email",
        )
        db.add(purchase)
        db.commit()

        today = date.today()
        warranty_end = today + timedelta(days=w_offset)
        return_end   = today + timedelta(days=r_offset)

        wp = WarrantyPeriod(
            id=uuid.uuid4(), purchase_id=purchase.id,
            warranty_end_date=warranty_end,
            return_window_end_date=return_end,
            confidence_score="high", is_estimated=False,
        )
        db.add(wp)
        db.commit()

        create_alerts_for_purchase(db, purchase, wp)

        ret_alert = db.query(Alert).filter_by(
            purchase_id=purchase.id, alert_type="return_window_expiry"
        ).first()
        war_alert = db.query(Alert).filter_by(
            purchase_id=purchase.id, alert_type="warranty_expiry"
        ).first()

        ret_ok = False
        war_ok = False
        ret_err = war_err = ""

        if ret_alert:
            expected_ret = return_end - timedelta(days=RETURN_WINDOW_LEAD_DAYS)
            ret_ok = ret_alert.fire_date.date() == expected_ret
            if not ret_ok:
                ret_err = f"fire={ret_alert.fire_date.date()} expected={expected_ret}"
        else:
            ret_err = "missing"

        if war_alert:
            expected_war = warranty_end - timedelta(days=WARRANTY_EXPIRY_LEAD_DAYS)
            war_ok = war_alert.fire_date.date() == expected_war
            if not war_ok:
                war_err = f"fire={war_alert.fire_date.date()} expected={expected_war}"
        else:
            war_err = "missing"

        status = "âœ…" if (ret_ok and war_ok) else "âŒ"
        print(f"  {'OK' if (ret_ok and war_ok) else 'FAIL'} {label}")
        if not ret_ok: print(f"     return alert: {ret_err}")
        if not war_ok: print(f"     warranty alert: {war_err}")
        all_pass = all_pass and ret_ok and war_ok

    db.close()

    timeliness = 1.0 if all_pass else 0.0
    print(f"\n  Alert Timeliness: {'100% âœ… PASS' if all_pass else 'FAILED âŒ'}")
    print(f"  Target: 100% | All fire_dates must match deadline - lead_days")
    return timeliness


# â”€â”€ Metric 3: Category Fallback Coverage â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def run_category_fallback_coverage():
    print("\n" + "=" * 64)
    print("METRIC 3: CATEGORY FALLBACK COVERAGE")
    print("=" * 64)

    samples = [
        ("Samsung Galaxy S23 Ultra", "Samsung", True),
        ("Lenovo IdeaPad Slim 3 Laptop", "Lenovo", True),
        ("LG 8kg Washing Machine", "LG", True),
        ("Roadster Men T-shirt", None, True),
        ("Apple AirPods Pro 2nd Gen", "Apple", True),
        ("Voltas 1.5 Ton AC", "Voltas", True),
        ("Havells 3L Water Heater", "Havells", True),
        ("RandomXYZ Unknown Item", None, False),
    ]

    matched = 0
    print()
    for product, brand, expect_match in samples:
        from app.services.category_fallback import get_category_fallback
        result = get_category_fallback(product, brand)
        got_match = result is not None
        ok = got_match == expect_match
        matched += int(ok)
        status = "[OK]  " if ok else "[FAIL]"
        cat = result[0] if result else "No match"
        print(f"  {status} {product[:45]:<45} -> {cat}")

    coverage = matched / len(samples)
    print(f"\n  Category detection accuracy: {coverage:.0%}  {chr(91)+chr(80)+chr(65)+chr(83)+chr(83)+chr(93) if coverage >= 0.80 else chr(91)+chr(70)+chr(65)+chr(73)+chr(76)+chr(93)}")
    print(f"  Target: >= 80% | Result: {coverage:.0%}")
    return coverage


# Final report

def main():
    print("\n" + "=" * 64)
    print("  WARRANTY RADAR -- MILESTONE 4 VALIDATION REPORT")
    print(f"  Run at: {datetime.now().strftime(chr(37)+chr(89)+chr(45)+chr(37)+chr(109)+chr(45)+chr(37)+chr(100)+chr(32)+chr(37)+chr(72)+chr(58)+chr(37)+chr(77)+chr(58)+chr(37)+chr(83))}")
    print("=" * 64)

    p1 = run_extraction_precision()
    p2 = run_alert_timeliness()
    p3 = run_category_fallback_coverage()

    print("\n" + "=" * 64)
    print("  SUMMARY")
    print("=" * 64)
    print(f"  Extraction Precision:      {p1:.1%}  {chr(91)+chr(80)+chr(65)+chr(83)+chr(83)+chr(93) if p1 >= 0.60 else chr(91)+chr(70)+chr(65)+chr(73)+chr(76)+chr(93)}")
    print(f"  Alert Timeliness:          {chr(49)+chr(48)+chr(48)+chr(37) if p2 else chr(70)+chr(65)+chr(73)+chr(76)} {chr(91)+chr(80)+chr(65)+chr(83)+chr(83)+chr(93) if p2 else chr(91)+chr(70)+chr(65)+chr(73)+chr(76)+chr(93)}")
    print(f"  Category Fallback Acc:     {p3:.0%}  {chr(91)+chr(80)+chr(65)+chr(83)+chr(83)+chr(93) if p3 >= 0.80 else chr(91)+chr(70)+chr(65)+chr(73)+chr(76)+chr(93)}")
    overall = (p1 >= 0.60) and (p2 >= 1.0) and (p3 >= 0.80)
    print(f"\n  Overall: {chr(65)+chr(76)+chr(76)+chr(32)+chr(84)+chr(65)+chr(82)+chr(71)+chr(69)+chr(84)+chr(83)+chr(32)+chr(77)+chr(69)+chr(84) if overall else chr(83)+chr(79)+chr(77)+chr(69)+chr(32)+chr(84)+chr(65)+chr(82)+chr(71)+chr(69)+chr(84)+chr(83)+chr(32)+chr(77)+chr(73)+chr(83)+chr(83)+chr(69)+chr(68)}")
    print("=" * 64 + "\n")

    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
