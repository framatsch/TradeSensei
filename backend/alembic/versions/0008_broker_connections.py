"""Add broker_connections table and broker_order_id column on trades.

Adds infrastructure for Iteration 7 live broker API connections (Schwab OAuth):

- ``broker_order_id VARCHAR(100) NULL`` on ``trades``: external broker order
  identifier used for deduplication when syncing trades from a live broker API.
  Indexed for fast lookup.
- ``broker_connections`` table: stores per-user Fernet-encrypted OAuth 2.0
  tokens for each broker integration.  Unique constraint on ``(user_id, broker)``
  ensures at most one active connection per broker per user.

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-16 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID  # noqa: F401

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add broker_order_id to trades and create broker_connections table."""

    # ── trades: broker_order_id column ────────────────────────────────────────
    op.add_column(
        "trades",
        sa.Column(
            "broker_order_id",
            sa.String(100),
            nullable=True,
            comment="External broker order identifier for deduplication.",
        ),
    )
    op.create_index(
        "ix_trades_broker_order_id",
        "trades",
        ["broker_order_id"],
        unique=False,
    )

    # ── broker_connections table ───────────────────────────────────────────────
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
            nullable=False,
            comment="UTC expiry timestamp of the access token.",
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


def downgrade() -> None:
    """Drop broker_connections table and broker_order_id from trades."""
    op.drop_index("ix_broker_connections_user_id", table_name="broker_connections")
    op.drop_table("broker_connections")
    op.drop_index("ix_trades_broker_order_id", table_name="trades")
    op.drop_column("trades", "broker_order_id")
