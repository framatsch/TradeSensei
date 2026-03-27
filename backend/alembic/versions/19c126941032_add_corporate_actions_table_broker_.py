"""add_corporate_actions_table_broker_conid_to_trades

Revision ID: 19c126941032
Revises: 79a75d5a2af2
Create Date: 2026-03-22 21:56:30.566263

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "19c126941032"
down_revision: str | None = "79a75d5a2af2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create the corporate_actions table.
    op.create_table(
        "corporate_actions",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("symbol", sa.String(length=30), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "ratio",
            sa.Numeric(precision=18, scale=8),
            nullable=False,
            comment=(
                "Split ratio: >1 for a forward split (e.g. 2.0 = 2:1), "
                "<1 for a reverse split (e.g. 0.05 = 1:20)."
            ),
        ),
        sa.Column(
            "old_conid",
            sa.String(length=50),
            nullable=True,
            comment="Broker contract ID before the split (IBKR-specific).",
        ),
        sa.Column(
            "new_conid",
            sa.String(length=50),
            nullable=True,
            comment="Broker contract ID after the split (IBKR-specific).",
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_corporate_actions_date", "corporate_actions", ["date"], unique=False
    )
    op.create_index(
        "ix_corporate_actions_symbol", "corporate_actions", ["symbol"], unique=False
    )
    op.create_index(
        "ix_corporate_actions_user_id", "corporate_actions", ["user_id"], unique=False
    )

    # Add broker_conid and is_manually_edited columns to trades.
    op.add_column(
        "trades",
        sa.Column(
            "broker_conid",
            sa.String(length=50),
            nullable=True,
            comment="External broker contract identifier (e.g. IBKR conid).",
        ),
    )
    op.add_column(
        "trades",
        sa.Column(
            "is_manually_edited",
            sa.Boolean(),
            server_default="false",
            nullable=False,
            comment=(
                "When True, this trade was manually corrected and will be "
                "skipped on subsequent broker re-imports."
            ),
        ),
    )
    op.create_index("ix_trades_broker_conid", "trades", ["broker_conid"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_trades_broker_conid", table_name="trades")
    op.drop_column("trades", "is_manually_edited")
    op.drop_column("trades", "broker_conid")

    op.drop_index("ix_corporate_actions_user_id", table_name="corporate_actions")
    op.drop_index("ix_corporate_actions_symbol", table_name="corporate_actions")
    op.drop_index("ix_corporate_actions_date", table_name="corporate_actions")
    op.drop_table("corporate_actions")
