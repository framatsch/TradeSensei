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

"""rename_trades_notes_to_journal

Revision ID: 9d38d119a8cf
Revises: 3c8f4a1e2b7d
Create Date: 2026-07-24 00:00:00.000000

Renames the ``trades.notes`` column to ``trades.journal`` to align the data
model with the "Journal" UI label and remove the naming collision with the
Quick Notes relationship ``trade.trade_notes``.

Scoped strictly to the Trade entity — ``daily_checkins.notes`` is untouched.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9d38d119a8cf"
down_revision: str | None = "3c8f4a1e2b7d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("trades", "notes", new_column_name="journal")


def downgrade() -> None:
    op.alter_column("trades", "journal", new_column_name="notes")
