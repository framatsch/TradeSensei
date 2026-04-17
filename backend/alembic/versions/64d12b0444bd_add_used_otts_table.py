"""add-used-otts-table

Revision ID: 64d12b0444bd
Revises: a1c1553f0cae
Create Date: 2026-04-18 00:50:39.302429

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "64d12b0444bd"
down_revision: Union[str, None] = "a1c1553f0cae"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
