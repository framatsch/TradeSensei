"""Playbooks, tags, trade_tags, trade_notes tables; playbook_id FK on trades.

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-15 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create playbooks, tags, trade_tags, trade_notes tables and add playbook_id to trades."""

    # ── playbooks table ────────────────────────────────────────────────────────
    op.create_table(
        "playbooks",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_playbooks_user_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_playbooks_user_id", "playbooks", ["user_id"])
    op.create_index(
        "ix_playbooks_user_id_name",
        "playbooks",
        ["user_id", "name"],
        unique=True,
    )

    # updated_at trigger for playbooks
    op.execute("""
        CREATE TRIGGER playbooks_updated_at
        BEFORE UPDATE ON playbooks
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)

    # ── tags table ─────────────────────────────────────────────────────────────
    op.create_table(
        "tags",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("color", sa.String(7), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_tags_user_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_tags_user_id", "tags", ["user_id"])
    op.create_index(
        "ix_tags_user_id_name",
        "tags",
        ["user_id", "name"],
        unique=True,
    )

    # ── trade_tags association table ───────────────────────────────────────────
    op.create_table(
        "trade_tags",
        sa.Column(
            "trade_id",
            sa.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "tag_id",
            sa.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["trade_id"],
            ["trades.id"],
            name="fk_trade_tags_trade_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
            name="fk_trade_tags_tag_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("trade_id", "tag_id", name="pk_trade_tags"),
    )
    op.create_index("ix_trade_tags_tag_id", "trade_tags", ["tag_id"])

    # ── trade_notes table ──────────────────────────────────────────────────────
    op.create_table(
        "trade_notes",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "trade_id",
            sa.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("emotion", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["trade_id"],
            ["trades.id"],
            name="fk_trade_notes_trade_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_trade_notes_user_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_trade_notes_trade_id", "trade_notes", ["trade_id"])
    op.create_index("ix_trade_notes_user_id", "trade_notes", ["user_id"])

    # updated_at trigger for trade_notes
    op.execute("""
        CREATE TRIGGER trade_notes_updated_at
        BEFORE UPDATE ON trade_notes
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)

    # ── playbook_id FK on trades ───────────────────────────────────────────────
    op.add_column(
        "trades",
        sa.Column(
            "playbook_id",
            sa.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_trades_playbook_id",
        "trades",
        "playbooks",
        ["playbook_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_trades_playbook_id", "trades", ["playbook_id"])


def downgrade() -> None:
    """Remove playbook_id from trades; drop trade_notes, trade_tags, tags, playbooks."""
    # Drop playbook_id from trades
    op.drop_index("ix_trades_playbook_id", table_name="trades")
    op.drop_constraint("fk_trades_playbook_id", "trades", type_="foreignkey")
    op.drop_column("trades", "playbook_id")

    # Drop trade_notes
    op.execute("DROP TRIGGER IF EXISTS trade_notes_updated_at ON trade_notes")
    op.drop_index("ix_trade_notes_user_id", table_name="trade_notes")
    op.drop_index("ix_trade_notes_trade_id", table_name="trade_notes")
    op.drop_table("trade_notes")

    # Drop trade_tags
    op.drop_index("ix_trade_tags_tag_id", table_name="trade_tags")
    op.drop_table("trade_tags")

    # Drop tags
    op.drop_index("ix_tags_user_id_name", table_name="tags")
    op.drop_index("ix_tags_user_id", table_name="tags")
    op.drop_table("tags")

    # Drop playbooks
    op.execute("DROP TRIGGER IF EXISTS playbooks_updated_at ON playbooks")
    op.drop_index("ix_playbooks_user_id_name", table_name="playbooks")
    op.drop_index("ix_playbooks_user_id", table_name="playbooks")
    op.drop_table("playbooks")
