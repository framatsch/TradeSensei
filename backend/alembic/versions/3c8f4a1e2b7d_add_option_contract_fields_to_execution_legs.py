"""add option contract fields to execution legs

Revision ID: 3c8f4a1e2b7d
Revises: e8a7d3c91b42
Create Date: 2026-07-18 18:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.utils.occ import parse_occ_option

# revision identifiers, used by Alembic.
revision: str = "3c8f4a1e2b7d"
down_revision: str | None = "e8a7d3c91b42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "logical_executions",
        sa.Column(
            "strike",
            sa.Numeric(18, 8),
            nullable=True,
            comment="Option strike price derived from OCC symbol.",
        ),
    )
    op.add_column(
        "logical_executions",
        sa.Column(
            "expiry",
            sa.Date(),
            nullable=True,
            comment="Option expiry date derived from OCC symbol.",
        ),
    )
    op.add_column(
        "logical_executions",
        sa.Column(
            "option_type",
            sa.String(length=1),
            nullable=True,
            comment="Option type derived from OCC symbol: 'C' or 'P'.",
        ),
    )

    op.add_column(
        "broker_raw_transactions",
        sa.Column(
            "strike",
            sa.Numeric(18, 8),
            nullable=True,
            comment="Option strike price derived from OCC symbol.",
        ),
    )
    op.add_column(
        "broker_raw_transactions",
        sa.Column(
            "expiry",
            sa.Date(),
            nullable=True,
            comment="Option expiry date derived from OCC symbol.",
        ),
    )
    op.add_column(
        "broker_raw_transactions",
        sa.Column(
            "option_type",
            sa.String(length=1),
            nullable=True,
            comment="Option type derived from OCC symbol: 'C' or 'P'.",
        ),
    )

    bind = op.get_bind()

    option_rows = bind.execute(
        sa.text(
            """
            SELECT id, raw_data ->> 'symbol' AS occ_symbol
            FROM broker_raw_transactions
            WHERE asset_class = 'OPTION'
            """
        )
    )

    for row in option_rows:
        row_id = row[0]
        occ_symbol = row[1] or ""
        strike, expiry, option_type = parse_occ_option(str(occ_symbol).upper())
        if strike is None and expiry is None and option_type is None:
            continue

        bind.execute(
            sa.text(
                """
                UPDATE broker_raw_transactions
                SET strike = :strike,
                    expiry = :expiry,
                    option_type = :option_type
                WHERE id = :row_id
                """
            ),
            {
                "row_id": row_id,
                "strike": strike,
                "expiry": expiry,
                "option_type": option_type,
            },
        )

    bind.execute(
        sa.text(
            """
            UPDATE logical_executions AS le
            SET strike = brt.strike,
                expiry = brt.expiry,
                option_type = brt.option_type
            FROM broker_raw_transactions AS brt
            WHERE le.source_id = brt.id
              AND le.asset_class = 'OPTION'
              AND (
                brt.strike IS NOT NULL
                OR brt.expiry IS NOT NULL
                OR brt.option_type IS NOT NULL
              )
            """
        )
    )


def downgrade() -> None:
    op.drop_column("broker_raw_transactions", "option_type")
    op.drop_column("broker_raw_transactions", "expiry")
    op.drop_column("broker_raw_transactions", "strike")

    op.drop_column("logical_executions", "option_type")
    op.drop_column("logical_executions", "expiry")
    op.drop_column("logical_executions", "strike")
