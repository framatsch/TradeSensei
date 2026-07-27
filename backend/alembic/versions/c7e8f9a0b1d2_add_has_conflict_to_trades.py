"""add_has_conflict_to_trades

Revision ID: c7e8f9a0b1d2
Revises: f3db6ff88b06
Create Date: 2026-07-26 20:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c7e8f9a0b1d2'
down_revision: str | None = 'f3db6ff88b06'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'trades',
        sa.Column(
            'has_conflict',
            sa.Boolean(),
            server_default='false',
            nullable=False,
            comment=(
                'True when the FIFO aggregator detected an unlinked duplicate'
                ' pair (an imported leg and an unlinked manual leg sharing'
                ' symbol, executed_at, direction, quantity, and price).'
                ' Surfacing signal only — see the execution-overwrite-protection spec.'
            ),
        ),
    )


def downgrade() -> None:
    op.drop_column('trades', 'has_conflict')
