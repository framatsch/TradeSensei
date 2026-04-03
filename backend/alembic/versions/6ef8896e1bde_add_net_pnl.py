"""add net_pnl

Revision ID: 6ef8896e1bde
Revises: 28989209dc97
Create Date: 2026-04-03 21:38:10.739877

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6ef8896e1bde"
down_revision: Union[str, None] = "28989209dc97"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "trades",
        sa.Column("net_pnl", sa.Numeric(precision=18, scale=4), nullable=True),
    )
    op.add_column(
        "trades",
        sa.Column(
            "net_pnl_eur",
            sa.Numeric(precision=18, scale=4),
            nullable=True,
            comment="Realised net P&L converted to EUR at the Bundesbank daily rate on the trade date.",
        ),
    )
    op.execute("UPDATE trades SET net_pnl = pnl - commission WHERE pnl IS NOT NULL")


def downgrade() -> None:
    op.drop_column("trades", "net_pnl_eur")
    op.drop_column("trades", "net_pnl")
