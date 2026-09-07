"""clear false user_modified markers

Revision ID: c4a8d2e9f301
Revises: 5f3d8c2a1b77
Create Date: 2026-09-06 22:20:00.000000

"""

import logging
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4a8d2e9f301"
down_revision: str | None = "5f3d8c2a1b77"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

logger = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    conn = op.get_bind()

    clear_result = conn.execute(
        sa.text(
            """
            UPDATE logical_executions AS le
            SET user_modified = false
            WHERE le.user_modified = true
              AND le.origin <> 'manual'
              AND (
                    (
                        le.origin = 'split'
                        AND le.parent_id IS NOT NULL
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM broker_raw_transactions brt
                        WHERE brt.id = le.source_id
                          AND brt.quantity = le.quantity
                          AND brt.price = le.price
                          AND brt.direction = le.direction::text
                          AND brt.executed_at = le.executed_at
                    )
                )
            """
        )
    )

    skipped_rows = conn.execute(
        sa.text(
            """
            SELECT
                le.id,
                le.user_id,
                le.account_id,
                le.symbol,
                le.origin,
                le.source_id
            FROM logical_executions le
            WHERE le.user_modified = true
            ORDER BY le.executed_at, le.id
            """
        )
    ).fetchall()

    for row in skipped_rows:
        logger.warning(
            "user_modified_cleanup_skipped execution_id=%s user_id=%s account_id=%s symbol=%s origin=%s source_id=%s",
            row.id,
            row.user_id,
            row.account_id,
            row.symbol,
            row.origin,
            row.source_id,
        )

    logger.info(
        "user_modified_cleanup_migration cleared=%d skipped=%d",
        int(getattr(clear_result, "rowcount", 0) or 0),
        len(skipped_rows),
    )


def downgrade() -> None:
    logger.info("user_modified_cleanup_migration downgrade is a no-op")
