"""reporting layer saved dashboard views and analytics indexes

Revision ID: 2f9b7d3a91cd
Revises: c5d8e9f2a312
Create Date: 2026-05-01 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2f9b7d3a91cd"
down_revision: str | None = "c5d8e9f2a312"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "saved_dashboard_views",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "filter_config",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["portfolio_id"],
            ["portfolios.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_saved_dashboard_views_portfolio_id",
        "saved_dashboard_views",
        ["portfolio_id"],
        unique=False,
    )
    op.create_index(
        "ix_saved_dashboard_views_portfolio_user",
        "saved_dashboard_views",
        ["portfolio_id", "user_id"],
        unique=False,
    )
    op.create_index(
        "ix_saved_dashboard_views_user_id",
        "saved_dashboard_views",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_trades_user_account_closed_at",
        "trades",
        ["user_id", "account_id", "closed_at"],
        unique=False,
    )
    op.create_index(
        "ix_trades_user_account_playbook_closed_at",
        "trades",
        ["user_id", "account_id", "playbook_id", "closed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_trades_user_account_playbook_closed_at", table_name="trades")
    op.drop_index("ix_trades_user_account_closed_at", table_name="trades")
    op.drop_index(
        "ix_saved_dashboard_views_user_id",
        table_name="saved_dashboard_views",
    )
    op.drop_index(
        "ix_saved_dashboard_views_portfolio_user",
        table_name="saved_dashboard_views",
    )
    op.drop_index(
        "ix_saved_dashboard_views_portfolio_id",
        table_name="saved_dashboard_views",
    )
    op.drop_table("saved_dashboard_views")
