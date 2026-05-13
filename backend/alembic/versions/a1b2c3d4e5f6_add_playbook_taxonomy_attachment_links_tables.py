"""add_playbook_taxonomy_attachment_links_tables

Revision ID: a1b2c3d4e5f6
Revises: ba90e0b3a3b7
Create Date: 2026-05-13 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "ba90e0b3a3b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. playbook_taxonomies — join table between playbooks and taxonomy definitions
    op.create_table(
        "playbook_taxonomies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("playbook_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("taxonomy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["playbook_id"],
            ["playbooks.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["taxonomy_id"],
            ["taxonomies.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("playbook_id", "taxonomy_id", name="uq_playbook_taxonomy_pair"),
    )
    op.create_index("ix_playbook_taxonomies_playbook_id", "playbook_taxonomies", ["playbook_id"])
    op.create_index("ix_playbook_taxonomies_taxonomy_id", "playbook_taxonomies", ["taxonomy_id"])

    # 2. playbook_attachments — image attachments for playbooks
    op.create_table(
        "playbook_attachments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("playbook_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("storage_url", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["playbook_id"],
            ["playbooks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_playbook_attachments_playbook_id", "playbook_attachments", ["playbook_id"])

    # 3. playbook_links — external labeled links for playbooks
    op.create_table(
        "playbook_links",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("playbook_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["playbook_id"],
            ["playbooks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_playbook_links_playbook_id", "playbook_links", ["playbook_id"])


def downgrade() -> None:
    op.drop_table("playbook_links")
    op.drop_table("playbook_attachments")
    op.drop_table("playbook_taxonomies")
