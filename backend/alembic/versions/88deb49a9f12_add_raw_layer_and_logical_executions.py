"""add_raw_layer_and_logical_executions

Adds the immutable raw-data layer (broker_raw_transactions), the mutable
logical execution layer (logical_executions), and the junction table
(transaction_execution_mappings) that links the two.  Also adds the
``has_conflict`` flag to the ``trades`` table.

Revision ID: 88deb49a9f12
Revises: 6ef8896e1bde
Create Date: 2026-04-04 18:27:42.197612

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "88deb49a9f12"
down_revision: Union[str, None] = "6ef8896e1bde"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply the raw-layer and logical-execution schema additions."""
    # ── New enum types ────────────────────────────────────────────────────────
    execution_status_enum = postgresql.ENUM(
        "imported",
        "manual",
        "merged",
        "split",
        name="execution_status_enum",
        create_type=True,
    )
    execution_status_enum.create(op.get_bind(), checkfirst=True)

    # ── broker_raw_transactions ───────────────────────────────────────────────
    op.create_table(
        "broker_raw_transactions",
        sa.Column(
            "id",
            sa.String(length=200),
            nullable=False,
            comment=(
                "Composite broker execution ID: '{broker_type}:{transaction_id}'. "
                "Used as idempotency key for re-imports."
            ),
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=True),
        sa.Column(
            "broker_type",
            sa.String(length=50),
            nullable=False,
            comment="Short broker identifier, e.g. 'ibkr' or 'schwab'.",
        ),
        sa.Column("symbol", sa.String(length=30), nullable=False),
        sa.Column(
            "conid",
            sa.String(length=50),
            nullable=True,
            comment="Broker contract identifier (IBKR conid).",
        ),
        sa.Column("asset_class", sa.String(length=20), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column(
            "quantity",
            sa.Numeric(precision=18, scale=8),
            nullable=False,
            comment="Absolute execution quantity (always positive).",
        ),
        sa.Column(
            "price",
            sa.Numeric(precision=18, scale=8),
            nullable=False,
            comment="Execution price per unit.",
        ),
        sa.Column(
            "commission",
            sa.Numeric(precision=18, scale=8),
            server_default="0",
            nullable=False,
            comment="Absolute commission charged for this execution.",
        ),
        sa.Column(
            "executed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Timestamp of the execution (UTC).",
        ),
        sa.Column(
            "pnl",
            sa.Numeric(precision=18, scale=8),
            nullable=True,
            comment="Broker-reported realised P&L (None for opening legs).",
        ),
        sa.Column(
            "currency",
            sa.String(length=3),
            nullable=True,
            comment="ISO-4217 currency code (e.g. 'USD').",
        ),
        sa.Column(
            "multiplier",
            sa.Integer(),
            server_default="1",
            nullable=False,
            comment="Contract multiplier (1 for equities, >1 for futures/options).",
        ),
        sa.Column(
            "raw_data",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
            comment="Full raw attribute dictionary from the broker source file.",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_brt_user_id", "broker_raw_transactions", ["user_id"])
    op.create_index("ix_brt_account_id", "broker_raw_transactions", ["account_id"])
    op.create_index("ix_brt_symbol", "broker_raw_transactions", ["symbol"])
    op.create_index("ix_brt_executed_at", "broker_raw_transactions", ["executed_at"])
    op.create_index("ix_brt_conid", "broker_raw_transactions", ["conid"])
    op.create_index("ix_brt_broker_type", "broker_raw_transactions", ["broker_type"])

    # ── logical_executions ────────────────────────────────────────────────────
    op.create_table(
        "logical_executions",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=True),
        sa.Column("symbol", sa.String(length=30), nullable=False),
        sa.Column(
            "conid",
            sa.String(length=50),
            nullable=True,
            comment="Broker contract identifier (IBKR conid).",
        ),
        sa.Column(
            "asset_class",
            postgresql.ENUM(
                "EQUITY",
                "OPTION",
                "FUTURE",
                "FOREX",
                "CRYPTO",
                name="asset_class_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "direction",
            postgresql.ENUM(
                "LONG",
                "SHORT",
                name="direction_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "quantity",
            sa.Numeric(precision=18, scale=8),
            nullable=False,
            comment="Execution quantity (absolute, always positive).",
        ),
        sa.Column(
            "price",
            sa.Numeric(precision=18, scale=8),
            nullable=False,
            comment="Execution price per unit.",
        ),
        sa.Column(
            "commission",
            sa.Numeric(precision=18, scale=8),
            server_default="0",
            nullable=False,
            comment="Commission for this execution leg.",
        ),
        sa.Column(
            "executed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Timestamp of the execution (UTC).",
        ),
        sa.Column(
            "pnl",
            sa.Numeric(precision=18, scale=8),
            nullable=True,
            comment="Broker-reported realised P&L (None for opening legs).",
        ),
        sa.Column(
            "pnl_eur",
            sa.Numeric(precision=18, scale=8),
            nullable=True,
            comment="Realised P&L converted to EUR at the Bundesbank daily rate.",
        ),
        sa.Column(
            "currency",
            sa.String(length=3),
            nullable=True,
            comment="ISO-4217 currency code (e.g. 'USD').",
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "imported",
                "manual",
                "merged",
                "split",
                name="execution_status_enum",
                create_type=False,
            ),
            server_default="imported",
            nullable=False,
            comment="Lineage status: imported | manual | merged | split.",
        ),
        sa.Column(
            "trade_id",
            sa.UUID(),
            nullable=True,
            comment=(
                "Aggregated Trade this execution was assigned to. "
                "None until the aggregator runs."
            ),
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
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["trade_id"], ["trades.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_le_user_id", "logical_executions", ["user_id"])
    op.create_index("ix_le_account_id", "logical_executions", ["account_id"])
    op.create_index("ix_le_symbol", "logical_executions", ["symbol"])
    op.create_index("ix_le_executed_at", "logical_executions", ["executed_at"])
    op.create_index("ix_le_conid", "logical_executions", ["conid"])
    op.create_index("ix_le_status", "logical_executions", ["status"])
    op.create_index("ix_le_trade_id", "logical_executions", ["trade_id"])

    # ── transaction_execution_mappings ────────────────────────────────────────
    op.create_table(
        "transaction_execution_mappings",
        sa.Column("raw_transaction_id", sa.String(length=200), nullable=False),
        sa.Column("logical_execution_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["logical_execution_id"],
            ["logical_executions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["raw_transaction_id"],
            ["broker_raw_transactions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("raw_transaction_id", "logical_execution_id"),
    )

    # ── trades.has_conflict ───────────────────────────────────────────────────
    op.add_column(
        "trades",
        sa.Column(
            "has_conflict",
            sa.Boolean(),
            server_default="false",
            nullable=False,
            comment=(
                "When True, the aggregated position does not reconcile with the "
                "broker's <OpenPosition> block.  The trade is flagged for manual "
                "review instead of being force-closed."
            ),
        ),
    )


def downgrade() -> None:
    """Reverse the raw-layer and logical-execution schema additions."""
    op.drop_column("trades", "has_conflict")
    op.drop_table("transaction_execution_mappings")
    op.drop_index("ix_le_trade_id", table_name="logical_executions")
    op.drop_index("ix_le_status", table_name="logical_executions")
    op.drop_index("ix_le_conid", table_name="logical_executions")
    op.drop_index("ix_le_executed_at", table_name="logical_executions")
    op.drop_index("ix_le_symbol", table_name="logical_executions")
    op.drop_index("ix_le_account_id", table_name="logical_executions")
    op.drop_index("ix_le_user_id", table_name="logical_executions")
    op.drop_table("logical_executions")
    op.drop_index("ix_brt_broker_type", table_name="broker_raw_transactions")
    op.drop_index("ix_brt_conid", table_name="broker_raw_transactions")
    op.drop_index("ix_brt_executed_at", table_name="broker_raw_transactions")
    op.drop_index("ix_brt_symbol", table_name="broker_raw_transactions")
    op.drop_index("ix_brt_account_id", table_name="broker_raw_transactions")
    op.drop_index("ix_brt_user_id", table_name="broker_raw_transactions")
    op.drop_table("broker_raw_transactions")
    # Drop the enum type we created
    op.execute("DROP TYPE IF EXISTS execution_status_enum")
