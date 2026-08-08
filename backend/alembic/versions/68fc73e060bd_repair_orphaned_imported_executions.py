"""repair orphaned imported executions

Revision ID: 68fc73e060bd
Revises: 7647be54482c
Create Date: 2026-08-02 21:16:49.802495

"""

import logging
from collections.abc import Sequence
from decimal import Decimal

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "68fc73e060bd"
down_revision: str | None = "7647be54482c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

logger = logging.getLogger("alembic.runtime.migration")

# Data-only, idempotent repair for the LOGI-class defect
# (execution-metadata-protection-hardening D13): the raw-pipeline
# reconcile-before-skip bug (D8) let closing executions land with
# `trade_id IS NULL` when they matched a metadata-protected position. This
# migration links each such orphan to its unique open, complementary trade
# and recomputes the trade's close fields. Ambiguous or unmatched orphans
# are left untouched and logged rather than guessed.
_ORPHAN_CANDIDATES_SQL = """
    WITH orphans AS (
        SELECT le.id AS execution_id, le.user_id, le.account_id, le.symbol,
               le.direction, le.quantity, le.price, le.commission,
               le.executed_at
        FROM logical_executions le
        WHERE le.origin = 'imported'
          AND le.deleted = false
          AND le.trade_id IS NULL
    ),
    candidates AS (
        SELECT o.execution_id, t.id AS trade_id, t.direction AS trade_direction,
               t.entry_price, t.multiplier, t.commission AS trade_commission
        FROM orphans o
        JOIN trades t
          ON t.user_id = o.user_id
         AND t.account_id IS NOT DISTINCT FROM o.account_id
         AND t.symbol = o.symbol
         AND t.closed_at IS NULL
         AND t.direction <> o.direction
         AND t.quantity = o.quantity
    ),
    match_counts AS (
        SELECT execution_id, COUNT(*) AS n
        FROM candidates
        GROUP BY execution_id
    ),
    unique_match AS (
        SELECT c.*
        FROM candidates c
        JOIN match_counts mc ON mc.execution_id = c.execution_id AND mc.n = 1
    )
    SELECT o.execution_id, o.symbol, o.executed_at, o.price, o.commission,
           o.quantity, COALESCE(mc.n, 0) AS candidate_count,
           um.trade_id, um.trade_direction, um.entry_price, um.multiplier,
           um.trade_commission
    FROM orphans o
    LEFT JOIN match_counts mc ON mc.execution_id = o.execution_id
    LEFT JOIN unique_match um ON um.execution_id = o.execution_id
"""


def upgrade() -> None:
    conn = op.get_bind()

    rows = conn.execute(sa.text(_ORPHAN_CANDIDATES_SQL)).fetchall()

    repaired = 0
    skipped = 0
    for row in rows:
        if row.candidate_count != 1 or row.trade_id is None:
            # Zero or multiple candidate trades — do not guess.
            logger.warning(
                "orphan_repair_skipped execution_id=%s symbol=%s executed_at=%s candidate_count=%d",
                row.execution_id,
                row.symbol,
                row.executed_at,
                row.candidate_count,
            )
            skipped += 1
            continue

        multiplier = Decimal(row.multiplier)
        if row.trade_direction == "LONG":
            pnl = (row.price - row.entry_price) * row.quantity * multiplier
        else:
            pnl = (row.entry_price - row.price) * row.quantity * multiplier
        net_pnl = pnl - (row.trade_commission + row.commission)

        conn.execute(
            sa.text("UPDATE logical_executions SET trade_id = :trade_id WHERE id = :execution_id"),
            {"trade_id": row.trade_id, "execution_id": row.execution_id},
        )
        conn.execute(
            sa.text(
                """
                UPDATE trades
                SET exit_price = :exit_price,
                    closed_at = :closed_at,
                    pnl = :pnl,
                    net_pnl = :net_pnl,
                    commission = commission + :commission_add
                WHERE id = :trade_id
                """
            ),
            {
                "exit_price": row.price,
                "closed_at": row.executed_at,
                "pnl": pnl,
                "net_pnl": net_pnl,
                "commission_add": row.commission,
                "trade_id": row.trade_id,
            },
        )
        repaired += 1

    logger.info(
        "orphan_repair_migration repaired=%d skipped=%d",
        repaired,
        skipped,
    )


def downgrade() -> None:
    # No-op by design: a correct trade_id link is not "undone" — the prior
    # NULL state is the bug being fixed, not a state worth restoring.
    logger.info("orphan_repair_migration downgrade is a no-op")
