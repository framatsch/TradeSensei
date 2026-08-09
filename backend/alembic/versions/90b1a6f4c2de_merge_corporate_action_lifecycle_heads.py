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

"""merge corporate action lifecycle heads

Revision ID: 90b1a6f4c2de
Revises: 68fc73e060bd, 8d2f4a1c9b71
Create Date: 2026-08-09 22:30:00.000000

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "90b1a6f4c2de"
down_revision: str | Sequence[str] | None = ("68fc73e060bd", "8d2f4a1c9b71")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
