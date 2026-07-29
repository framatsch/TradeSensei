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

"""merge_multiple_heads

Revision ID: 828898f603ed
Revises: 32112bfd9edf, acd888d66d9c
Create Date: 2026-06-06 10:48:13.998205

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = '828898f603ed'
down_revision: str | None = ('32112bfd9edf', 'acd888d66d9c')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
