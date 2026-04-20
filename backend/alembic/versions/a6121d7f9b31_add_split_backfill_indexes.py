"""Add partial indexes for split-aware backfill query patterns.

Revision ID: a6121d7f9b31
Revises: 51f7adace3d1
Create Date: 2026-04-19 22:20:00.000000
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a6121d7f9b31"
down_revision: str | None = "51f7adace3d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create indexes used by split-aware import backfill and orphan resolution."""
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_le_parent_active_split
        ON logical_executions (parent_id)
        WHERE origin = 'split' AND deleted = false;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_le_orphan_split_lookup
        ON logical_executions (user_id, account_id, executed_at)
        WHERE origin = 'split' AND trade_id IS NULL AND deleted = false;
        """
    )


def downgrade() -> None:
    """Drop split-aware import indexes."""
    op.execute("DROP INDEX IF EXISTS ix_le_orphan_split_lookup;")
    op.execute("DROP INDEX IF EXISTS ix_le_parent_active_split;")
