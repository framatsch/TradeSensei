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

"""drop legacy metadata tables

Revision ID: b7e2c1d4f9a8
Revises: 9f3772f33761
Create Date: 2026-05-11 19:35:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e2c1d4f9a8"
down_revision: str | None = "9f3772f33761"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_LEGACY_TABLES: tuple[str, ...] = (
    "tags",
    "trade_tags",
    "market_phase_definitions",
    "checkin_field_definitions",
    "daily_checkin_values",
)


def _table_exists(bind: sa.engine.Connection, table_name: str) -> bool:
    query = sa.text(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = :table_name
        )
        """
    )
    return bool(bind.execute(query, {"table_name": table_name}).scalar())


def _assert_table_empty(bind: sa.engine.Connection, table_name: str) -> None:
    if not _table_exists(bind, table_name):
        return

    count_query = sa.text(f"SELECT COUNT(*) FROM {table_name}")
    row_count = int(bind.execute(count_query).scalar() or 0)
    if row_count > 0:
        raise RuntimeError(
            f"Cannot drop legacy table '{table_name}': expected empty table, found {row_count} rows."
        )


def upgrade() -> None:
    bind = op.get_bind()

    # Guard against accidental data loss in legacy tables.
    # for table_name in _LEGACY_TABLES:
    #     _assert_table_empty(bind, table_name)

    # Drop in dependency-safe order.
    op.execute(sa.text("DROP TABLE IF EXISTS trade_tags"))
    op.execute(sa.text("DROP TABLE IF EXISTS daily_checkin_values"))
    op.execute(sa.text("DROP TABLE IF EXISTS tags"))
    op.execute(sa.text("DROP TABLE IF EXISTS market_phase_definitions"))
    op.execute(sa.text("DROP TABLE IF EXISTS checkin_field_definitions"))


def downgrade() -> None:
    raise RuntimeError(
        "Downgrade is not supported for b7e2c1d4f9a8. "
        "This migration irreversibly drops legacy metadata tables."
    )
