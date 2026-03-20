"""widen_symbol_max_length_to_30

Revision ID: f08b3ef4719a
Revises: 088b78227343
Create Date: 2026-03-22 16:04:09.812177

Widens the trades.symbol VARCHAR column from 20 to 30 characters to support
full OCC option symbol format (21 chars, e.g. 'CHTR  251003P00240000').
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f08b3ef4719a"
down_revision: str | None = "088b78227343"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "trades",
        "symbol",
        existing_type=sa.VARCHAR(length=20),
        type_=sa.String(length=30),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "trades",
        "symbol",
        existing_type=sa.String(length=30),
        type_=sa.VARCHAR(length=20),
        existing_nullable=False,
    )
