"""
Add WhatsApp link + purchase payment-method tables.

Revision: 0004
Parent:   0003

Both tables are brand new (no existing table is altered). The upgrade is
idempotent: the API server also runs ``CREATE TABLE IF NOT EXISTS`` for these
two tables at startup, so on a database where that already happened this
migration simply does nothing.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    if not _has_table("whatsapp_links"):
        op.create_table(
            "whatsapp_links",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("phone_number", sa.String(20), nullable=True),
            sa.Column("link_code", sa.String(12), nullable=True),
            sa.Column("link_code_expires_at", sa.DateTime(), nullable=True),
            sa.Column("linked_at", sa.DateTime(), nullable=True),
            sa.Column(
                "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
            ),
        )
        op.create_index("ix_whatsapp_links_user_id", "whatsapp_links", ["user_id"], unique=True)
        op.create_index(
            "ix_whatsapp_links_phone_number", "whatsapp_links", ["phone_number"], unique=True
        )
        op.create_index("ix_whatsapp_links_link_code", "whatsapp_links", ["link_code"])

    if not _has_table("purchase_payment_methods"):
        op.create_table(
            "purchase_payment_methods",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "purchase_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("purchases.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("issuer", sa.String(50), nullable=True),
            sa.Column("card_key", sa.String(64), nullable=True),
            sa.Column("last4", sa.String(4), nullable=True),
            sa.Column("source", sa.String(20), nullable=False, server_default="detected"),
            sa.Column("evidence", sa.String(255), nullable=True),
            sa.Column(
                "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
            ),
        )
        op.create_index(
            "ix_purchase_payment_methods_purchase_id",
            "purchase_payment_methods",
            ["purchase_id"],
            unique=True,
        )


def downgrade() -> None:
    if _has_table("purchase_payment_methods"):
        op.drop_table("purchase_payment_methods")
    if _has_table("whatsapp_links"):
        op.drop_table("whatsapp_links")

