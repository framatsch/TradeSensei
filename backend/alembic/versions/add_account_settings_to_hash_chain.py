"""Add account settings column (hash-chain branch).

Adds the nullable JSONB ``settings`` column to the ``accounts`` table for
databases that followed the hash-named migration chain (e.g. the test DB)
and therefore never ran migration ``0012``.

Uses ``IF NOT EXISTS`` semantics via a try/except so the upgrade is safe
to run on databases that already have the column (e.g. production DB
after ``0012`` was applied via the numbered chain).

Revision ID: a1b2c3d4e5f6
Revises: 19c126941032
Create Date: 2026-03-23 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "19c126941032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nullable JSONB settings column to accounts if not present."""
    # Use raw DDL with IF NOT EXISTS so this migration is idempotent on
    # databases that already have the column from the numbered chain.
    op.execute(sa.text("ALTER TABLE accounts ADD COLUMN IF NOT EXISTS settings JSONB"))


def downgrade() -> None:
    """Drop the settings column from accounts."""
    op.drop_column("accounts", "settings")
