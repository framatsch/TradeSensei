"""add_is_mixed_execution_to_logical_executions

Revision ID: f1db1278b353
Revises: 646da0a15710
Create Date: 2026-05-17 10:03:19.074536

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f1db1278b353'
down_revision: str | None = '646da0a15710'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'logical_executions',
        sa.Column(
            'is_mixed_execution',
            sa.Boolean(),
            server_default='false',
            nullable=False,
            comment=(
                'True when the broker reported a position flip (C;O or O;C) for this'
                ' execution.  The FIFO aggregator uses this to allow the closing portion'
                ' to leave a new open lot rather than treating the remainder as orphaned.'
            ),
        ),
    )


def downgrade() -> None:
    op.drop_column('logical_executions', 'is_mixed_execution')
