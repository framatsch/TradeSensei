"""add-rls-user-isolation

Enables PostgreSQL Row-Level Security (RLS) on all user-scoped tables.
Each table gets a ``user_isolation`` policy that filters rows by
``current_setting('app.current_user_id', true)::uuid``, which is SET per
request by the ``get_session_with_rls`` FastAPI dependency.

The Alembic role (``tradesensei``) already has BYPASSRLS so migrations
run without restriction.  If running as a different role without BYPASSRLS,
execute ``ALTER ROLE <role> BYPASSRLS;`` as superuser first.

Revision ID: 3bbca280b48e
Revises: 64d12b0444bd
Create Date: 2026-04-18 01:11:54.499073

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3bbca280b48e"
down_revision: str | None = "64d12b0444bd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tables that have a UUID ``user_id`` column and require RLS isolation.
# Tables without user_id (fx_rates, ohlc_prices, trade_tags, used_otts, etc.)
# are shared reference / junction data and do not get RLS policies.
_USER_SCOPED_TABLES = [
    "trades",
    "logical_executions",
    "broker_raw_transactions",
    "accounts",
    "playbooks",
    "tags",
    "trade_notes",
    "user_settings",
    "corporate_actions",
]


def upgrade() -> None:
    """Enable RLS and create user_isolation policies on all user-scoped tables."""
    for table in _USER_SCOPED_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        # FORCE RLS enforces policies even for the table owner.
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY user_isolation ON {table}
            USING (user_id = current_setting('app.current_user_id', true)::uuid)
            """
        )


def downgrade() -> None:
    """Drop user_isolation policies and disable RLS on all user-scoped tables."""
    for table in _USER_SCOPED_TABLES:
        op.execute(f"DROP POLICY IF EXISTS user_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
