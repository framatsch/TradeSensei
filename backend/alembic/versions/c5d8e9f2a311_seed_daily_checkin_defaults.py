"""seed_daily_checkin_defaults

Revision ID: c5d8e9f2a311
Revises: a7c3f61b9d20
Create Date: 2026-05-01 10:32:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5d8e9f2a311"
down_revision: str | None = "a7c3f61b9d20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(
        sa.text(
            """
            INSERT INTO checkin_field_definitions (user_id, field_name, field_type, is_active)
            SELECT u.id, defaults.field_name, defaults.field_type, true
            FROM users AS u
            CROSS JOIN (
                VALUES
                    ('mood-level', 'integer'),
                    ('focus', 'integer'),
                    ('rule-followed', 'boolean')
            ) AS defaults(field_name, field_type)
            ON CONFLICT ON CONSTRAINT uq_checkin_field_user_name DO NOTHING
            """
        )
    )

    bind.execute(
        sa.text(
            """
            INSERT INTO market_phase_definitions (user_id, name, label, color_hex, is_active)
            SELECT u.id, defaults.name, defaults.label, defaults.color_hex, true
            FROM users AS u
            CROSS JOIN (
                VALUES
                    ('bullish', 'Bullish', '#22c55e'),
                    ('bearish', 'Bearish', '#ef4444'),
                    ('sideways', 'Sideways', '#f59e0b'),
                    ('volatile', 'Volatile', '#8b5cf6')
            ) AS defaults(name, label, color_hex)
            ON CONFLICT ON CONSTRAINT uq_market_phase_user_name DO NOTHING
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            DELETE FROM checkin_field_definitions
            WHERE field_name IN ('mood-level', 'focus', 'rule-followed')
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM market_phase_definitions
            WHERE name IN ('bullish', 'bearish', 'sideways', 'volatile')
            """
        )
    )
