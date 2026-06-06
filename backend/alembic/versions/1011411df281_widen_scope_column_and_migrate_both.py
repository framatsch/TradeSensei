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

"""widen_scope_column_and_migrate_both

Revision ID: 1011411df281
Revises: 828898f603ed
Create Date: 2026-06-06 12:00:00.000000

Widens the ``taxonomies.scope`` column from VARCHAR(20) to VARCHAR(50) to
accommodate comma-separated multi-scope strings (e.g. ``"trades,checkins"``).

Also migrates legacy ``"both"`` rows:
  - ``scope = "both"``  →  ``scope = "trades,checkins,playbook"``

The ``"both"`` value was the old way of expressing "all applicable scopes".
Going forward, explicit comma-separated tokens replace it.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1011411df281"
down_revision: str | None = "828898f603ed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Widen the column so comma-separated tokens fit.
    op.alter_column(
        "taxonomies",
        "scope",
        existing_type=sa.String(20),
        type_=sa.String(50),
        existing_nullable=False,
    )

    # 2. Migrate legacy "both" rows to explicit multi-scope string.
    op.execute(
        sa.text("UPDATE taxonomies SET scope = 'trades,checkins,playbook' WHERE scope = 'both'")
    )


def downgrade() -> None:
    # Reverse the data migration: collapse multi-scope back to "both".
    # Only rows that were originally "both" (i.e. all three tokens) are
    # reverted; rows with partial multi-scope stay as-is (they were created
    # after the upgrade and have no clean downgrade path).
    op.execute(
        sa.text(
            "UPDATE taxonomies SET scope = 'both' WHERE scope = 'trades,checkins,playbook'"
        )
    )

    # Narrow the column back — this will fail if any remaining rows exceed
    # 20 characters. That's intentional: partial multi-scope values need
    # manual cleanup before downgrading.
    op.alter_column(
        "taxonomies",
        "scope",
        existing_type=sa.String(50),
        type_=sa.String(20),
        existing_nullable=False,
    )
