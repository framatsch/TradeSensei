"""Add currency + pnl_eur to trades; add fx_rates table for EUR/USD caching.

Adds two nullable columns to ``trades`` for German tax reporting (Anlage KAP):
- ``currency VARCHAR(3)``: ISO-4217 denomination of the trade (e.g. ``"USD"``)
- ``pnl_eur NUMERIC(18,8)``: Realised P&L converted to EUR at the official
  Bundesbank exchange rate on the trade date.

Also creates the ``fx_rates`` table, which caches daily EUR/USD exchange rates
fetched from the Deutsche Bundesbank Statistical Data Warehouse API so that
re-imports do not trigger redundant HTTP requests.

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-15 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add currency/pnl_eur to trades and create fx_rates table."""

    # ── trades: currency column ────────────────────────────────────────────────
    op.add_column(
        "trades",
        sa.Column(
            "currency",
            sa.String(3),
            nullable=True,
            comment="ISO-4217 currency code of the trade (e.g. USD)",
        ),
    )

    # ── trades: pnl_eur column ─────────────────────────────────────────────────
    op.add_column(
        "trades",
        sa.Column(
            "pnl_eur",
            sa.Numeric(18, 8),
            nullable=True,
            comment=(
                "Realised P&L converted to EUR at the Bundesbank daily rate "
                "on the trade date. NULL for open trades or when rate unavailable."
            ),
        ),
    )

    # ── fx_rates table ─────────────────────────────────────────────────────────
    op.create_table(
        "fx_rates",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column(
            "date",
            sa.Date(),
            nullable=False,
            comment="Calendar date of the exchange rate (Bundesbank EZB reference rate).",
        ),
        sa.Column(
            "base",
            sa.String(3),
            nullable=False,
            comment="Base currency ISO-4217 code (e.g. USD).",
        ),
        sa.Column(
            "quote",
            sa.String(3),
            nullable=False,
            comment="Quote currency ISO-4217 code (e.g. EUR).",
        ),
        sa.Column(
            "rate",
            sa.Numeric(18, 8),
            nullable=False,
            comment="Exchange rate: 1 base = rate quote.",
        ),
        sa.Column(
            "source",
            sa.String(50),
            nullable=False,
            server_default="bundesbank",
            comment="Source identifier for the rate (e.g. 'bundesbank').",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "date", "base", "quote", name="uq_fx_rates_date_base_quote"
        ),
    )

    op.create_index(
        "ix_fx_rates_date_base_quote", "fx_rates", ["date", "base", "quote"]
    )


def downgrade() -> None:
    """Remove currency/pnl_eur from trades and drop fx_rates table."""
    op.drop_index("ix_fx_rates_date_base_quote", table_name="fx_rates")
    op.drop_table("fx_rates")
    op.drop_column("trades", "pnl_eur")
    op.drop_column("trades", "currency")
