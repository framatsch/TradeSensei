# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""backfill execution legs for existing trades

Revision ID: 4e095dd6e4c5
Revises: f97ff74cda3d
Create Date: 2026-04-14 21:08:49.456789

This migration creates logical_executions (legs) for all existing trades that
don't have any. For each trade, we create:
- Entry leg: direction=trade.direction, price=entry_price, executed_at=opened_at
- Exit leg (if closed): opposite direction, price=exit_price, executed_at=closed_at
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4e095dd6e4c5"
down_revision: str | None = "f97ff74cda3d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create execution legs for all trades that don't have any."""
    # Create entry legs for all trades (even open ones)
    op.execute("""
        INSERT INTO logical_executions (
            user_id,
            account_id,
            symbol,
            conid,
            asset_class,
            direction,
            quantity,
            price,
            commission,
            executed_at,
            currency,
            status,
            trade_id,
            multiplier
        )
        SELECT
            t.user_id,
            t.account_id,
            t.symbol,
            t.broker_conid,
            t.asset_class,
            t.direction,  -- Entry leg has same direction as trade
            t.quantity,
            t.entry_price,
            t.commission,  -- Full commission on entry leg
            t.opened_at,
            COALESCE(t.currency, 'USD'),
            'imported'::execution_status_enum,
            t.id,
            COALESCE(t.multiplier, 1)
        FROM trades t
        WHERE NOT EXISTS (
            SELECT 1 FROM logical_executions le
            WHERE le.trade_id = t.id
        )
        AND t.entry_price != 0.001  -- Skip orphaned lots (they only have exit leg)
        AND t.user_id IS NOT NULL  -- Skip trades without user_id
    """)

    # Create exit legs for all closed trades
    op.execute("""
        INSERT INTO logical_executions (
            user_id,
            account_id,
            symbol,
            conid,
            asset_class,
            direction,
            quantity,
            price,
            commission,
            executed_at,
            pnl,
            pnl_eur,
            currency,
            status,
            trade_id,
            multiplier
        )
        SELECT
            t.user_id,
            t.account_id,
            t.symbol,
            t.broker_conid,
            t.asset_class,
            -- Exit leg has opposite direction
            CASE
                WHEN t.direction = 'LONG' THEN 'SHORT'::direction_enum
                ELSE 'LONG'::direction_enum
            END,
            t.quantity,
            t.exit_price,
            0,  -- Commission already on entry leg
            t.closed_at,
            t.pnl,
            t.pnl_eur,
            COALESCE(t.currency, 'USD'),
            'imported'::execution_status_enum,
            t.id,
            COALESCE(t.multiplier, 1)
        FROM trades t
        WHERE t.closed_at IS NOT NULL
        AND t.exit_price IS NOT NULL
        AND t.user_id IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM logical_executions le
            WHERE le.trade_id = t.id
            AND le.executed_at = t.closed_at
        )
    """)

    # Create entry legs for orphaned lots (entry_price = 0.001)
    op.execute("""
        INSERT INTO logical_executions (
            user_id,
            account_id,
            symbol,
            conid,
            asset_class,
            direction,
            quantity,
            price,
            commission,
            executed_at,
            currency,
            status,
            trade_id,
            multiplier
        )
        SELECT
            t.user_id,
            t.account_id,
            t.symbol,
            t.broker_conid,
            t.asset_class,
            t.direction,
            t.quantity,
            t.entry_price,
            0,
            t.opened_at,
            COALESCE(t.currency, 'USD'),
            'imported'::execution_status_enum,
            t.id,
            COALESCE(t.multiplier, 1)
        FROM trades t
        WHERE t.entry_price = 0.001
        AND t.user_id IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM logical_executions le
            WHERE le.trade_id = t.id
        )
    """)


def downgrade() -> None:
    """Remove all backfilled execution legs."""
    op.execute("""
        DELETE FROM logical_executions
        WHERE status = 'imported'::execution_status_enum
    """)
