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

"""increase_net_pnl_scale_to_8

Revision ID: f2f9e5f1b0c4
Revises: 88deb49a9f12
Create Date: 2026-04-04 23:35:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2f9e5f1b0c4"
down_revision: str | None = "88deb49a9f12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Increase net PnL precision scale to 8 decimals."""
    op.alter_column(
        "trades",
        "net_pnl",
        existing_type=sa.Numeric(precision=18, scale=4),
        type_=sa.Numeric(precision=18, scale=8),
        existing_nullable=True,
    )
    op.alter_column(
        "trades",
        "net_pnl_eur",
        existing_type=sa.Numeric(precision=18, scale=4),
        type_=sa.Numeric(precision=18, scale=8),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Restore net PnL precision scale back to 4 decimals."""
    op.alter_column(
        "trades",
        "net_pnl_eur",
        existing_type=sa.Numeric(precision=18, scale=8),
        type_=sa.Numeric(precision=18, scale=4),
        existing_nullable=True,
    )
    op.alter_column(
        "trades",
        "net_pnl",
        existing_type=sa.Numeric(precision=18, scale=8),
        type_=sa.Numeric(precision=18, scale=4),
        existing_nullable=True,
    )
