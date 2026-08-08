"""backfill execution metadata protection

Revision ID: 7647be54482c
Revises: 2866995ad90d
Create Date: 2026-08-01 22:37:20.384064

"""

import logging
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7647be54482c"
down_revision: str | None = "2866995ad90d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

logger = logging.getLogger("alembic.runtime.migration")

# Divergence tolerance for comparing an imported execution's price/quantity/
# commission against its linked BrokerRawTransaction. A difference larger
# than this epsilon is treated as a genuine user edit rather than floating
# point/Decimal rounding noise.
_DIVERGENCE_TOLERANCE = "0.0000001"


def upgrade() -> None:
    conn = op.get_bind()

    metadata_predicate = """
        (
            (trades.journal IS NOT NULL AND trades.journal <> '')
            OR trades.user_rating IS NOT NULL
            OR COALESCE(trades.image_urls, '[]'::jsonb) <> '[]'::jsonb
            OR trades.tradingview_link IS NOT NULL
            OR trades.playbook_id IS NOT NULL
            OR EXISTS (
                SELECT 1
                FROM trade_notes tn
                WHERE tn.trade_id = trades.id
            )
            OR EXISTS (
                SELECT 1
                FROM trade_taxonomies tt
                WHERE tt.trade_id = trades.id
            )
            OR EXISTS (
                SELECT 1
                FROM trade_annotations ta
                WHERE ta.trade_id = trades.id
            )
        )
    """

    marked_trades_result = conn.execute(
        sa.text(
            f"""
            UPDATE trades
            SET is_manually_edited = true
            WHERE is_manually_edited IS DISTINCT FROM true
              AND {metadata_predicate}
            """
        )
    )

    marked_executions_for_metadata_result = conn.execute(
        sa.text(
            f"""
            UPDATE logical_executions
            SET user_modified = true
            WHERE deleted = false
              AND user_modified IS DISTINCT FROM true
              AND trade_id IN (
                  SELECT trades.id
                  FROM trades
                  WHERE {metadata_predicate}
              )
            """
        )
    )

    marked_executions_for_divergence_result = conn.execute(
        sa.text(
            f"""
            UPDATE logical_executions AS le
            SET user_modified = true
            FROM broker_raw_transactions AS brt
            WHERE le.source_id = brt.id
              AND le.origin = 'imported'
              AND le.deleted = false
              AND le.user_modified IS DISTINCT FROM true
              AND (
                  ABS(COALESCE(le.price, 0) - COALESCE(brt.price, 0)) > {_DIVERGENCE_TOLERANCE}
                  OR ABS(COALESCE(le.quantity, 0) - COALESCE(brt.quantity, 0)) > {_DIVERGENCE_TOLERANCE}
                  OR ABS(COALESCE(le.commission, 0) - COALESCE(brt.commission, 0)) > {_DIVERGENCE_TOLERANCE}
              )
            """
        )
    )

    logger.info(
        "execution_metadata_backfill trades_marked=%d executions_marked_from_metadata=%d executions_marked_from_divergence=%d",
        int(getattr(marked_trades_result, "rowcount", 0) or 0),
        int(getattr(marked_executions_for_metadata_result, "rowcount", 0) or 0),
        int(getattr(marked_executions_for_divergence_result, "rowcount", 0) or 0),
    )


def downgrade() -> None:
    # No-op by design: pre-migration boolean state is unrecoverable and clearing
    # these flags would re-open the metadata-loss path on subsequent imports.
    logger.info("execution_metadata_backfill downgrade is a no-op")
