"""add_tradingview_link_and_screenshots_to_trade

Revision ID: 79a75d5a2af2
Revises: f91cc12066ce
Create Date: 2026-03-22 16:51:21.928461

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "79a75d5a2af2"
down_revision: str | None = "f91cc12066ce"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("trades", sa.Column("tradingview_link", sa.String(), nullable=True))
    op.add_column(
        "trades",
        sa.Column(
            "screenshots",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("trades", "screenshots")
    op.drop_column("trades", "tradingview_link")
