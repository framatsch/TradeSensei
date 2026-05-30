"""drop is_modelbook from trades and daily_checkins

Revision ID: 1f1fe4f274ae
Revises: b3c4d5e6f7a8
Create Date: 2026-05-30 12:57:25.228056

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f1fe4f274ae'
down_revision: Union[str, None] = 'b3c4d5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("trades", "is_modelbook")
    op.drop_column("daily_checkins", "is_modelbook")


def downgrade() -> None:
    op.add_column(
        "daily_checkins",
        sa.Column(
            "is_modelbook",
            sa.Boolean(),
            server_default="false",
            nullable=False,
            comment="True if this check-in is starred in the Model Book.",
        ),
    )
    op.add_column(
        "trades",
        sa.Column(
            "is_modelbook",
            sa.Boolean(),
            server_default="false",
            nullable=False,
            comment="True if this trade is starred in the Model Book.",
        ),
    )
