"""
SQLAlchemy ORM models for Warranty Radar.

Schema overview
───────────────
  users              — one row per Google-authenticated user
  purchases          — one row per detected purchase (email or upload source)
  warranty_periods   — warranty + return-window data for each purchase
  alerts             — scheduled alert records (Milestone 3 logic)
  recalls            — product recall records   (Milestone 3 logic)

All primary keys are UUIDs generated server-side.
All timestamps are UTC.
"""

import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ── Valid column values (enforced at application layer) ──────────────────────
# source_type:       'email' | 'upload'
# confidence_score:  'high'  | 'medium' | 'low'


# ── Models ────────────────────────────────────────────────────────────────────

class User(Base):
    """Authenticated user — one record per Google account."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    google_oauth_token_encrypted: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Fernet-encrypted OAuth refresh token"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, server_default=func.now()
    )

    # Relationships
    purchases: Mapped[list["Purchase"]] = relationship(
        "Purchase", back_populates="user", cascade="all, delete-orphan"
    )
    whatsapp_link: Mapped[Optional["WhatsAppLink"]] = relationship(
        "WhatsAppLink", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    email_inbox: Mapped[Optional["EmailInbox"]] = relationship(
        "EmailInbox", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} email={self.email!r}>"


class Purchase(Base):
    """A detected purchase, sourced from Gmail or an uploaded document."""

    __tablename__ = "purchases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_name: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    brand: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    retailer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    purchase_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)

    # Source tracking
    source_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="'email', 'upload', or 'whatsapp'",
    )
    source_email_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Gmail message ID — raw email body is never stored",
    )
    source_file_ref: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Relative path under uploads/ — file content is not stored in DB",
    )

    # India-specific feature fields
    family_member: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Tag for family/shared-inbox mode (e.g. 'Self', 'Dad', 'Mom', 'Sibling')",
    )
    # Schema groundwork: attribute purchases to a specific household member sharing one inbox.
    # Populated by a later milestone; NULL until then.
    household_member: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        default=None,
        comment="Which household member made this purchase (shared-inbox attribution, Milestone N+1)",
    )
    registration_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="True if brand requires product registration to activate warranty",
    )
    registration_url: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
        comment="Direct link to brand warranty registration portal",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="purchases")
    warranty_period: Mapped[Optional["WarrantyPeriod"]] = relationship(
        "WarrantyPeriod", back_populates="purchase", uselist=False, cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert", back_populates="purchase", cascade="all, delete-orphan"
    )
    payment_method: Mapped[Optional["PurchasePaymentMethod"]] = relationship(
        "PurchasePaymentMethod",
        back_populates="purchase",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Purchase id={self.id} product={self.product_name!r} source={self.source_type!r}>"


class WarrantyPeriod(Base):
    """Warranty and return-window metadata extracted for a purchase."""

    __tablename__ = "warranty_periods"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    purchase_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchases.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One warranty record per purchase
        index=True,
    )
    warranty_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    return_window_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    confidence_score: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="low",
        comment="'high', 'medium', or 'low' — set by extraction pipeline",
    )
    source_snippet: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="The raw text fragment that drove the extraction",
    )
    is_estimated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True if warranty/return dates were inferred, not stated explicitly",
    )

    # Relationships
    purchase: Mapped["Purchase"] = relationship("Purchase", back_populates="warranty_period")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<WarrantyPeriod purchase_id={self.purchase_id} "
            f"confidence={self.confidence_score!r}>"
        )


class Alert(Base):
    """
    Scheduled alerts — table created now, logic implemented in Milestone 3.

    alert_type examples: 'return_window_expiry', 'warranty_expiry'
    """

    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    purchase_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    fire_date: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    purchase: Mapped["Purchase"] = relationship("Purchase", back_populates="alerts")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Alert id={self.id} type={self.alert_type!r} sent={self.sent}>"


class Recall(Base):
    """
    Product recall records — table created now, logic implemented in Milestone 3.
    """

    __tablename__ = "recalls"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    brand: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    product_model: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    date_found: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Recall id={self.id} brand={self.brand!r} model={self.product_model!r}>"


# ── WhatsApp bot + credit-card benefit tables ────────────────────────────────
# These two tables are intentionally *new tables* (no new columns on existing
# tables) so they can be created safely with CREATE TABLE IF NOT EXISTS on a
# live database that is migrated manually. See main.py lifespan + migration 0004.


class WhatsAppLink(Base):
    """
    Links one WhatsApp number to one workspace (user).

    A row starts life as a pending link (``link_code`` set, ``phone_number``
    NULL). When the user sends ``LINK <code>`` from WhatsApp, the number is
    bound and the code is cleared, which proves the sender controls the account.
    """

    __tablename__ = "whatsapp_links"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    phone_number: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        unique=True,
        index=True,
        comment="WhatsApp number as digits only, with country code (e.g. 919876543210)",
    )
    link_code: Mapped[Optional[str]] = mapped_column(String(12), nullable=True, index=True)
    link_code_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    linked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="whatsapp_link")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<WhatsAppLink user={self.user_id} linked={self.phone_number is not None}>"


class PurchasePaymentMethod(Base):
    """
    Which credit card paid for a purchase — drives the card-benefit matcher.

    Only the issuer, an optional catalogue card key, the last four digits and a
    short evidence snippet are stored. Raw invoice/email text is never stored.
    ``source`` is 'detected' (found in the invoice) or 'manual' (user picked it).
    """

    __tablename__ = "purchase_payment_methods"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    purchase_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchases.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    issuer: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    card_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    last4: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="detected")
    evidence: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, server_default=func.now()
    )

    purchase: Mapped["Purchase"] = relationship("Purchase", back_populates="payment_method")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PurchasePaymentMethod purchase={self.purchase_id} card={self.card_key!r}>"


class EmailInbox(Base):
    """
    A user's private forwarding address: ``bills+<inbox_token>@<INBOUND_EMAIL_DOMAIN>``.

    Forwarding an order / invoice email there saves it to the user's vault - no
    Gmail OAuth and no Google security audit needed. The token is unguessable and
    can be rotated at any time.

    ``verification_code`` holds the most recent Gmail "forwarding confirmation"
    code, because Gmail will not auto-forward until the user enters that code.
    """

    __tablename__ = "email_inboxes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    inbox_token: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    verification_code: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    verification_received_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="email_inbox")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<EmailInbox user={self.user_id}>"
