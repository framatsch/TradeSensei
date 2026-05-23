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

"""drop cash_transactions table

Revision ID: b3c4d5e6f7a8
Revises: 2cc64ca84bae
Create Date: 2026-05-17 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "b3c4d5e6f7a8"
down_revision = "2cc64ca84bae"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Drop the cash_transactions table if it exists.

    The table may already be absent on environments that ran the removal
    before this migration was introduced (e.g. the test DB).
    """
    op.execute(sa.text("DROP TABLE IF EXISTS cash_transactions"))


def downgrade() -> None:
    """Irreversible — table is not recreated on downgrade."""
    pass
