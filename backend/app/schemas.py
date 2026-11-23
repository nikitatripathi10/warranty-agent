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
        None, description="Total warranty length in months (standard + additional)"
    )
    standard_warranty_months: Optional[int] = Field(
        None, description="Manufacturer / standard warranty length in months"
    )
    additional_warranty_months: Optional[int] = Field(
        None, description="Additional / extended warranty length in months"
    )
    additional_warranty_details: Optional[str] = Field(
        None, description="Additional / extended warranty details or manual entry notes"
    )
    manufacturer_doc_name: Optional[str] = Field(
        None, description="Uploaded manufacturer/standard warranty document filename"
    )
    additional_doc_name: Optional[str] = Field(
        None, description="Uploaded additional/extended warranty document filename"
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
    source_snippet: Optional[str] = Field(None, max_length=2000)


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


class EmailConnectRequest(BaseModel):
    """Direct email sign-in or connection request."""

    email: str = Field(..., min_length=3, max_length=255, description="User's email address")
    name: Optional[str] = Field(None, max_length=150, description="Optional display name")
    user_id: Optional[uuid.UUID] = Field(
        None,
        description=(
            "Workspace token previously issued to this browser. Required to reopen "
            "an existing workspace without Google verification."
        ),
    )


class EmailConnectResponse(BaseModel):
    """Returned after direct email sign-in or connection."""

    user_id: uuid.UUID
    email: str
    name: str
    has_gmail_connected: bool
    access_token: Optional[str] = None
    message: str = "Connected successfully"


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


# ── Legal Notice & Dispute Generator Schemas ─────────────────────────────────

class LegalNoticeRequest(BaseModel):
    """Request to generate a statutory pre-litigation legal notice under Consumer Protection Act 2019."""

    user_id: uuid.UUID
    grievance_type: str = Field(
        "warranty_denial",
        description="Type of grievance: 'warranty_denial', 'defective_product', 'delayed_repair', 'unfair_trade_practice'",
    )
    issue_description: Optional[str] = Field(
        None,
        description="Detailed description of defect or service deficiency experienced by consumer",
    )
    custom_demand: Optional[str] = Field(
        None,
        description="Consumer's desired relief: 'full_refund', 'replacement', 'immediate_repair_compensation'",
    )
    consumer_name: Optional[str] = Field(None, description="Name of the complainant")
    consumer_address: Optional[str] = Field(None, description="Address of the complainant")
    consumer_phone: Optional[str] = Field(None, description="Phone number of the complainant")


class LegalNoticeResponse(BaseModel):
    """Generated legal notice, NCH grievance draft, and e-Daakhil filing guidance."""

    purchase_id: uuid.UUID
    product_name: str
    brand: Optional[str] = None
    retailer: Optional[str] = None
    purchase_date: Optional[str] = None
    invoice_number: Optional[str] = None
    amount_paid: Optional[str] = None
    notice_reference: str
    legal_notice_text: str
    nch_grievance_draft: str
    statutory_sections_cited: list[str]
    edaakhil_guidance: dict
    portal_links: dict


# ── Festival Price Drop Refund Radar Schemas ─────────────────────────────────

class PriceCheckRequest(BaseModel):
    """Optional manual price override check."""

    current_sale_price: Optional[float] = Field(
        None, description="Current festival sale price observed by consumer"
    )


class PriceRadarItem(BaseModel):
    """Single item festival sale price drop opportunity."""

    purchase_id: uuid.UUID
    product_name: str
    brand: Optional[str] = None
    retailer: Optional[str] = None
    purchase_date: Optional[str] = None
    original_price: float
    current_sale_price: float
    price_drop_amount: float
    discount_percentage: float
    is_return_window_active: bool
    return_window_end_date: Optional[str] = None
    days_left_in_return_window: int
    festival_event: str
    refund_request_message: str
    direct_support_url: str
    support_channel_name: str = "Customer Support"
    product_store_url: Optional[str] = None
    whatsapp_url: Optional[str] = None
    brand_support_url: Optional[str] = None
    brand_support_name: Optional[str] = None
    brand_whatsapp_url: Optional[str] = None


class PriceRadarListResponse(BaseModel):
    """Response containing price drop opportunities across all eligible purchases."""

    user_id: uuid.UUID
    total_potential_refund: float
    active_opportunities_count: int
    festival_event: str
    items: list[PriceRadarItem]



# ── Credit-card benefit matcher schemas ──────────────────────────────────────

class CardOption(BaseModel):
    """A selectable credit card in the benefit catalogue."""

    key: str
    label: str
    issuer: str


class DetectedCardOut(BaseModel):
    """The card found on the invoice (or chosen by the user) for a purchase."""

    issuer: Optional[str] = None
    issuer_label: Optional[str] = None
    card_key: Optional[str] = None
    card_label: Optional[str] = None
    last4: Optional[str] = None
    source: str = "detected"
    evidence: Optional[str] = None


class CardBenefitOut(BaseModel):
    """What the card may add on top of the manufacturer warranty."""

    status: str = Field(
        ...,
        description=(
            "'extended_warranty' | 'purchase_protection_only' | 'no_known_benefit' | "
            "'needs_card' | 'not_eligible'"
        ),
    )
    headline: str
    card_label: Optional[str] = None
    extension_months: int = 0
    manufacturer_warranty_end: Optional[str] = None
    extended_warranty_end: Optional[str] = None
    days_until_extended_end: Optional[int] = None
    protection_summary: Optional[str] = None
    insurer: Optional[str] = None
    conditions: list[str] = Field(default_factory=list)
    claim_steps: list[str] = Field(default_factory=list)
    disclaimer: str


class CardBenefitReport(BaseModel):
    """Response of GET /purchases/{id}/card-benefits."""

    purchase_id: uuid.UUID
    detected_card: Optional[DetectedCardOut] = None
    options: list[CardOption]
    benefit: CardBenefitOut


class PaymentCardRequest(BaseModel):
    """Manually choose (or clear) the credit card used for a purchase."""

    user_id: uuid.UUID
    card_key: Optional[str] = Field(
        None, description="Catalogue key, 'other_card', or null to clear the choice"
    )
    last4: Optional[str] = Field(None, pattern=r"^\d{4}$")


# ── WhatsApp bot schemas ─────────────────────────────────────────────────────

class WhatsAppStatusOut(BaseModel):
    """Link state of the WhatsApp bot for a workspace."""

    configured: bool
    linked: bool
    phone_masked: Optional[str] = None
    bot_number: Optional[str] = None
    pending_code: bool = False
    provider: Optional[str] = None
    sandbox_join_code: Optional[str] = None
    sandbox_join_link: Optional[str] = None


class WhatsAppLinkCodeOut(BaseModel):
    """A short-lived code the user sends to the bot as 'LINK <code>'."""

    code: str
    expires_in_minutes: int
    bot_number: Optional[str] = None
    deep_link: Optional[str] = None
    provider: Optional[str] = None
    sandbox_join_code: Optional[str] = None
    sandbox_join_link: Optional[str] = None


# ── Forward-to-email schemas ─────────────────────────────────────────────────

class InboundAttachment(BaseModel):
    """A PDF / image attached to a forwarded email (base64 encoded by the worker)."""

    filename: str = "attachment"
    content_type: str = ""
    content_base64: str


class InboundEmailPayload(BaseModel):
    """Body POSTed by the Cloudflare Email Worker for every forwarded email."""

    model_config = ConfigDict(populate_by_name=True)

    to: str = Field(..., description="Envelope recipient, e.g. bills+<token>@yourdomain.in")
    sender: str = Field("", alias="from")
    subject: str = ""
    text: str = ""
    html: str = ""
    message_id: str = ""
    attachments: list[InboundAttachment] = Field(default_factory=list)


class InboundEmailResponse(BaseModel):
    """'saved' | 'duplicate' | 'unreadable' | 'forwarding_confirmation' | 'ignored'."""

    status: str
    product_name: Optional[str] = None


class ForwardingAddressOut(BaseModel):
    """The user's private forwarding address and any pending Gmail confirmation code."""

    enabled: bool
    address: Optional[str] = None
    domain: Optional[str] = None
    verification_code: Optional[str] = None


# ── Production hardening schemas ─────────────────────────────────────────────

class InvoiceUrlResponse(BaseModel):
    """Short-lived download link for a stored invoice (when using cloud storage)."""

    purchase_id: uuid.UUID
    url: Optional[str] = None
    storage: str = "local"
