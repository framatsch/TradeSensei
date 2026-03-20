"""Add user_settings table and make broker_connections.token_expires_at nullable.

Changes:
- ``broker_connections.token_expires_at``: Make nullable to support non-OAuth
  broker integrations (e.g. IBKR Flex Queries) that do not have short-lived
  expiry timestamps managed by the application.
- ``user_settings`` table: Key-value store for per-user UI preferences
  (theme, default_date_range). Unique constraint on ``(user_id, key)``.

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-20 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Make token_expires_at nullable and create user_settings table."""

    # ── broker_connections: make token_expires_at nullable ────────────────────
    op.alter_column(
        "broker_connections",
        "token_expires_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
        comment="UTC expiry timestamp of the access token. NULL for non-OAuth brokers (e.g. IBKR).",
    )

    # ── user_settings table ───────────────────────────────────────────────────
    op.create_table(
        "user_settings",
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
            "key",
            sa.String(100),
            nullable=False,
            comment="Setting key identifier (e.g. 'theme', 'default_date_range').",
        ),
        sa.Column(
            "value",
            sa.Text(),
            nullable=False,
            comment="Setting value stored as text.",
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
            "key",
            name="uq_user_settings_user_key",
        ),
    )

    op.create_index(
        "ix_user_settings_user_id",
        "user_settings",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop user_settings table and restore token_expires_at NOT NULL."""
    op.drop_index("ix_user_settings_user_id", table_name="user_settings")
    op.drop_table("user_settings")

    op.alter_column(
        "broker_connections",
        "token_expires_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        comment="UTC expiry timestamp of the access token.",
    )
