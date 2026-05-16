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

"""add net_pnl

Revision ID: 6ef8896e1bde
Revises: 28989209dc97
Create Date: 2026-04-03 21:38:10.739877

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6ef8896e1bde"
down_revision: str | None = "28989209dc97"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "trades",
        sa.Column("net_pnl", sa.Numeric(precision=18, scale=4), nullable=True),
    )
    op.add_column(
        "trades",
        sa.Column(
            "net_pnl_eur",
            sa.Numeric(precision=18, scale=4),
            nullable=True,
            comment="Realised net P&L converted to EUR at the Bundesbank daily rate on the trade date.",
        ),
    )
    op.execute("UPDATE trades SET net_pnl = pnl - commission WHERE pnl IS NOT NULL")


def downgrade() -> None:
    op.drop_column("trades", "net_pnl_eur")
    op.drop_column("trades", "net_pnl")
