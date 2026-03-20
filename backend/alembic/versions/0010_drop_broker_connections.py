"""Drop broker_connections table.

The broker credentials model has been refactored from a per-user global
``broker_connections`` table to per-account ``account_properties`` rows.
This migration removes the now-obsolete ``broker_connections`` table.

Changes:
- Drop ``broker_connections`` table (including its index and unique constraint).

Revision ID: 0010
Revises: 0009
Create Date: 2026-03-21 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop the broker_connections table."""
    op.drop_index("ix_broker_connections_user_id", table_name="broker_connections")
    op.drop_table("broker_connections")


def downgrade() -> None:
    """Recreate the broker_connections table."""
    op.create_table(
        "broker_connections",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "broker",
            sa.String(50),
            nullable=False,
        ),
        sa.Column(
            "access_token",
            sa.Text(),
            nullable=False,
            comment="Fernet-encrypted OAuth access token.",
        ),
        sa.Column(
            "refresh_token",
            sa.Text(),
            nullable=False,
            comment="Fernet-encrypted OAuth refresh token.",
        ),
        sa.Column(
            "token_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="UTC expiry timestamp of the access token. NULL for non-OAuth brokers (e.g. IBKR).",
        ),
        sa.Column(
            "last_sync_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="UTC timestamp of the last successful trade sync.",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "user_id",
            "broker",
            name="uq_broker_connections_user_broker",
        ),
    )
    op.create_index(
        "ix_broker_connections_user_id",
        "broker_connections",
        ["user_id"],
        unique=False,
    )
