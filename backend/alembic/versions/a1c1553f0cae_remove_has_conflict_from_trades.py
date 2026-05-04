"""remove_has_conflict_from_trades

Drop the ``has_conflict`` column from the ``trades`` table.
The conflict-detection feature is superseded by the simplified execution model
(Decision 5 / task 5.5): trades with all executions ``deleted=true`` simply
have a zero-quantity aggregation — no separate conflict flag is needed.

Revision ID: a1c1553f0cae
Revises: b8d1e4f2a9c3
Create Date: 2026-04-18 00:03:17.965592

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1c1553f0cae"
down_revision: Union[str, None] = "b8d1e4f2a9c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop has_conflict column from the trades table."""
    op.drop_column("trades", "has_conflict")


def downgrade() -> None:
    """Restore has_conflict column (defaults to false for existing rows)."""
    op.add_column(
        "trades",
        sa.Column(
            "has_conflict",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment=(
                "When True, the aggregated position does not reconcile with the "
                "broker's <OpenPosition> block.  Deprecated — retained for rollback only."
            ),
        ),
    )
