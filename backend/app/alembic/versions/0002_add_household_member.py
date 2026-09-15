"""
Add household_member column to purchases table.

Revision: 0002
Parent:   0001

This is schema groundwork for the shared-inbox feature (future milestone).
The column is nullable with a default of NULL so it is a pure additive change
and is safe to apply to a live database with existing rows.

Apply:
    alembic upgrade head

Roll back:
    alembic downgrade -1
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "purchases",
        sa.Column(
            "household_member",
            sa.String(100),
            nullable=True,
            comment=(
                "Which household member made this purchase "
                "(shared-inbox attribution, Milestone N+1)"
            ),
        ),
    )


def downgrade() -> None:
    op.drop_column("purchases", "household_member")
