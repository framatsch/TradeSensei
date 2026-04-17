"""simplified execution model: rename status->origin, add deleted/user_modified/parent_id, add suppressed

Revision ID: a1b2c3d4e5f6
Revises: f97ff74cda3d
Create Date: 2026-04-17 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "b8d1e4f2a9c3"
down_revision: Union[str, None] = "4e095dd6e4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply the simplified execution model schema changes.

    Changes:
    1. Rename logical_executions.status -> origin (TEXT with CHECK constraint)
    2. Add logical_executions.deleted BOOLEAN NOT NULL DEFAULT false
    3. Add logical_executions.user_modified BOOLEAN NOT NULL DEFAULT false
    4. Add logical_executions.parent_id INT nullable FK -> logical_executions(id)
    5. Add broker_raw_transactions.suppressed BOOLEAN NOT NULL DEFAULT false
    6. Add indexes for new columns
    """
    # --- Step 1: Add new TEXT origin column ---
    op.add_column(
        "logical_executions",
        sa.Column(
            "origin",
            sa.Text(),
            nullable=True,  # temporarily nullable to allow migration of existing rows
            comment="Execution provenance: imported | manual | merged | split",
        ),
    )

    # --- Step 2: Copy existing status values into origin column ---
    # Map old EDITED status to 'imported' since origin only has 4 values
    op.execute(
        """
        UPDATE logical_executions
        SET origin = CASE
            WHEN status::text = 'edited' THEN 'imported'
            ELSE status::text
        END
        """
    )

    # --- Step 3: Make origin NOT NULL now that data is populated ---
    op.alter_column("logical_executions", "origin", nullable=False)

    # --- Step 4: Add CHECK constraint on origin ---
    op.execute(
        """
        ALTER TABLE logical_executions
        ADD CONSTRAINT ck_le_origin
        CHECK (origin IN ('imported', 'manual', 'merged', 'split'))
        """
    )

    # --- Step 5: Drop old status column ---
    # First drop the index on status
    op.drop_index("ix_le_status", table_name="logical_executions")

    # Drop the enum-typed status column
    op.drop_column("logical_executions", "status")

    # --- Step 6: Drop the old execution_status_enum type if it exists ---
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'execution_status_enum') THEN
                DROP TYPE execution_status_enum;
            END IF;
        END $$
        """
    )

    # --- Step 7: Add deleted column ---
    op.add_column(
        "logical_executions",
        sa.Column(
            "deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Soft-delete flag. When true, excluded from aggregation.",
        ),
    )

    # --- Step 8: Add user_modified column ---
    op.add_column(
        "logical_executions",
        sa.Column(
            "user_modified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment=(
                "Set to true automatically when a user patches an imported execution."
            ),
        ),
    )

    # --- Step 9: Add parent_id column ---
    op.add_column(
        "logical_executions",
        sa.Column(
            "parent_id",
            UUID(as_uuid=True),
            nullable=True,
            comment=(
                "For split/merge lineage: FK to the original LogicalExecution. "
                "Set to NULL when ON DELETE SET NULL."
            ),
        ),
    )

    # Add the FK constraint for parent_id
    op.create_foreign_key(
        "fk_le_parent_id",
        "logical_executions",
        "logical_executions",
        ["parent_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # --- Step 10: Add suppressed column to broker_raw_transactions ---
    op.add_column(
        "broker_raw_transactions",
        sa.Column(
            "suppressed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment=(
                "When true, this raw transaction is permanently excluded from "
                "all future imports."
            ),
        ),
    )

    # --- Step 11: Add new indexes ---
    op.create_index(
        "ix_le_trade_id_deleted",
        "logical_executions",
        ["trade_id", "deleted"],
    )
    op.create_index(
        "ix_le_parent_id",
        "logical_executions",
        ["parent_id"],
    )
    op.create_index(
        "ix_le_origin",
        "logical_executions",
        ["origin"],
    )
    op.create_index(
        "ix_brt_suppressed",
        "broker_raw_transactions",
        ["suppressed"],
    )


def downgrade() -> None:
    """Revert the simplified execution model schema changes."""
    # Drop new indexes
    op.drop_index("ix_brt_suppressed", table_name="broker_raw_transactions")
    op.drop_index("ix_le_origin", table_name="logical_executions")
    op.drop_index("ix_le_parent_id", table_name="logical_executions")
    op.drop_index("ix_le_trade_id_deleted", table_name="logical_executions")

    # Drop suppressed column from broker_raw_transactions
    op.drop_column("broker_raw_transactions", "suppressed")

    # Drop parent_id FK and column
    op.drop_constraint("fk_le_parent_id", "logical_executions", type_="foreignkey")
    op.drop_column("logical_executions", "parent_id")

    # Drop new columns
    op.drop_column("logical_executions", "user_modified")
    op.drop_column("logical_executions", "deleted")

    # Re-create execution_status_enum type
    op.execute(
        """
        CREATE TYPE execution_status_enum AS ENUM (
            'imported', 'edited', 'manual', 'merged', 'split'
        )
        """
    )

    # Re-add status column
    op.add_column(
        "logical_executions",
        sa.Column(
            "status",
            sa.Enum(
                "imported",
                "edited",
                "manual",
                "merged",
                "split",
                name="execution_status_enum",
            ),
            nullable=True,
        ),
    )

    # Restore status values from origin
    op.execute(
        """
        UPDATE logical_executions
        SET status = origin::execution_status_enum
        """
    )

    # Make status NOT NULL
    op.alter_column("logical_executions", "status", nullable=False)

    # Re-create index on status
    op.create_index("ix_le_status", "logical_executions", ["status"])

    # Drop CHECK constraint on origin
    op.execute(
        "ALTER TABLE logical_executions DROP CONSTRAINT ck_le_origin"
    )

    # Drop origin column
    op.drop_column("logical_executions", "origin")
