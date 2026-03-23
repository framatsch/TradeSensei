"""Add JSONB settings column to accounts table.

Stores per-account import/sync preferences (sync_days, flex_from_date_preset,
flex_custom_from_date) as a nullable JSONB blob.  A NULL value is treated as
"use defaults" by the application layer.

Revision ID: 0012
Revises: 0011
Create Date: 2026-03-23 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nullable JSONB settings column to accounts."""
    op.add_column(
        "accounts",
        sa.Column(
            "settings",
            JSONB,
            nullable=True,
            comment=(
                "Per-account import/sync settings. "
                "Keys: sync_days (int), flex_from_date_preset (str), "
                "flex_custom_from_date (str YYYYMMDD or null). "
                "NULL means use application defaults."
            ),
        ),
    )


def downgrade() -> None:
    """Drop the settings column from accounts."""
    op.drop_column("accounts", "settings")
