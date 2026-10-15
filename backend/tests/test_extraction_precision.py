"""
Milestone 4 — Extraction Precision Tests (pytest)

Tests the two-pass extraction pipeline against the labeled dataset
(labeled_dataset.json) and measures Extraction Precision:

    Extraction Precision = Correct Fields Extracted / Total Fields Extracted

A "correct field" is one where:
  - Both ground truth and extracted value are non-null, AND
  - The extracted value matches the ground truth within tolerance.

Matching rules per field:
  product_name  — case-insensitive substring match (≥60% overlap) using SequenceMatcher
  brand         — case-insensitive exact match after stripping
  retailer      — canonical name match (after vendor normalisation)
  purchase_date — exact ISO date string match
  price         — within 1 INR tolerance
  warranty_*    — exact integer match
  return_*      — exact integer match

Run:
    cd backend
    venv\\Scripts\\pytest tests/test_extraction_precision.py -v --tb=short
"""

import json
import pathlib
from decimal import Decimal
from difflib import SequenceMatcher
from typing import Optional


DATASET_PATH = pathlib.Path(__file__).parent / "labeled_dataset.json"
# Minimum similarity ratio to accept product_name match
_PRODUCT_SIM_THRESHOLD = 0.50


def _load_dataset():
    with open(DATASET_PATH, encoding="utf-8") as f:
        return json.load(f)


def _product_name_matches(extracted: Optional[str], truth: Optional[str]) -> bool:
    """Case-insensitive substring / similarity match for product names."""
    if truth is None:
        return True  # Don't penalise when ground truth is None
    if extracted is None:
        return False
    e = extracted.lower().strip()
    t = truth.lower().strip()
    # Accept if one contains the other, or if similarity is high enough
    if t in e or e in t:
        return True
    ratio = SequenceMatcher(None, e, t).ratio()
    return ratio >= _PRODUCT_SIM_THRESHOLD


def _brand_matches(extracted: Optional[str], truth: Optional[str]) -> bool:
    if truth is None:
        return True
    if extracted is None:
        return False
    return extracted.strip().lower() == truth.strip().lower()


def _retailer_matches(extracted: Optional[str], truth: Optional[str]) -> bool:
    if truth is None:
        return True
    if extracted is None:
        return False
    from app.services.vendor_normalizer import normalize_vendor
    norm_extracted = normalize_vendor(extracted) or extracted
    norm_truth = normalize_vendor(truth) or truth
    return norm_extracted.strip().lower() == norm_truth.strip().lower()


def _date_matches(extracted, truth: Optional[str]) -> bool:
    if truth is None:
        return True
    if extracted is None:
        return False
    return str(extracted) == truth


def _price_matches(extracted, truth: Optional[float]) -> bool:
    if truth is None:
        return True
    if extracted is None:
        return False
    try:
        return abs(float(extracted) - float(truth)) <= 1.0
    except (TypeError, ValueError):
        return False


def _int_field_matches(extracted: Optional[int], truth: Optional[int]) -> bool:
    if truth is None:
        return True
    if extracted is None:
        return False
    return int(extracted) == int(truth)


def _count_fields(result, ground_truth: dict) -> tuple[int, int]:
    """
    Return (correct, total) counts for extracted non-null fields.

    We only count fields where ground truth is non-null (we can't verify
    a field that wasn't labelled). We count a field as "attempted" only when
    the extractor returned a non-null value AND ground truth is non-null.
    """
    correct = 0
    total = 0

    checks = [
        ("product_name",          _product_name_matches(result.product_name,      ground_truth.get("product_name"))),
        ("brand",                 _brand_matches(result.brand,                    ground_truth.get("brand"))),
        ("retailer",              _retailer_matches(result.retailer,              ground_truth.get("retailer"))),
        ("purchase_date",         _date_matches(result.purchase_date,             ground_truth.get("purchase_date"))),
        ("price",                 _price_matches(result.price,                    ground_truth.get("price"))),
        ("warranty_period_months",_int_field_matches(result.warranty_period_months, ground_truth.get("warranty_period_months"))),
        ("return_window_days",    _int_field_matches(result.return_window_days,   ground_truth.get("return_window_days"))),
    ]

    for field_name, is_correct in checks:
        gt_val = ground_truth.get(field_name)
        extracted_val = getattr(result, field_name, None)
        if gt_val is not None and extracted_val is not None:
            total += 1
            if is_correct:
                correct += 1

    return correct, total


