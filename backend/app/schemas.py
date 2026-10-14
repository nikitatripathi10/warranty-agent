"""
Pydantic v2 request/response schemas for Warranty Radar.

These are the public API shapes — distinct from SQLAlchemy ORM models.
FastAPI uses these for automatic validation, serialisation, and OpenAPI docs.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


# ── Extraction schemas ────────────────────────────────────────────────────────

class ExtractionResultSchema(BaseModel):
    """Output of the two-pass extraction pipeline."""

    product_name: Optional[str] = None
    brand: Optional[str] = None
    retailer: Optional[str] = None
    purchase_date: Optional[date] = None
    price: Optional[Decimal] = None
    warranty_period_months: Optional[int] = Field(
        None, description="Warranty length in months if stated"
    )
    return_window_days: Optional[int] = Field(
        None, description="Return window in days if stated"
    )
    confidence: str = Field(
        "low", description="Extraction confidence: 'high', 'medium', or 'low'"
    )
    source_snippet: Optional[str] = Field(
        None, description="Raw text fragment used for extraction"
    )
    pass_used: str = Field(
        "regex", description="Which pass produced the result: 'regex' or 'llm'"
    )


# ── Purchase schemas ──────────────────────────────────────────────────────────

class WarrantyPeriodOut(BaseModel):
    """Public representation of a warranty_periods row."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    purchase_id: uuid.UUID
    warranty_end_date: Optional[date] = None
    return_window_end_date: Optional[date] = None
    confidence_score: str
    source_snippet: Optional[str] = None
    is_estimated: bool


class PurchaseOut(BaseModel):
    """Public representation of a purchases row."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    product_name: Optional[str] = None
    brand: Optional[str] = None
    retailer: Optional[str] = None
    purchase_date: Optional[date] = None
    price: Optional[Decimal] = None
    source_type: str
    source_email_id: Optional[str] = None
    source_file_ref: Optional[str] = None
    family_member: Optional[str] = None
    household_member: Optional[str] = None
    registration_required: bool = False
    registration_url: Optional[str] = None
    created_at: datetime
    warranty_period: Optional[WarrantyPeriodOut] = None


class PurchaseEditRequest(BaseModel):
    """Request body for manually editing a purchase record."""

    product_name: Optional[str] = Field(None, max_length=512)
    brand: Optional[str] = Field(None, max_length=255)
    retailer: Optional[str] = Field(None, max_length=255)
    purchase_date: Optional[date] = None
    price: Optional[Decimal] = None
    family_member: Optional[str] = Field(None, max_length=100)
    registration_required: Optional[bool] = None
    registration_url: Optional[str] = Field(None, max_length=1024)
    # Warranty period overrides
    warranty_end_date: Optional[date] = None
    return_window_end_date: Optional[date] = None


class PurchasesListResponse(BaseModel):
    """Response for listing all purchases for a user."""

    user_id: uuid.UUID
    total: int
    purchases: list[PurchaseOut]


# ── Ingestion schemas ─────────────────────────────────────────────────────────

class IngestionSummary(BaseModel):
    """Returned after a batch email-fetch ingestion run."""

    user_id: uuid.UUID
    emails_scanned: int
    purchases_created: int
    purchases_failed: int
    errors: list[str] = Field(default_factory=list)


class UploadResponse(BaseModel):
    """Returned after a document upload + extraction."""

    purchase: PurchaseOut
    extraction: ExtractionResultSchema
    ocr_used: bool


# ── Auth schemas ──────────────────────────────────────────────────────────────

class OAuthCallbackResponse(BaseModel):
    """Returned to the frontend after a successful OAuth callback."""

    user_id: uuid.UUID
    email: str
    message: str = "Gmail connected successfully"


# ── Extraction test schema ────────────────────────────────────────────────────

class ExtractionTestRequest(BaseModel):
    """Raw text to run through the extraction pipeline without persisting."""

    text: str = Field(..., min_length=1, description="Email body or document text to parse")
    hint: Optional[str] = Field(
        None,
        description="Optional source hint: 'amazon', 'flipkart', etc.",
    )


# ── Alert schemas ─────────────────────────────────────────────────────────────

class AlertOut(BaseModel):
    """A single upcoming or historical alert."""

    alert_id: str
    purchase_id: str
    product_name: Optional[str] = None
    brand: Optional[str] = None
    retailer: Optional[str] = None
    alert_type: str
    fire_date: str
    days_until: int
    is_overdue: bool


class AlertsListResponse(BaseModel):
    """Response for listing alerts for a user."""

    user_id: uuid.UUID
    total: int
    alerts: list[AlertOut]


# ── Agent / chat schemas ──────────────────────────────────────────────────────

class AgentQueryRequest(BaseModel):
    """Request for the chat-style warranty agent."""

    user_id: uuid.UUID
    question: str = Field(..., min_length=1, max_length=500, description="User's natural-language question")


class AgentQueryResponse(BaseModel):
    """Response from the warranty agent."""

    answer: str
    user_id: uuid.UUID


# ── Recall schemas ────────────────────────────────────────────────────────────

class RecallOut(BaseModel):
    """A product recall record."""

    id: str
    brand: Optional[str] = None
    product_model: Optional[str] = None
    description: Optional[str] = None
    source_url: Optional[str] = None
    date_found: Optional[str] = None


class RecallCheckResponse(BaseModel):
    """Result of running a recall check for a user."""

    user_id: uuid.UUID
    purchases_checked: int
    recall_matches: int
