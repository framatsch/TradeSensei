"""add_daily_checkin_tables

Revision ID: a7c3f61b9d20
Revises: d1f3a4b5c6d7
Create Date: 2026-05-01 10:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c3f61b9d20"
down_revision: str | None = "d1f3a4b5c6d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "checkin_field_definitions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column(
            "field_type",
            sa.Enum(
                "integer",
                "boolean",
                name="checkin_field_type_enum",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "field_name", name="uq_checkin_field_user_name"),
    )
    op.create_index(
        "ix_checkin_field_definitions_user_id",
        "checkin_field_definitions",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "market_phase_definitions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("color_hex", sa.String(length=7), nullable=False, server_default="#6366f1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_market_phase_user_name"),
    )
    op.create_index(
        "ix_market_phase_definitions_user_id",
        "market_phase_definitions",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "daily_checkins",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("market_phase", sa.String(length=50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("news_links", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column(
            "screenshot_urls",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("custom_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.UniqueConstraint("user_id", "date", name="uq_daily_checkin_user_date"),
    )
    op.create_index("ix_daily_checkins_user_id", "daily_checkins", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_daily_checkins_user_id", table_name="daily_checkins")
    op.drop_table("daily_checkins")

    op.drop_index("ix_market_phase_definitions_user_id", table_name="market_phase_definitions")
    op.drop_table("market_phase_definitions")

    op.drop_index("ix_checkin_field_definitions_user_id", table_name="checkin_field_definitions")
    op.drop_table("checkin_field_definitions")
    op.execute("DROP TYPE IF EXISTS checkin_field_type_enum;")