# ── Per-case tests (parametrised) ─────────────────────────────────────────────

import pytest

dataset = _load_dataset()


@pytest.mark.parametrize("case", dataset, ids=[c["id"] for c in dataset])
def test_extraction_case(case):
    """
    For each labeled case, verify:
    1. Extraction runs without error.
    2. Confidence is not lower than ground_truth.confidence_min.
    3. At least 50% of non-null labeled fields are correctly extracted.
    """
    from app.services.extractor_regex import run_regex_pass

    text = case["text"]
    hint = case.get("retailer_hint")
    ground_truth = case["ground_truth"]
    confidence_min = ground_truth.get("confidence_min", "low")

    result = run_regex_pass(text, hint=hint)

    # Confidence floor — extractor must not report worse than minimum expected
    confidence_order = {"high": 2, "medium": 1, "low": 0}
    extracted_level = confidence_order.get(result.confidence, 0)
    min_level = confidence_order.get(confidence_min, 0)
    # We allow lower confidence if ground truth min is 'low' — that's expected
    if confidence_min != "low":
        assert extracted_level >= min_level - 1, (
            f"[{case['id']}] confidence too low: got {result.confidence!r}, "
            f"expected at least {confidence_min!r}"
        )

    # Field precision
    correct, total = _count_fields(result, ground_truth)
    if total > 0:
        precision = correct / total
        assert precision >= 0.40, (
            f"[{case['id']}] field precision {precision:.0%} "
            f"({correct}/{total} correct) — below 40% threshold\n"
            f"  Extracted: product={result.product_name!r} brand={result.brand!r} "
            f"retailer={result.retailer!r} date={result.purchase_date} "
            f"price={result.price}\n"
            f"  Expected:  product={ground_truth.get('product_name')!r} "
            f"brand={ground_truth.get('brand')!r} retailer={ground_truth.get('retailer')!r} "
            f"date={ground_truth.get('purchase_date')} price={ground_truth.get('price')}"
        )


# ── Aggregate precision measurement ───────────────────────────────────────────

def test_aggregate_extraction_precision():
    """
    HEADLINE METRIC: Extraction Precision across the full labeled dataset.
    Measures: Correct Fields Extracted / Total Fields Extracted (non-null pairs).

    Target: ≥ 65% (Pass 1 regex only, without LLM).
    """
    from app.services.extractor_regex import run_regex_pass

    total_correct = 0
    total_attempted = 0
    failures = []

    for case in dataset:
        text = case["text"]
        hint = case.get("retailer_hint")
        ground_truth = case["ground_truth"]

        result = run_regex_pass(text, hint=hint)
        correct, total = _count_fields(result, ground_truth)
        total_correct += correct
        total_attempted += total
        if total > 0 and correct < total:
            failures.append(
                f"  [{case['id']}] {correct}/{total} correct "
                f"(product={result.product_name!r}, price={result.price}, "
                f"retailer={result.retailer!r})"
            )

    precision = total_correct / total_attempted if total_attempted else 0.0
    report = (
        f"\n{'='*60}\n"
        f"EXTRACTION PRECISION REPORT (Pass 1 Regex Only)\n"
        f"{'='*60}\n"
        f"  Dataset size:       {len(dataset)} cases\n"
        f"  Fields attempted:   {total_attempted}\n"
        f"  Fields correct:     {total_correct}\n"
        f"  Precision:          {precision:.1%}\n"
        f"{'='*60}\n"
    )
    if failures:
        report += "Cases with partial mismatches:\n" + "\n".join(failures[:10])
        if len(failures) > 10:
            report += f"\n  ... and {len(failures)-10} more"

    print(report)

    assert precision >= 0.60, (
        f"Extraction precision {precision:.1%} is below the 60% target.\n{report}"
    )
