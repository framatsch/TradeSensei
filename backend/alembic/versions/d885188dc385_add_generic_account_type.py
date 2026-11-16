"""add_generic_account_type

Revision ID: d885188dc385
Revises: d7e1a4b9c2f0
Create Date: 2026-11-10 20:53:39.764323

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d885188dc385"
down_revision: str | None = "d7e1a4b9c2f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the lowercase enum value used by AccountType.values_callable.

    Alembic autogenerate does not detect PostgreSQL enum value additions.
    Autocommit supports PostgreSQL versions requiring enum DDL outside a transaction.
    """
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'generic'")


def downgrade() -> None:
    """Keep the unused enum value; PostgreSQL cannot safely drop enum members."""
    pass
