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

"""widen_annotation_definitions_scope_and_migrate_both

Revision ID: c1f0baf3b07d
Revises: 1011411df281
Create Date: 2026-06-06 13:00:00.000000

Mirrors the taxonomy scope migration (1011411df281) for annotation_definitions:

1. Widens ``annotation_definitions.scope`` from VARCHAR(20) to VARCHAR(50).
2. Drops the ``ck_annotation_definitions_scope`` CHECK constraint that
   restricted scope to ``('trades', 'checkins', 'both')``.
3. Migrates legacy ``scope = 'both'`` rows to ``'checkins,trades'``
   (comma-separated, alphabetically sorted to match normalize_scope output).

After this migration both the ``taxonomies`` and ``annotation_definitions``
tables use the same comma-separated multi-token scope format.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c1f0baf3b07d"
down_revision: str | None = "1011411df281"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Drop the enum CHECK constraint so multi-token values are accepted.
    op.drop_constraint("ck_annotation_definitions_scope", "annotation_definitions", type_="check")

    # 2. Widen the column to accommodate comma-separated token strings.
    op.alter_column(
        "annotation_definitions",
        "scope",
        existing_type=sa.String(20),
        type_=sa.String(50),
        existing_nullable=False,
    )

    # 3. Migrate legacy "both" → "checkins,trades" (alphabetical sort matches
    #    normalize_scope canonical form).
    op.execute(
        sa.text("UPDATE annotation_definitions SET scope = 'checkins,trades' WHERE scope = 'both'")
    )


def downgrade() -> None:
    # Reverse the data migration: only 'checkins,trades' rows that were
    # originally 'both' are reverted.  Partial multi-scope rows created after
    # the upgrade have no clean downgrade path and will cause the
    # ALTER COLUMN below to fail if they exceed 20 characters — intentional.
    op.execute(
        sa.text(
            "UPDATE annotation_definitions SET scope = 'both' WHERE scope = 'checkins,trades'"
        )
    )

    op.alter_column(
        "annotation_definitions",
        "scope",
        existing_type=sa.String(50),
        type_=sa.String(20),
        existing_nullable=False,
    )

    op.create_check_constraint(
        "ck_annotation_definitions_scope",
        "annotation_definitions",
        sa.column("scope").in_(["trades", "checkins", "both"]),
    )
