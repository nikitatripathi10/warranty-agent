"""
Ingestion endpoints — email fetching and document uploads.

POST /ingestion/fetch-emails?user_id=<uuid>
    Fetches Gmail order-confirmation emails for the user, runs two-pass
    extraction on each, persists results to purchases + warranty_periods.

POST /ingestion/upload
    Accepts a PDF or image file upload, runs OCR if needed, then extraction,
    then persists the result.

Notes:
- Raw email bodies are NEVER stored in the database. Only the Gmail message ID
  is stored long-term (in purchases.source_email_id).
- Uploaded files are saved to the UPLOAD_DIR directory; only the relative path
  is stored in purchases.source_file_ref.
- user_id is accepted as a query/form parameter. A proper auth middleware will
  replace this in a later milestone.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from google.oauth2.credentials import Credentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Purchase, User, WarrantyPeriod
from app.schemas import IngestionSummary, PurchaseOut, UploadResponse
from app.services.encryption import decrypt_token
from app.services.extractor_llm import extract_with_llm
from app.services.extractor_regex import ExtractionResult, run_regex_pass
from app.services.gmail_client import (
    build_gmail_service,
    fetch_message_attachments,
    fetch_message_body,
    search_order_emails,
)
from app.services.ocr import extract_text
from app.services.vendor_normalizer import normalize_vendor
from app.services.category_fallback import apply_category_fallback
from app.services.alert_engine import create_alerts_for_purchase

load_dotenv()

logger = logging.getLogger(__name__)
router = APIRouter()

_UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB hard limit


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return user


def _rebuild_credentials(user: User) -> Credentials:
    """Decrypt the stored refresh token and build a Credentials object."""
    if not user.google_oauth_token_encrypted:
        raise HTTPException(
            status_code=400,
            detail="This user has not connected Gmail. Call /auth/gmail/connect first.",
        )
    try:
        refresh_token = decrypt_token(user.google_oauth_token_encrypted)
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to decrypt OAuth token — possible key rotation issue.",
        ) from exc

    google_client_id     = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")

    return Credentials(
        token=None,  # Will be refreshed automatically on first API call
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=google_client_id,
        client_secret=google_client_secret,
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )


def _run_extraction_pipeline(
    text: str,
    hint: Optional[str] = None,
    file_bytes: Optional[bytes] = None,
    mime_type: Optional[str] = None,
) -> ExtractionResult:
    """
    Run Pass 1 (regex) then Pass 2 (Gemini Multimodal Vision / LLM) if needed.

    Returns whichever result is more complete and confident.
    """
    regex_result = run_regex_pass(text, hint=hint)
    final_result = regex_result

    needs_llm = (
        regex_result.confidence == "low"
        or not regex_result.product_name
        or regex_result.purchase_date is None
    )

    if not needs_llm:
        logger.info("Two-pass: Pass 1 sufficient (confidence=%s)", regex_result.confidence)
    else:
        logger.info("Two-pass: Invoking Gemini Vision / LLM extraction")
        llm_result = extract_with_llm(text, file_bytes=file_bytes, mime_type=mime_type)
        if llm_result is not None and llm_result.product_name:
            # Merge any fields regex found that LLM left blank
            if not llm_result.brand and regex_result.brand:
                llm_result.brand = regex_result.brand
            if not llm_result.retailer and regex_result.retailer:
                llm_result.retailer = regex_result.retailer
            if llm_result.purchase_date is None and regex_result.purchase_date is not None:
                llm_result.purchase_date = regex_result.purchase_date
            if llm_result.price is None and regex_result.price is not None:
                llm_result.price = regex_result.price
            if llm_result.warranty_period_months is None and regex_result.warranty_period_months is not None:
                llm_result.warranty_period_months = regex_result.warranty_period_months
            if llm_result.return_window_days is None and regex_result.return_window_days is not None:
                llm_result.return_window_days = regex_result.return_window_days
            final_result = llm_result
        elif llm_result is not None and regex_result.product_name:
            # Fill missing fields on regex_result from llm_result
            if not final_result.brand and llm_result.brand:
                final_result.brand = llm_result.brand
            if not final_result.retailer and llm_result.retailer:
                final_result.retailer = llm_result.retailer
            if final_result.purchase_date is None and llm_result.purchase_date is not None:
                final_result.purchase_date = llm_result.purchase_date
            if final_result.price is None and llm_result.price is not None:
                final_result.price = llm_result.price
        else:
            logger.warning("Two-pass: LLM fallback returned None — using regex result")

    if final_result.product_name:
        fallback = apply_category_fallback(
            product_name=final_result.product_name,
            brand=final_result.brand,
            existing_warranty_months=final_result.warranty_period_months,
            existing_return_days=final_result.return_window_days,
        )
        if final_result.warranty_period_months is None:
            final_result.warranty_period_months = fallback["warranty_period_months"]
        if final_result.return_window_days is None:
            final_result.return_window_days = fallback["return_window_days"]

    return final_result


def _compute_warranty_end(purchase_date: Optional[date], months: Optional[int]) -> Optional[date]:
    if purchase_date and months:
        # Simple approximation: 30 days/month
        return purchase_date + timedelta(days=months * 30)
    return None


def _compute_return_window_end(purchase_date: Optional[date], days: Optional[int]) -> Optional[date]:
    if purchase_date and days:
        return purchase_date + timedelta(days=days)
    return None


def _persist_purchase(
    db: Session,
    user_id: uuid.UUID,
    result: ExtractionResult,
    source_type: str,
    source_email_id: Optional[str] = None,
    source_file_ref: Optional[str] = None,
) -> Purchase:
    """Create and commit a Purchase + WarrantyPeriod row from an ExtractionResult."""
    # Normalise retailer to canonical form before saving
    canonical_retailer = normalize_vendor(result.retailer) or result.retailer

    purchase = Purchase(
        user_id=user_id,
        product_name=result.product_name,
        brand=result.brand,
        retailer=canonical_retailer,
        purchase_date=result.purchase_date,
        price=result.price,
        source_type=source_type,
        source_email_id=source_email_id,
        source_file_ref=source_file_ref,
    )
    db.add(purchase)
    db.flush()  # Get the purchase.id before committing

    # Apply category fallback for missing warranty / return-window data
    fallback = apply_category_fallback(
        product_name=result.product_name,
        brand=result.brand,
        existing_warranty_months=result.warranty_period_months,
        existing_return_days=result.return_window_days,
    )

    warranty_end = _compute_warranty_end(
        result.purchase_date, fallback["warranty_period_months"]
    )
    return_end = _compute_return_window_end(
        result.purchase_date, fallback["return_window_days"]
    )

    # is_estimated: True if category fallback was used OR if LLM was the source
    is_estimated = fallback["is_estimated"] or (result.pass_used == "llm")

    warranty = WarrantyPeriod(
        purchase_id=purchase.id,
        warranty_end_date=warranty_end,
        return_window_end_date=return_end,
        confidence_score=result.confidence,
        source_snippet=result.source_snippet or f"[pass={result.pass_used}]",
        is_estimated=is_estimated,
    )
    db.add(warranty)
    db.commit()
    db.refresh(purchase)

    # Schedule alerts for the newly persisted purchase
    create_alerts_for_purchase(db, purchase, warranty)

    return purchase


# ── Email fetch endpoint ──────────────────────────────────────────────────────

@router.post(
    "/fetch-emails",
    response_model=IngestionSummary,
    summary="Fetch and ingest Gmail order emails for a user",
)
def fetch_emails(
    user_id: uuid.UUID = Query(..., description="UUID of the connected user"),
    max_results: int = Query(50, ge=1, le=200, description="Max emails to scan"),
    db: Session = Depends(get_db),
) -> IngestionSummary:
    """
    1. Rebuild OAuth credentials from the stored encrypted refresh token.
    2. Search Gmail for order-confirmation emails.
    3. For each message, fetch the body, run two-pass extraction, persist result.
    4. Return a summary with counts and any errors.
    """
    user = _get_user_or_404(db, user_id)
    credentials = _rebuild_credentials(user)

    try:
        gmail_service = build_gmail_service(credentials)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    messages = search_order_emails(gmail_service, max_results=max_results)
    logger.info("Fetched %d email stubs for user %s", len(messages), user_id)

    created = 0
    failed  = 0
    errors: list[str] = []

    for stub in messages:
        msg_id = stub.get("id", "")
        try:
            existing = (
                db.query(Purchase)
                .filter(Purchase.user_id == user.id, Purchase.source_email_id == msg_id)
                .first()
            )

            body_parts: list[str] = []
            body = fetch_message_body(gmail_service, msg_id)
            if body:
                body_parts.append(body)

            # Also extract text/OCR from any PDF or image attachments (e.g. warranty cards / invoices)
            attachments = fetch_message_attachments(gmail_service, msg_id)
            for att_filename, att_mime, att_bytes in attachments:
                att_text, _ = extract_text(att_bytes, att_filename, content_type=att_mime)
                if att_text.strip():
                    body_parts.append(att_text)

            combined_text = "\n\n".join(body_parts).strip()
            if not combined_text:
                logger.warning("Empty body and no readable attachments for message %s — skipping", msg_id)
                failed += 1
                errors.append(f"msg:{msg_id} — empty content")
                continue

            # Determine retailer hint from email body (best-effort)
            hint = None
            body_lower = combined_text.lower()
            if "amazon" in body_lower:
                hint = "amazon"
            elif "flipkart" in body_lower:
                hint = "flipkart"
            elif "meesho" in body_lower:
                hint = "meesho"
            elif "ajio" in body_lower:
                hint = "ajio"

            result = _run_extraction_pipeline(combined_text, hint=hint)

            # Guard against persisting records without an identifiable product name
            if not result.product_name:
                logger.warning("No product name extracted from email %s — skipping", msg_id)
                failed += 1
                errors.append(f"msg:{msg_id} — no product name detected")
                continue

            if existing:
                db.delete(existing)
                db.commit()

            _persist_purchase(
                db,
                user_id=user.id,
                result=result,
                source_type="email",
                source_email_id=msg_id,
            )
            created += 1
            logger.info(
                "Persisted purchase from email %s: %r (confidence=%s)",
                msg_id,
                result.product_name,
                result.confidence,
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Failed to process email %s: %s", msg_id, exc)
            failed += 1
            errors.append(f"msg:{msg_id} — {exc}")

    return IngestionSummary(
        user_id=user.id,
        emails_scanned=len(messages),
        purchases_created=created,
        purchases_failed=failed,
        errors=errors,
    )


# ── Document upload endpoint ──────────────────────────────────────────────────

@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload a PDF/image document and extract purchase info",
)
async def upload_document(
    file: UploadFile = File(..., description="PDF, JPEG, or PNG invoice/warranty card"),
    user_id: uuid.UUID = Form(..., description="UUID of the user uploading the document"),
    db: Session = Depends(get_db),
) -> UploadResponse:
    """
    1. Validate and save the uploaded file to UPLOAD_DIR.
    2. Extract text (OCR if needed).
    3. Run two-pass extraction.
    4. Persist purchase + warranty_period rows.
    5. Return the created purchase and extraction metadata.
    """
    user = _get_user_or_404(db, user_id)

    # -- Validate file type --
    allowed_content_types = {
        "application/pdf",
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/tiff",
    }
    if file.content_type and file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type: {file.content_type!r}. "
                "Please upload a PDF, JPEG, PNG, WEBP, or TIFF."
            ),
        )

    # -- Read file bytes with size guard --
    file_bytes = await file.read()
    if len(file_bytes) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File is too large. Maximum allowed size is {_MAX_UPLOAD_BYTES // (1024*1024)} MB.",
        )

    # -- Save to uploads/ directory --
    _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_filename = _sanitise_filename(file.filename or "upload")
    unique_filename = f"{uuid.uuid4().hex}_{safe_filename}"
    save_path = _UPLOAD_DIR / unique_filename

    try:
        save_path.write_bytes(file_bytes)
        logger.info("Saved upload: %s (%d bytes)", save_path, len(file_bytes))
    except OSError as exc:
        logger.error("Failed to save uploaded file: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Could not save the uploaded file. Please try again.",
        ) from exc

    source_file_ref = str(save_path)

    # -- Extract & analyse document (Gemini Vision first for images, OCR + regex fallback) --
    content_type = file.content_type or ""
    is_image_upload = content_type.startswith("image/") or safe_filename.lower().endswith(
        (".jpg", ".jpeg", ".png", ".webp")
    )

    result: Optional[ExtractionResult] = None
    ocr_used = False

    if is_image_upload:
        # Fast path: use Gemini Vision API directly on the image bytes (~2-3s, zero CPU OCR bottleneck)
        vision_res = extract_with_llm("", file_bytes=file_bytes, mime_type=content_type or "image/jpeg")
        if vision_res is not None and vision_res.product_name:
            fallback = apply_category_fallback(
                product_name=vision_res.product_name,
                brand=vision_res.brand,
                existing_warranty_months=vision_res.warranty_period_months,
                existing_return_days=vision_res.return_window_days,
            )
            if vision_res.warranty_period_months is None:
                vision_res.warranty_period_months = fallback["warranty_period_months"]
            if vision_res.return_window_days is None:
                vision_res.return_window_days = fallback["return_window_days"]
            result = vision_res
            ocr_used = True

    if result is None:
        text, ocr_used = extract_text(file_bytes, safe_filename, content_type=content_type)
        if not text.strip():
            logger.warning("No text extracted from '%s' — result will have low confidence", safe_filename)
        result = _run_extraction_pipeline(
            text,
            file_bytes=file_bytes,
            mime_type=content_type,
        )

    # -- Persist to DB --
    try:
        purchase = _persist_purchase(
            db,
            user_id=user.id,
            result=result,
            source_type="upload",
            source_file_ref=source_file_ref,
        )
    except Exception as exc:
        logger.error("DB error persisting upload for user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Extraction succeeded but saving to database failed. Please try again.",
        ) from exc

    logger.info(
        "Upload ingestion complete for user %s: product=%r confidence=%s ocr=%s",
        user_id,
        result.product_name,
        result.confidence,
        ocr_used,
    )

    from app.schemas import ExtractionResultSchema
    extraction_schema = ExtractionResultSchema(
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

    return UploadResponse(
        purchase=PurchaseOut.model_validate(purchase),
        extraction=extraction_schema,
        ocr_used=ocr_used,
    )


def _sanitise_filename(filename: str) -> str:
    """Strip directory traversal characters and keep only safe characters."""
    import re
    name = Path(filename).name  # Strip any path components
    name = re.sub(r"[^\w.\-]", "_", name)
    return name[:200]  # Truncate to avoid filesystem limits
