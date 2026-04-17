"""add-is-combo-to-trades

Revision ID: 51f7adace3d1
Revises: 3bbca280b48e
Create Date: 2026-04-19 10:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "51f7adace3d1"
down_revision: Union[str, None] = "3bbca280b48e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
