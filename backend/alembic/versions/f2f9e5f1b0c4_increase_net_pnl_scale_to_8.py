"""increase_net_pnl_scale_to_8

Revision ID: f2f9e5f1b0c4
Revises: 88deb49a9f12
Create Date: 2026-04-04 23:35:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2f9e5f1b0c4"
down_revision: Union[str, None] = "88deb49a9f12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Increase net PnL precision scale to 8 decimals."""
    op.alter_column(
        "trades",
        "net_pnl",
        existing_type=sa.Numeric(precision=18, scale=4),
        type_=sa.Numeric(precision=18, scale=8),
        existing_nullable=True,
    )
    op.alter_column(
        "trades",
        "net_pnl_eur",
        existing_type=sa.Numeric(precision=18, scale=4),
        type_=sa.Numeric(precision=18, scale=8),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Restore net PnL precision scale back to 4 decimals."""
    op.alter_column(
        "trades",
        "net_pnl_eur",
        existing_type=sa.Numeric(precision=18, scale=8),
        type_=sa.Numeric(precision=18, scale=4),
        existing_nullable=True,
    )
    op.alter_column(
        "trades",
        "net_pnl",
        existing_type=sa.Numeric(precision=18, scale=8),
        type_=sa.Numeric(precision=18, scale=4),
        existing_nullable=True,
    )
