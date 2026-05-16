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

"""merge multiple heads

Revision ID: f97ff74cda3d
Revises: 28989209dc98, 627ae0cc1cff
Create Date: 2026-04-11 11:49:40.300711

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = 'f97ff74cda3d'
down_revision: str | None = ('28989209dc98', '627ae0cc1cff')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
