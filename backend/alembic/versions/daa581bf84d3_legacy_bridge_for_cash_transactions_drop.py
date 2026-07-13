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

"""Legacy bridge revision for cash_transactions drop.

Revision ID: daa581bf84d3
Revises: 2cc64ca84bae
Create Date: 2026-07-13 00:00:00.000000

This no-op migration keeps compatibility with databases that were already
stamped with the historical revision id ``daa581bf84d3``.
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "daa581bf84d3"
down_revision: str | None = "2cc64ca84bae"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
