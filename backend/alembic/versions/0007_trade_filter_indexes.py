"""Add composite indexes for trade filter/sort performance.

Creates indexes on the ``trades`` table columns used by the
``TradeFilterParams`` and ``TradeSortParams`` query parameters in
``GET /api/v1/trades``:

- ``ix_trades_user_symbol``: (user_id, symbol) for symbol ILIKE filter
- ``ix_trades_user_direction``: (user_id, direction) for direction filter
- ``ix_trades_user_asset_class``: (user_id, asset_class) for asset_class filter
- ``ix_trades_user_opened_at``: (user_id, opened_at) for date range filter + sort
- ``ix_trades_user_closed_at``: (user_id, closed_at) for date range filter + sort
- ``ix_trades_user_pnl``: (user_id, pnl) for pnl_positive filter + sort
- ``ix_trades_user_playbook_id``: (user_id, playbook_id) for playbook filter

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-16 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create composite indexes for trade filter/sort performance."""
    op.create_index(
        "ix_trades_user_symbol",
        "trades",
        ["user_id", "symbol"],
        unique=False,
    )
    op.create_index(
        "ix_trades_user_direction",
        "trades",
        ["user_id", "direction"],
        unique=False,
    )
    op.create_index(
        "ix_trades_user_asset_class",
        "trades",
        ["user_id", "asset_class"],
        unique=False,
    )
    op.create_index(
        "ix_trades_user_opened_at",
        "trades",
        ["user_id", "opened_at"],
        unique=False,
    )
    op.create_index(
        "ix_trades_user_closed_at",
        "trades",
        ["user_id", "closed_at"],
        unique=False,
    )
    op.create_index(
        "ix_trades_user_pnl",
        "trades",
        ["user_id", "pnl"],
        unique=False,
    )
    op.create_index(
        "ix_trades_user_playbook_id",
        "trades",
        ["user_id", "playbook_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop composite indexes added in upgrade()."""
    op.drop_index("ix_trades_user_playbook_id", table_name="trades")
    op.drop_index("ix_trades_user_pnl", table_name="trades")
    op.drop_index("ix_trades_user_closed_at", table_name="trades")
    op.drop_index("ix_trades_user_opened_at", table_name="trades")
    op.drop_index("ix_trades_user_asset_class", table_name="trades")
    op.drop_index("ix_trades_user_direction", table_name="trades")
    op.drop_index("ix_trades_user_symbol", table_name="trades")
