"""seed_system_filters

Revision ID: 28989209dc97
Revises: 28989209dc96
Create Date: 2026-03-27 13:01:32.480759

"""
from typing import Sequence, Union
import json

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '28989209dc97'
down_revision: Union[str, None] = '28989209dc96'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    system_filters = [
        {
            "name": "All Winners",
            "scope": "SYSTEM",
            "definition": json.dumps({"pnl_positive": True}),
            "needs_review": False
        },
        {
            "name": "All Losers",
            "scope": "SYSTEM",
            "definition": json.dumps({"pnl_positive": False}),
            "needs_review": False
        },
        {
            "name": "Long Trades",
            "scope": "SYSTEM",
            "definition": json.dumps({"direction": "LONG"}),
            "needs_review": False
        },
        {
            "name": "Short Trades",
            "scope": "SYSTEM",
            "definition": json.dumps({"direction": "SHORT"}),
            "needs_review": False
        },
        {
            "name": "Equities Only",
            "scope": "SYSTEM",
            "definition": json.dumps({"asset_class": "EQUITY"}),
            "needs_review": False
        },
        {
            "name": "Options Only",
            "scope": "SYSTEM",
            "definition": json.dumps({"asset_class": "OPTION"}),
            "needs_review": False
        },
        {
            "name": "Open Trades",
            "scope": "SYSTEM",
            "definition": json.dumps({"status": "open"}),
            "needs_review": False
        }
    ]

    for f in system_filters:
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
            f
        )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text("DELETE FROM saved_trade_filters WHERE scope = 'SYSTEM'")
    )
