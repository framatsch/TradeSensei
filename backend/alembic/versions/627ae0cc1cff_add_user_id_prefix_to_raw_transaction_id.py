"""add_user_id_prefix_to_raw_transaction_id

Revision ID: 627ae0cc1cff
Revises: 1025c1183a57
Create Date: 2026-04-05 12:59:11.120226

"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "627ae0cc1cff"
down_revision: Union[str, None] = "1025c1183a57"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update foreign keys safely
    op.execute(
        """
        ALTER TABLE transaction_execution_mappings
        DROP CONSTRAINT IF EXISTS transaction_execution_mappings_raw_transaction_id_fkey;
        """
    )
    op.execute(
        """
        UPDATE transaction_execution_mappings t
        SET raw_transaction_id = b.user_id::text || ':' || t.raw_transaction_id
        FROM broker_raw_transactions b
        WHERE t.raw_transaction_id = b.id
        AND b.id NOT LIKE b.user_id::text || ':%';
        """
    )
    op.execute(
        """
        UPDATE broker_raw_transactions
        SET id = user_id::text || ':' || id
        WHERE id NOT LIKE user_id::text || ':%';
        """
    )
    op.execute(
        """
        ALTER TABLE transaction_execution_mappings
        ADD CONSTRAINT transaction_execution_mappings_raw_transaction_id_fkey
        FOREIGN KEY (raw_transaction_id) REFERENCES broker_raw_transactions(id)
        ON DELETE CASCADE;
        """
    )


def downgrade() -> None:
    pass
