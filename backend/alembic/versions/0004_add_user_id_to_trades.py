"""Add user_id FK to trades table for direct user-scoped queries.

Adds a ``user_id`` column (FK → ``users.id``, CASCADE on delete) to the
``trades`` table.  This allows all metrics and time-series queries to filter
by user without requiring an INNER JOIN on ``accounts``, which previously
excluded all trades that had no ``account_id`` set.

Backfill strategy:
- Trades that already have an ``account_id``: derive ``user_id`` from the
  parent account via a single UPDATE … FROM accounts.
- Trades without an ``account_id`` (e.g. trades seeded directly via the REST
  API without an account): cannot be backfilled automatically.  For a fresh
  database (development/test) this situation does not arise because the column
  is set at insert time going forward.  For any existing rows that remain NULL
  after the backfill the column is left nullable; the application layer must
  always supply ``user_id`` on new inserts.

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-15 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add user_id column to trades and backfill from accounts."""

    # 1. Add the column as nullable first so existing rows are not rejected.
    op.add_column(
        "trades",
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # 2. Backfill trades that have an account_id by joining to accounts.
    op.execute(
        """
        UPDATE trades
        SET    user_id = accounts.user_id
        FROM   accounts
        WHERE  trades.account_id = accounts.id
          AND  trades.user_id IS NULL
        """
    )

    # 3. Add the FK constraint (deferred so existing NULL rows are allowed).
    op.create_foreign_key(
        "fk_trades_user_id_users",
        "trades",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 4. Create an index for fast user-scoped lookups.
    op.create_index("ix_trades_user_id", "trades", ["user_id"])


def downgrade() -> None:
    """Remove user_id column and related index/FK from trades."""
    op.drop_index("ix_trades_user_id", table_name="trades")
    op.drop_constraint("fk_trades_user_id_users", "trades", type_="foreignkey")
    op.drop_column("trades", "user_id")
