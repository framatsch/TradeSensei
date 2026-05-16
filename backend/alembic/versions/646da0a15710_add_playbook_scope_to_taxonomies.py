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

"""add playbook scope to taxonomies

Revision ID: 646da0a15710
Revises: a1b2c3d4e5f6
Create Date: 2026-05-13 23:44:15.863558

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '646da0a15710'
down_revision: str | None = 'a1b2c3d4e5f6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Update taxonomy scope check constraint to include 'playbook'
    op.drop_constraint("ck_taxonomies_scope", "taxonomies", type_="check")
    op.create_check_constraint(
        "ck_taxonomies_scope",
        "taxonomies",
        sa.column("scope").in_(["trades", "checkins", "playbook", "both"])
    )


def downgrade() -> None:
    # Revert taxonomy scope check constraint
    op.drop_constraint("ck_taxonomies_scope", "taxonomies", type_="check")
    op.create_check_constraint(
        "ck_taxonomies_scope",
        "taxonomies",
        sa.column("scope").in_(["trades", "checkins", "both"])
    )
