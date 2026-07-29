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

"""drop is_modelbook from trades and daily_checkins

Revision ID: 1f1fe4f274ae
Revises: b3c4d5e6f7a8
Create Date: 2026-05-30 12:57:25.228056

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1f1fe4f274ae'
down_revision: str | None = 'b3c4d5e6f7a8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE trades DROP COLUMN IF EXISTS is_modelbook"))
    op.execute(sa.text("ALTER TABLE daily_checkins DROP COLUMN IF EXISTS is_modelbook"))


def downgrade() -> None:
    op.add_column(
        "daily_checkins",
        sa.Column(
            "is_modelbook",
            sa.Boolean(),
            server_default="false",
            nullable=False,
            comment="True if this check-in is starred in the Model Book.",
        ),
    )
    op.add_column(
        "trades",
        sa.Column(
            "is_modelbook",
            sa.Boolean(),
            server_default="false",
            nullable=False,
            comment="True if this trade is starred in the Model Book.",
        ),
    )
