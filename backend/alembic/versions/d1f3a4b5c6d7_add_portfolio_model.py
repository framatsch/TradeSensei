"""add_portfolio_model

Revision ID: d1f3a4b5c6d7
Revises: c2d4a6ef9b71
Create Date: 2026-04-26 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1f3a4b5c6d7"
down_revision: str | None = "c2d4a6ef9b71"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portfolios",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("base_currency", sa.String(length=3), nullable=False),
        sa.Column("color_hex", sa.String(length=7), nullable=True),
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
        sa.UniqueConstraint("user_id", "name", name="uq_portfolios_user_name"),
        sa.CheckConstraint(
            "color_hex IS NULL OR color_hex ~ '^#[0-9A-Fa-f]{6}$'",
            name="ck_portfolios_color_hex",
        ),
    )
    op.create_index("ix_portfolios_user_id", "portfolios", ["user_id"], unique=False)

    op.add_column(
        "accounts",
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_accounts_portfolio_id_portfolios",
        "accounts",
        "portfolios",
        ["portfolio_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_accounts_portfolio_id",
        "accounts",
        ["portfolio_id"],
        unique=False,
    )

    op.execute(
        sa.text(
            """
            INSERT INTO portfolios (
                id,
                user_id,
                name,
                base_currency,
                color_hex,
                created_at,
                updated_at
            )
            SELECT
                gen_random_uuid(),
                u.id,
                'Default Portfolio',
                'USD',
                '#6366f1',
                now(),
                now()
            FROM users u
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE accounts a
            SET portfolio_id = p.id
            FROM portfolios p
            WHERE p.user_id = a.user_id
            """
        )
    )

    op.alter_column(
        "accounts",
        "portfolio_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "accounts",
        "portfolio_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.execute(sa.text("UPDATE accounts SET portfolio_id = NULL"))

    op.drop_index("ix_accounts_portfolio_id", table_name="accounts")
    op.drop_constraint(
        "fk_accounts_portfolio_id_portfolios",
        "accounts",
        type_="foreignkey",
    )
    op.drop_column("accounts", "portfolio_id")

    op.drop_index("ix_portfolios_user_id", table_name="portfolios")
    op.drop_table("portfolios")
