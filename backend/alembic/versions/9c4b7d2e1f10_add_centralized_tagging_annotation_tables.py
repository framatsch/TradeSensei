"""add centralized tagging and annotation tables

Revision ID: 9c4b7d2e1f10
Revises: aa41b963f861
Create Date: 2026-05-09 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c4b7d2e1f10"
down_revision: str | None = "aa41b963f861"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "taxonomies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("color_hex", sa.String(length=7), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("icon_identifier", sa.String(length=100), nullable=True),
        sa.Column(
            "is_archived",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("scope IN ('trades', 'checkins', 'both')", name="ck_taxonomies_scope"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "scope", name="uq_taxonomies_name_scope"),
    )
    op.create_index("ix_taxonomies_scope", "taxonomies", ["scope"], unique=False)
    op.create_index("ix_taxonomies_archived", "taxonomies", ["is_archived"], unique=False)

    op.create_table(
        "annotation_definitions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("scale_labels", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("icon_identifier", sa.String(length=100), nullable=True),
        sa.Column(
            "is_archived",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "type IN ('int', 'float', 'bool', 'string_enum')",
            name="ck_annotation_definitions_type",
        ),
        sa.CheckConstraint(
            "scope IN ('trades', 'checkins', 'both')",
            name="ck_annotation_definitions_scope",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "scope", name="uq_annotation_definitions_name_scope"),
    )
    op.create_index(
        "ix_annotation_definitions_scope",
        "annotation_definitions",
        ["scope"],
        unique=False,
    )
    op.create_index(
        "ix_annotation_definitions_archived",
        "annotation_definitions",
        ["is_archived"],
        unique=False,
    )

    op.create_table(
        "trade_taxonomies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("trade_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("taxonomy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["taxonomy_id"], ["taxonomies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["trade_id"], ["trades.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trade_id", "taxonomy_id", name="uq_trade_taxonomy_pair"),
    )

    op.create_table(
        "checkin_taxonomies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("checkin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("taxonomy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["checkin_id"], ["daily_checkins.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["taxonomy_id"], ["taxonomies.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("checkin_id", "taxonomy_id", name="uq_checkin_taxonomy_pair"),
    )

    op.create_table(
        "trade_annotations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("trade_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("annotation_definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("value_int", sa.Integer(), nullable=True),
        sa.Column("value_float", sa.Numeric(18, 8), nullable=True),
        sa.Column("value_bool", sa.Boolean(), nullable=True),
        sa.Column("value_string", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "num_nonnulls(value_int, value_float, value_bool, value_string) = 1",
            name="ck_trade_annotations_exactly_one_value",
        ),
        sa.ForeignKeyConstraint(
            ["annotation_definition_id"],
            ["annotation_definitions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["trade_id"], ["trades.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trade_id",
            "annotation_definition_id",
            name="uq_trade_annotation_pair",
        ),
    )

    op.create_table(
        "checkin_annotations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("checkin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("annotation_definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("value_int", sa.Integer(), nullable=True),
        sa.Column("value_float", sa.Numeric(18, 8), nullable=True),
        sa.Column("value_bool", sa.Boolean(), nullable=True),
        sa.Column("value_string", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "num_nonnulls(value_int, value_float, value_bool, value_string) = 1",
            name="ck_checkin_annotations_exactly_one_value",
        ),
        sa.ForeignKeyConstraint(
            ["annotation_definition_id"],
            ["annotation_definitions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["checkin_id"], ["daily_checkins.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "checkin_id",
            "annotation_definition_id",
            name="uq_checkin_annotation_pair",
        ),
    )


def downgrade() -> None:
    op.drop_table("checkin_annotations")
    op.drop_table("trade_annotations")
    op.drop_table("checkin_taxonomies")
    op.drop_table("trade_taxonomies")

    op.drop_index("ix_annotation_definitions_archived", table_name="annotation_definitions")
    op.drop_index("ix_annotation_definitions_scope", table_name="annotation_definitions")
    op.drop_table("annotation_definitions")

    op.drop_index("ix_taxonomies_archived", table_name="taxonomies")
    op.drop_index("ix_taxonomies_scope", table_name="taxonomies")
    op.drop_table("taxonomies")
