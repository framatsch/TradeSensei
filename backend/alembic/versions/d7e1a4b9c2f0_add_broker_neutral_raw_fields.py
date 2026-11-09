"""add broker-neutral order_id, net_cash, is_mixed_execution to raw transactions

Revision ID: d7e1a4b9c2f0
Revises: c4a8d2e9f301
Create Date: 2026-11-09 12:00:00.000000

Promotes three IBKR-only ``raw_data`` keys to explicit columns so combo
grouping and position-flip detection no longer read broker-specific JSONB
keys. The backfill mirrors the runtime extraction it replaces exactly:

- ``order_id``: ``raw_data->>'brokerageOrderID'`` unchanged (an empty string
  stays an empty string — it is persisted as ``trades.broker_order_id``).
- ``net_cash``: ``raw_data->>'netCash'`` cast to numeric; values that are not
  numeric (the old ``CAST`` would have failed the whole import) become NULL.
- ``is_mixed_execution``: ``upper(raw_data->>'openCloseIndicator')`` contains
  ``C;O`` or ``O;C``.

Downgrade drops the columns; the source values remain in ``raw_data``.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7e1a4b9c2f0"
down_revision: str | None = "c4a8d2e9f301"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "broker_raw_transactions",
        sa.Column(
            "order_id",
            sa.String(length=100),
            nullable=True,
            comment="Broker order-level grouping key used for combo detection (IBKR brokerageOrderID).",
        ),
    )
    op.add_column(
        "broker_raw_transactions",
        sa.Column(
            "net_cash",
            sa.Numeric(precision=18, scale=8),
            nullable=True,
            comment="Signed cash effect of the execution as reported or derived by the broker adapter.",
        ),
    )
    op.add_column(
        "broker_raw_transactions",
        sa.Column(
            "is_mixed_execution",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="True when one execution both closes and opens a position (position flip).",
        ),
    )

    op.execute(
        sa.text(
            r"""
            UPDATE broker_raw_transactions SET
              order_id = raw_data->>'brokerageOrderID',
              net_cash = CASE
                WHEN raw_data->>'netCash' ~ '^\s*[+-]?([0-9]+\.?[0-9]*|\.[0-9]+)([eE][+-]?[0-9]+)?\s*$'
                  THEN (raw_data->>'netCash')::numeric
                ELSE NULL
              END,
              is_mixed_execution = (
                upper(coalesce(raw_data->>'openCloseIndicator', '')) LIKE '%C;O%'
                OR upper(coalesce(raw_data->>'openCloseIndicator', '')) LIKE '%O;C%'
              )
            WHERE raw_data ?| array['brokerageOrderID', 'netCash', 'openCloseIndicator']
            """
        )
    )


def downgrade() -> None:
    op.drop_column("broker_raw_transactions", "is_mixed_execution")
    op.drop_column("broker_raw_transactions", "net_cash")
    op.drop_column("broker_raw_transactions", "order_id")
