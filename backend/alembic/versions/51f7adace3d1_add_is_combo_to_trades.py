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

"""add-is-combo-to-trades

Revision ID: 51f7adace3d1
Revises: 3bbca280b48e
Create Date: 2026-04-19 10:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "51f7adace3d1"
down_revision: str | None = "3bbca280b48e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add COMBO flag and allow null top-level fields for COMBO trades."""
    op.add_column(
        "trades",
        sa.Column(
            "is_combo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.alter_column(
        "trades",
        "asset_class",
        existing_type=sa.Enum(name="asset_class_enum", create_type=False),
        nullable=True,
    )
    op.alter_column(
        "trades",
        "quantity",
        existing_type=sa.Numeric(18, 8),
        nullable=True,
    )
    op.alter_column(
        "trades",
        "entry_price",
        existing_type=sa.Numeric(18, 8),
        nullable=True,
    )


def downgrade() -> None:
    """Drop COMBO flag and restore previous non-null constraints."""
    op.alter_column(
        "trades",
        "entry_price",
        existing_type=sa.Numeric(18, 8),
        nullable=False,
    )
    op.alter_column(
        "trades",
        "quantity",
        existing_type=sa.Numeric(18, 8),
        nullable=False,
    )
    op.alter_column(
        "trades",
        "asset_class",
        existing_type=sa.Enum(name="asset_class_enum", create_type=False),
        nullable=False,
    )
    op.drop_column("trades", "is_combo")
