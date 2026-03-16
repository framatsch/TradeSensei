"""Add provider/provider_id to users; make hashed_password nullable.

Extends the ``users`` table to support OAuth authentication alongside the
existing local (password-based) login:

- ``provider VARCHAR(20) NOT NULL DEFAULT 'local'``: authentication
  provider; ``'local'`` for password users, ``'google'`` for Google OAuth.
- ``provider_id VARCHAR(255) NULL``: provider-specific user identifier
  (e.g. the Google ``sub`` claim). ``NULL`` for local accounts.
- ``hashed_password`` becomes nullable to accommodate OAuth-only users
  who have no local password.
- Adds a partial unique index on ``(provider, provider_id)`` where
  ``provider_id IS NOT NULL`` to prevent duplicate OAuth accounts.
- Backfills all existing rows with ``provider = 'local'``.

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-15 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply the migration: add provider columns, make password nullable."""
    # 1. Add provider column with default 'local' — NOT NULL from the start
    op.add_column(
        "users",
        sa.Column(
            "provider",
            sa.String(20),
            nullable=False,
            server_default="local",
        ),
    )

    # 2. Add provider_id column — nullable
    op.add_column(
        "users",
        sa.Column("provider_id", sa.String(255), nullable=True),
    )

    # 3. Make hashed_password nullable (OAuth users have no local password)
    op.alter_column("users", "hashed_password", nullable=True)

    # 4. Partial unique index on (provider, provider_id) where provider_id IS NOT NULL
    op.create_index(
        "ix_users_provider_provider_id",
        "users",
        ["provider", "provider_id"],
        unique=True,
        postgresql_where=sa.text("provider_id IS NOT NULL"),
    )


def downgrade() -> None:
    """Reverse the migration: remove provider columns, restore NOT NULL."""
    # Drop the partial index first
    op.drop_index(
        "ix_users_provider_provider_id",
        table_name="users",
        postgresql_where=sa.text("provider_id IS NOT NULL"),
    )

    # Restore hashed_password to NOT NULL
    # (assumes no OAuth-only rows remain — downgrade would fail otherwise)
    op.alter_column("users", "hashed_password", nullable=False)

    op.drop_column("users", "provider_id")
    op.drop_column("users", "provider")
