"""Update accounts table and create account_properties table.

Refactors broker credentials from the global ``broker_connections`` table
to per-account ``account_properties`` key-value rows:

Changes:
- ``accounts.broker``: Drop the string column (replaced by ``type``).
- ``accounts.type``: Add non-nullable ``accounttype`` enum column
  (values: ``manual``, ``schwab``, ``ibkr``), default ``manual``.
- ``account_properties`` table: New table for encrypted per-account
  broker credential key-value pairs.

Revision ID: 0011
Revises: 0010
Create Date: 2026-03-21 00:00:01.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop accounts.broker, add accounts.type, create account_properties."""

    # ── accounts: create the enum type ───────────────────────────────────────
    accounttype_enum = sa.Enum("manual", "schwab", "ibkr", name="accounttype")
    accounttype_enum.create(op.get_bind(), checkfirst=True)

    # ── accounts: drop broker column ─────────────────────────────────────────
    op.drop_column("accounts", "broker")

    # ── accounts: add type column ─────────────────────────────────────────────
    op.add_column(
        "accounts",
        sa.Column(
            "type",
            sa.Enum("manual", "schwab", "ibkr", name="accounttype", create_type=False),
            nullable=False,
            server_default="manual",
            comment="Account/broker type (manual, schwab, or ibkr).",
        ),
    )

    # ── account_properties table ──────────────────────────────────────────────
    op.create_table(
        "account_properties",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "account_id",
            UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "key",
            sa.String(50),
            nullable=False,
            comment=(
                "Property key identifier, e.g. 'SCHWAB_APP_KEY', 'SCHWAB_APP_SECRET', "
                "'IBKR_FLEX_TOKEN', 'IBKR_FLEX_QUERY_ID'."
            ),
        ),
        sa.Column(
            "value",
            sa.Text(),
            nullable=False,
            comment="Fernet-encrypted property value.",
        ),
        sa.UniqueConstraint(
            "account_id",
            "key",
            name="uq_account_properties_account_key",
        ),
    )

    op.create_index(
        "ix_account_properties_account_id",
        "account_properties",
        ["account_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop account_properties, remove accounts.type, restore accounts.broker."""
    op.drop_index("ix_account_properties_account_id", table_name="account_properties")
    op.drop_table("account_properties")

    op.drop_column("accounts", "type")

    # Re-add the broker column
    op.add_column(
        "accounts",
        sa.Column(
            "broker",
            sa.String(50),
            nullable=True,
        ),
    )

    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS accounttype")
