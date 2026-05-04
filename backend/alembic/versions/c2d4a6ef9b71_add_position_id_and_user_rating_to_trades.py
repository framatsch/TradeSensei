"""Add position_id and user_rating to trades.

Revision ID: c2d4a6ef9b71
Revises: a6121d7f9b31
Create Date: 2026-04-20 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2d4a6ef9b71"
down_revision: str | None = "a6121d7f9b31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add business-position and rating fields to trades."""
    op.add_column(
        "trades",
        sa.Column(
            "position_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
    )
    op.add_column(
        "trades",
        sa.Column(
            "user_rating",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_index("ix_trades_position_id", "trades", ["position_id"], unique=False)
    op.create_index(
        "ix_trades_user_position",
        "trades",
        ["user_id", "position_id"],
        unique=False,
    )
    op.create_check_constraint(
        "ck_trades_user_rating_range",
        "trades",
        "user_rating IS NULL OR (user_rating BETWEEN 1 AND 5)",
    )


def downgrade() -> None:
    """Remove business-position and rating fields from trades."""
    op.drop_constraint("ck_trades_user_rating_range", "trades", type_="check")
    op.drop_index("ix_trades_user_position", table_name="trades")
    op.drop_index("ix_trades_position_id", table_name="trades")
    op.drop_column("trades", "user_rating")
    op.drop_column("trades", "position_id")
