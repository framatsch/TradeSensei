"""Add account_number column to accounts table.

Revision ID: 088b78227343
Revises: 0011
Create Date: 2026-03-21 17:43:01.245458

Changes:
- ``accounts.account_number``: Add nullable VARCHAR(50) column for the broker
  account number (e.g. "U1234567"). Existing rows get NULL.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "088b78227343"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add account_number column to the accounts table."""
    op.add_column(
        "accounts",
        sa.Column("account_number", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    """Drop account_number column from the accounts table."""
    op.drop_column("accounts", "account_number")
