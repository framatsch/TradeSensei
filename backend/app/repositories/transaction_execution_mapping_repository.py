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

"""Async repository for ``transaction_execution_mappings`` table."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction_execution_mapping import TransactionExecutionMapping


class TransactionExecutionMappingRepository:
    """Data-access object for raw-to-logical execution mappings.

    Args:
        session: Open async SQLAlchemy session managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with a database session.

        Args:
            session: Database session used for all repository operations.
        """
        self._session = session

    async def exists_for_raw_transaction(self, raw_transaction_id: str) -> bool:
        """Return whether a raw transaction already has a logical mapping."""
        result = await self._session.execute(
            select(TransactionExecutionMapping.raw_transaction_id).where(TransactionExecutionMapping.raw_transaction_id == raw_transaction_id)
        )
        return result.scalar_one_or_none() is not None

    async def list_execution_ids_for_raw(
        self,
        raw_transaction_id: str,
    ) -> list[uuid.UUID]:
        """Return mapped logical execution IDs for one raw transaction."""
        result = await self._session.execute(
            select(TransactionExecutionMapping.logical_execution_id).where(TransactionExecutionMapping.raw_transaction_id == raw_transaction_id)
        )
        return list(result.scalars().all())
