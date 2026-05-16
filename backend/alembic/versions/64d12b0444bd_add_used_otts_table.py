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

"""add-used-otts-table

Revision ID: 64d12b0444bd
Revises: a1c1553f0cae
Create Date: 2026-04-18 00:50:39.302429

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "64d12b0444bd"
down_revision: str | None = "a1c1553f0cae"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the used_otts table and index for OTT blocklist storage."""
    op.create_table(
        "used_otts",
        sa.Column("jti", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("jti"),
    )
    op.create_index("ix_used_otts_expires", "used_otts", ["expires_at"], unique=False)


def downgrade() -> None:
    """Drop the used_otts table and its index."""
    op.drop_index("ix_used_otts_expires", table_name="used_otts")
    op.drop_table("used_otts")
