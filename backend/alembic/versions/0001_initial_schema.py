"""Initial schema — trades table + TimescaleDB hypertable.

Revision ID: 0001
Revises:
Create Date: 2026-03-14 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the ``trades`` table, its indexes, and the TimescaleDB hypertable."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # ── Enum types ─────────────────────────────────────────────────────────────
    direction_enum = postgresql.ENUM(
        "LONG", "SHORT", name="direction_enum", create_type=False
    )
    asset_class_enum = postgresql.ENUM(
        "EQUITY",
        "OPTION",
        "FUTURE",
        "FOREX",
        "CRYPTO",
        name="asset_class_enum",
        create_type=False,
    )
    # op.get_bind() is deprecated in Alembic 1.12+; migrate when project upgrades to alembic 2.x
    direction_enum.create(op.get_bind(), checkfirst=True)
    # op.get_bind() is deprecated in Alembic 1.12+; migrate when project upgrades to alembic 2.x
    asset_class_enum.create(op.get_bind(), checkfirst=True)

    # ── Table ──────────────────────────────────────────────────────────────────
    op.create_table(
        "trades",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column(
            "direction",
            direction_enum,
            nullable=False,
        ),
        sa.Column(
            "asset_class",
            asset_class_enum,
            nullable=False,
        ),
        sa.Column("quantity", sa.Numeric(18, 8), nullable=False),
        sa.Column("entry_price", sa.Numeric(18, 8), nullable=False),
        sa.Column("exit_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("stop_loss", sa.Numeric(18, 8), nullable=True),
        sa.Column("take_profit", sa.Numeric(18, 8), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pnl", sa.Numeric(18, 8), nullable=True),
        sa.Column(
            "commission",
            sa.Numeric(18, 8),
            nullable=False,
            server_default="0",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
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
    )

    # ── Indexes ────────────────────────────────────────────────────────────────
    op.create_index("ix_trades_symbol", "trades", ["symbol"])
    op.create_index("ix_trades_opened_at", "trades", ["opened_at"])
    op.create_index("ix_trades_closed_at", "trades", ["closed_at"])

    # ── updated_at trigger ────────────────────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trades_updated_at
        BEFORE UPDATE ON trades
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)



def downgrade() -> None:
    """Drop the ``trades`` table and its enum types."""
    op.execute("DROP TRIGGER IF EXISTS trades_updated_at ON trades")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column")
    op.drop_index("ix_trades_closed_at", table_name="trades")
    op.drop_index("ix_trades_opened_at", table_name="trades")
    op.drop_index("ix_trades_symbol", table_name="trades")
    op.drop_table("trades")
    # op.get_bind() is deprecated in Alembic 1.12+; migrate when project upgrades to alembic 2.x
    sa.Enum(name="direction_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="asset_class_enum").drop(op.get_bind(), checkfirst=True)
