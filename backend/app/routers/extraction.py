"""
POST /extraction/test — Run the two-pass pipeline on raw text without persisting.

Useful for development, debugging, and automated tests of the extraction engine.
The result is returned directly; nothing is written to the database.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from app.schemas import ExtractionResultSchema, ExtractionTestRequest
from app.services.extractor_regex import run_regex_pass
from app.services.extractor_llm import extract_with_llm

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/test",
    response_model=ExtractionResultSchema,
    summary="Test extraction pipeline on raw text (no DB write)",
)
def test_extraction(body: ExtractionTestRequest) -> ExtractionResultSchema:
    """
    Run Pass 1 (regex) then Pass 2 (LLM) on the supplied text and return the result.

    This endpoint is for development/debug only — it does not persist any data.
    """
    logger.info(
        "Extraction test requested: %d chars, hint=%r",
        len(body.text),
        body.hint,
    )

    # Pass 1 — regex
    regex_result = run_regex_pass(body.text, hint=body.hint)
    logger.info("Pass 1 result: confidence=%s", regex_result.confidence)

    if regex_result.confidence != "low":
        # Regex was confident enough — skip LLM
        return _to_schema(regex_result)

    # Pass 2 — LLM fallback
    logger.info("Pass 1 confidence is 'low' — triggering LLM fallback")
    llm_result = extract_with_llm(body.text)

    if llm_result is not None:
        return _to_schema(llm_result)

    # LLM also failed — return whatever regex managed
    logger.warning("Both passes failed or returned low confidence — returning regex result")
    return _to_schema(regex_result)


def _to_schema(result) -> ExtractionResultSchema:
    return ExtractionResultSchema(
        product_name=result.product_name,
        brand=result.brand,
        retailer=result.retailer,
        purchase_date=result.purchase_date,
        price=result.price,
        warranty_period_months=result.warranty_period_months,
        return_window_days=result.return_window_days,
        confidence=result.confidence,
        source_snippet=result.source_snippet,
        pass_used=result.pass_used,
    )
