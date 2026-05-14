"""add playbook scope to taxonomies

Revision ID: 646da0a15710
Revises: a1b2c3d4e5f6
Create Date: 2026-05-13 23:44:15.863558

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '646da0a15710'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update taxonomy scope check constraint to include 'playbook'
    op.drop_constraint("ck_taxonomies_scope", "taxonomies", type_="check")
    op.create_check_constraint(
        "ck_taxonomies_scope",
        "taxonomies",
        sa.column("scope").in_(["trades", "checkins", "playbook", "both"])
    )


def downgrade() -> None:
    # Revert taxonomy scope check constraint
    op.drop_constraint("ck_taxonomies_scope", "taxonomies", type_="check")
    op.create_check_constraint(
        "ck_taxonomies_scope",
        "taxonomies",
        sa.column("scope").in_(["trades", "checkins", "both"])
    )
