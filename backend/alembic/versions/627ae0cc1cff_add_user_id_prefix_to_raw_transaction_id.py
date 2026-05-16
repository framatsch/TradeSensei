# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""add_user_id_prefix_to_raw_transaction_id

Revision ID: 627ae0cc1cff
Revises: 1025c1183a57
Create Date: 2026-04-05 12:59:11.120226

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "627ae0cc1cff"
down_revision: str | None = "1025c1183a57"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
