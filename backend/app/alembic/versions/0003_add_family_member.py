"""
Add missing columns to purchases table.

Revision: 0003
Parent:   0002
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("purchases", sa.Column("family_member", sa.String(100), nullable=True))
    op.add_column("purchases", sa.Column("registration_required", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("purchases", sa.Column("registration_url", sa.String(1024), nullable=True))

def downgrade() -> None:
    op.drop_column("purchases", "registration_url")
    op.drop_column("purchases", "registration_required")
    op.drop_column("purchases", "family_member")
