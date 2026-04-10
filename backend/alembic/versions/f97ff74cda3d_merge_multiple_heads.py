"""merge multiple heads

Revision ID: f97ff74cda3d
Revises: 28989209dc98, 627ae0cc1cff
Create Date: 2026-04-11 11:49:40.300711

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f97ff74cda3d'
down_revision: Union[str, None] = ('28989209dc98', '627ae0cc1cff')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
