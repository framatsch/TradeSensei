"""seed_needs_review_filter

Revision ID: 28989209dc98
Revises: 28989209dc97
Create Date: 2026-04-10 18:30:00.000000

"""
import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '28989209dc98'
down_revision: str | None = '28989209dc97'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    filter_data = {
        "name": "Needs Review",
        "scope": "SYSTEM",
        "definition": json.dumps({"has_conflict": True}),
        "needs_review": False
    }

    bind.execute(
        sa.text(
            """
            INSERT INTO saved_trade_filters (name, scope, definition, needs_review)
            SELECT CAST(:name AS VARCHAR), CAST(:scope AS filter_scope_enum), CAST(:definition AS JSONB), CAST(:needs_review AS BOOLEAN)
            WHERE NOT EXISTS (
                SELECT 1 FROM saved_trade_filters 
                WHERE name = CAST(:name AS VARCHAR) AND scope = 'SYSTEM'
            )
            """
        ),
        filter_data
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text("DELETE FROM saved_trade_filters WHERE name = 'Needs Review' AND scope = 'SYSTEM'")
    )
