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

"""add has_unlinked_executions to trades

Revision ID: 5f3d8c2a1b77
Revises: 90b1a6f4c2de
Create Date: 2026-08-15 22:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "5f3d8c2a1b77"
down_revision: str | Sequence[str] | None = "90b1a6f4c2de"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "trades",
        sa.Column(
            "has_unlinked_executions",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment=(
                "True when at least one broker execution was left unlinked because "
                "the protected trade could not absorb it during import."
            ),
        ),
    )


def downgrade() -> None:
    op.drop_column("trades", "has_unlinked_executions")
