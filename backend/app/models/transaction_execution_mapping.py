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

"""SQLAlchemy ORM model for the ``transaction_execution_mappings`` junction table.

This table implements the n:m relationship between
:class:`~app.models.broker_raw_transaction.BrokerRawTransaction` and
:class:`~app.models.logical_execution.LogicalExecution`.

For a standard 1:1 imported execution there is exactly one row linking the raw
transaction to its logical counterpart.  When a user merges multiple raw
transactions into one logical execution, or splits one raw transaction into
multiple logical executions, additional rows are created here to record the
complete lineage.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TransactionExecutionMapping(Base):
    """Junction table linking raw transactions to logical executions.

    The composite primary key ``(raw_transaction_id, logical_execution_id)``
    ensures each pair is recorded only once.

    Attributes:
        raw_transaction_id: Foreign key to
            :class:`~app.models.broker_raw_transaction.BrokerRawTransaction`.
        logical_execution_id: Foreign key to
            :class:`~app.models.logical_execution.LogicalExecution`.
        created_at: Row-creation timestamp set by the database.
    """

    __tablename__ = "transaction_execution_mappings"

    raw_transaction_id: Mapped[str] = mapped_column(
        ForeignKey("broker_raw_transactions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    logical_execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("logical_executions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        """Return a debug string for this mapping row.

        Returns:
            A string showing raw_transaction_id → logical_execution_id.
        """
        return f"<TransactionExecutionMapping raw={self.raw_transaction_id!r} logical={self.logical_execution_id!r}>"
