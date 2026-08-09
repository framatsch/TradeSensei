"""add unique corporate action user/symbol/date

Revision ID: 8d2f4a1c9b71
Revises: 7647be54482c
Create Date: 2026-08-09 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "8d2f4a1c9b71"
down_revision: str | None = "7647be54482c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    duplicates = conn.execute(
        sa.text(
            """
            SELECT user_id, symbol, date, COUNT(*) AS cnt
            FROM corporate_actions
            GROUP BY user_id, symbol, date
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()
    if duplicates:
        raise RuntimeError("Duplicate corporate_actions rows exist for (user_id, symbol, date). Resolve duplicates before applying migration.")

    op.create_unique_constraint(
        "uq_corporate_actions_user_symbol_date",
        "corporate_actions",
        ["user_id", "symbol", "date"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_corporate_actions_user_symbol_date",
        "corporate_actions",
        type_="unique",
    )
