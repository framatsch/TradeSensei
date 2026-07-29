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

"""remove_ck_taxonomies_scope

Revision ID: 32112bfd9edf
Revises: b7e2c1d4f9a8
Create Date: 2026-06-06 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '32112bfd9edf'
down_revision: str | None = 'b7e2c1d4f9a8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    # Drop the strict scope check constraint to allow comma-separated combinations
    op.drop_constraint("ck_taxonomies_scope", "taxonomies", type_="check")

def downgrade() -> None:
    op.create_check_constraint(
        "ck_taxonomies_scope",
        "taxonomies",
        sa.column("scope").in_(["trades", "checkins", "playbook", "both"])
    )
