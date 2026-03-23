"""add_cash_transactions_table

Revision ID: f91cc12066ce
Revises: f08b3ef4719a
Create Date: 2026-03-22 16:40:20.320680

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f91cc12066ce"
down_revision: str | None = "f08b3ef4719a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enum type
    op.execute(
        "CREATE TYPE cash_transaction_type_enum AS ENUM ('DIVIDEND', 'WITHHOLDING_TAX', 'DEPOSIT', 'WITHDRAWAL', 'INTEREST', 'FEE', 'OTHER')"
    )

    # Create table
    op.create_table(
        "cash_transactions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM(
                "DIVIDEND",
                "WITHHOLDING_TAX",
                "DEPOSIT",
                "WITHDRAWAL",
                "INTEREST",
                "FEE",
                "OTHER",
                name="cash_transaction_type_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("symbol", sa.String(length=30), nullable=True),
        sa.Column("amount", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column(
            "amount_eur",
            sa.Numeric(precision=24, scale=8),
            nullable=True,
            comment="Amount converted to EUR at the Bundesbank daily rate on the transaction date.",
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", "date"),
    )

    # Create indexes
    op.create_index(
        "ix_cash_transactions_account_id",
        "cash_transactions",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        "ix_cash_transactions_account_id_date",
        "cash_transactions",
        ["account_id", "date"],
        unique=False,
    )
    op.create_index(
        "ix_cash_transactions_date", "cash_transactions", ["date"], unique=False
    )
    op.create_index(
        "ix_cash_transactions_type", "cash_transactions", ["type"], unique=False
    )

    # Convert to TimescaleDB hypertable
    op.execute(
        "SELECT create_hypertable('cash_transactions', 'date', chunk_time_interval => INTERVAL '1 year', if_not_exists => TRUE)"
    )


def downgrade() -> None:
    # Drop table (this also removes the hypertable)
    op.drop_table("cash_transactions")

    # Drop enum type
    op.execute("DROP TYPE cash_transaction_type_enum")
