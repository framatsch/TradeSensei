"""add image_urls to trades

Revision ID: c5d8e9f2a312
Revises: c5d8e9f2a311
Create Date: 2024-05-01 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c5d8e9f2a312'
down_revision: str | None = 'c5d8e9f2a311'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('trades', sa.Column('image_urls', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False))
    op.drop_column('trades', 'screenshots')


def downgrade() -> None:
    op.add_column('trades', sa.Column('screenshots', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=True))
    op.drop_column('trades', 'image_urls')
