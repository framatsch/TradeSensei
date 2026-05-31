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

"""seed_market_index_definitions

Revision ID: 314159265358
Revises: 1f1fe4f274ae
Create Date: 2026-05-30 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "314159265358"
down_revision: str | None = "1f1fe4f274ae"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    # Create default indexes for all users who don't have them yet or just ON CONFLICT DO NOTHING
    bind.execute(
        sa.text(
            """
            INSERT INTO market_index_definitions (user_id, symbol, name, tradingview_url, is_active)
            SELECT u.id, defaults.symbol, defaults.name, defaults.tradingview_url, true
            FROM users AS u
            CROSS JOIN (
                VALUES
                    ('SPX', 'S&P 500', 'https://www.tradingview.com/symbols/SPX/'),
                    ('NDX', 'NASDAQ 100', 'https://www.tradingview.com/symbols/NDX/'),
                    ('DAX', 'DAX', 'https://www.tradingview.com/symbols/XETR-DAX/')
            ) AS defaults(symbol, name, tradingview_url)
            ON CONFLICT ON CONSTRAINT uq_market_index_user_symbol DO NOTHING
            """
        )
    )

def downgrade() -> None:
    # Intentional no-op: seeded defaults cannot be safely removed
    pass
