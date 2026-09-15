"""
Initial schema migration — creates all five Warranty Radar tables.

Revision: 0001
Tables:   users, purchases, warranty_periods, alerts, recalls

This migration was generated from app/models.py. Run with:
    alembic upgrade head

To roll back:
    alembic downgrade -1
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column(
            "google_oauth_token_encrypted",
            sa.Text,
            nullable=True,
            comment="Fernet-encrypted OAuth refresh token",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ── purchases ─────────────────────────────────────────────────────────────
    op.create_table(
        "purchases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_name", sa.String(512), nullable=True),
        sa.Column("brand", sa.String(255), nullable=True),
        sa.Column("retailer", sa.String(255), nullable=True),
        sa.Column("purchase_date", sa.Date, nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "source_type",
            sa.String(20),
            nullable=False,
            comment="'email' or 'upload'",
        ),
        sa.Column(
            "source_email_id",
            sa.String(255),
            nullable=True,
            comment="Gmail message ID — raw email body is never stored",
        ),
        sa.Column(
            "source_file_ref",
            sa.String(512),
            nullable=True,
            comment="Relative path under uploads/ — file content is not stored in DB",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchases_user_id", "purchases", ["user_id"])

    # ── warranty_periods ───────────────────────────────────────────────────────
    op.create_table(
        "warranty_periods",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchase_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("warranty_end_date", sa.Date, nullable=True),
        sa.Column("return_window_end_date", sa.Date, nullable=True),
        sa.Column(
            "confidence_score",
            sa.String(10),
            nullable=False,
            server_default="low",
            comment="'high', 'medium', or 'low'",
        ),
        sa.Column("source_snippet", sa.Text, nullable=True),
        sa.Column(
            "is_estimated",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.ForeignKeyConstraint(["purchase_id"], ["purchases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("purchase_id", name="uq_warranty_periods_purchase_id"),
    )
    op.create_index("ix_warranty_periods_purchase_id", "warranty_periods", ["purchase_id"])

    # ── alerts ────────────────────────────────────────────────────────────────
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchase_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("fire_date", sa.DateTime(timezone=False), nullable=False),
        sa.Column(
            "sent",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.ForeignKeyConstraint(["purchase_id"], ["purchases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_purchase_id", "alerts", ["purchase_id"])

    # ── recalls ───────────────────────────────────────────────────────────────
    op.create_table(
        "recalls",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand", sa.String(255), nullable=True),
        sa.Column("product_model", sa.String(512), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("date_found", sa.Date, nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recalls_brand", "recalls", ["brand"])


def downgrade() -> None:
    op.drop_table("recalls")
    op.drop_table("alerts")
    op.drop_table("warranty_periods")
    op.drop_table("purchases")
    op.drop_table("users")
