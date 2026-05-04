"""add_market_index_definitions

Revision ID: aa41b963f861
Revises: c5d8e9f2a312
Create Date: 2026-05-04 22:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "aa41b963f861"
down_revision: str | None = "e3a9f3db71c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_index_definitions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("tradingview_url", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "symbol", name="uq_market_index_user_symbol"),
    )
    op.create_index(
        "ix_market_index_definitions_user_id",
        "market_index_definitions",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "checkin_market_indices",
        sa.Column("checkin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("index_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["checkin_id"],
            ["daily_checkins.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["index_id"],
            ["market_index_definitions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("checkin_id", "index_id"),
    )


def downgrade() -> None:
    op.drop_table("checkin_market_indices")
    op.drop_index(
        "ix_market_index_definitions_user_id",
        table_name="market_index_definitions",
    )
    op.drop_table("market_index_definitions")
