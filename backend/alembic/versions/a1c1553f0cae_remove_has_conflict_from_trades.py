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

"""remove_has_conflict_from_trades

Drop the ``has_conflict`` column from the ``trades`` table.
The conflict-detection feature is superseded by the simplified execution model
(Decision 5 / task 5.5): trades with all executions ``deleted=true`` simply
have a zero-quantity aggregation — no separate conflict flag is needed.

Revision ID: a1c1553f0cae
Revises: b8d1e4f2a9c3
Create Date: 2026-04-18 00:03:17.965592

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1c1553f0cae"
down_revision: str | None = "b8d1e4f2a9c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop has_conflict column from the trades table."""
    op.drop_column("trades", "has_conflict")


def downgrade() -> None:
    """Restore has_conflict column (defaults to false for existing rows)."""
    op.add_column(
        "trades",
        sa.Column(
            "has_conflict",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment=(
                "When True, the aggregated position does not reconcile with the "
                "broker's <OpenPosition> block.  Deprecated — retained for rollback only."
            ),
        ),
    )
