"""
Add the forward-to-email inbox table.

Revision: 0005
Parent:   0004

Brand new table (no existing table is altered). Idempotent: the API server also
runs ``CREATE TABLE IF NOT EXISTS`` for it at startup, so on a database where
that already happened this migration does nothing.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    if _has_table("email_inboxes"):
        return
    op.create_table(
        "email_inboxes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("inbox_token", sa.String(32), nullable=False),
        sa.Column("verification_code", sa.String(16), nullable=True),
        sa.Column("verification_received_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_email_inboxes_user_id", "email_inboxes", ["user_id"], unique=True)
    op.create_index("ix_email_inboxes_inbox_token", "email_inboxes", ["inbox_token"], unique=True)


def downgrade() -> None:
    if _has_table("email_inboxes"):
        op.drop_table("email_inboxes")

