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

"""add_open_close_to_logical_executions_and_raw_transactions

Revision ID: d7e2f1a9c4b8
Revises: c1f0baf3b07d
Create Date: 2026-07-16 23:10:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd7e2f1a9c4b8'
down_revision: str | None = 'c1f0baf3b07d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_OPEN_CLOSE_COMMENT = (
    "Opening/closing indicator derived by the broker parser: 'O' (opening),"
    " 'C' (closing), or NULL (mixed/unknown/manual). Populated from IBKR"
    " openCloseIndicator or Schwab positionEffect."
)


def upgrade() -> None:
    op.add_column(
        'logical_executions',
        sa.Column(
            'open_close',
            sa.String(length=1),
            nullable=True,
            comment=_OPEN_CLOSE_COMMENT,
        ),
    )
    op.add_column(
        'broker_raw_transactions',
        sa.Column(
            'open_close',
            sa.String(length=1),
            nullable=True,
            comment=_OPEN_CLOSE_COMMENT,
        ),
    )


def downgrade() -> None:
    op.drop_column('broker_raw_transactions', 'open_close')
    op.drop_column('logical_executions', 'open_close')
