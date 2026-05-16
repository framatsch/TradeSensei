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

"""Repository for the ``logical_executions`` table."""

import uuid
from collections.abc import Iterator, Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import IMPORT_EXECUTIONS_BATCH_SIZE
from app.models.logical_execution import (
    EXECUTION_ORIGIN_IMPORTED,
    EXECUTION_ORIGIN_MANUAL,
    LogicalExecution,
)


class ExecutionRepository:
    """Repository for logical_executions table."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: The SQLAlchemy async session to use.
        """
        self.session = session

    async def list_by_trade_id(
        self,
        trade_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> Sequence[LogicalExecution]:
        """Fetch executions belonging to a specific trade.

        Args:
            trade_id: The ID of the trade.
            include_deleted: When False (default), excludes soft-deleted executions.

        Returns:
            A sequence of execution models ordered by execution time.
        """
        stmt = select(LogicalExecution).where(LogicalExecution.trade_id == trade_id)
        if not include_deleted:
            stmt = stmt.where(LogicalExecution.deleted.is_(False))
        stmt = stmt.order_by(LogicalExecution.executed_at.asc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_id(
        self,
        execution_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> LogicalExecution | None:
        """Fetch an execution by its primary key, optionally scoped to a user.

        Args:
            execution_id: The ID of the execution.
            user_id: When provided, restricts the lookup to this user's
                executions — returns None if the execution belongs to a
                different user.

        Returns:
            The execution model if found (and owned by user when specified),
            otherwise None.
        """
        stmt = select(LogicalExecution).where(LogicalExecution.id == execution_id)
        if user_id is not None:
            stmt = stmt.where(LogicalExecution.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_ids(self, execution_ids: list[uuid.UUID]) -> list[LogicalExecution]:
        """Fetch executions by primary keys.

        Args:
            execution_ids: Execution UUIDs to fetch.

        Returns:
            Matching execution rows.
        """
        if not execution_ids:
            return []
        result = await self.session.execute(select(LogicalExecution).where(LogicalExecution.id.in_(execution_ids)))
        return list(result.scalars().all())

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID | None = None,
        origin: str | None = None,
        include_deleted: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[LogicalExecution]:
        """Return executions for a user with optional filters.

        Args:
            user_id: Owning user UUID.
            account_id: Optional account UUID filter.
            origin: Optional origin filter (imported|manual|merged|split).
            include_deleted: When False (default), excludes soft-deleted executions.
            limit: Optional max row count.
            offset: Number of rows to skip before reading.

        Returns:
            Matching executions ordered by execution time.
        """
        stmt = select(LogicalExecution).where(LogicalExecution.user_id == user_id)
        if account_id is not None:
            stmt = stmt.where(LogicalExecution.account_id == account_id)
        if origin is not None:
            stmt = stmt.where(LogicalExecution.origin == origin)
        if not include_deleted:
            stmt = stmt.where(LogicalExecution.deleted.is_(False))
        stmt = stmt.order_by(
            LogicalExecution.executed_at.asc(),
            LogicalExecution.id.asc(),  # Stable tie-breaker for pagination
        )
        if offset > 0:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **kwargs: object) -> LogicalExecution:
        """Create a new execution record.

        Args:
            **kwargs: Field values for the new execution.

        Returns:
            The newly created and flushed execution model.
        """
        execution = LogicalExecution(**kwargs)
        self.session.add(execution)
        await self.session.flush()
        return execution

    async def update(self, execution: LogicalExecution, **kwargs: object) -> LogicalExecution:
        """Update an existing execution record in-place.

        Args:
            execution: The model instance to update.
            **kwargs: The fields and values to update.

        Returns:
            The updated execution model.
        """
        for key, value in kwargs.items():
            if hasattr(execution, key):
                setattr(execution, key, value)

        await self.session.flush()
        return execution

    async def soft_delete(self, execution_id: uuid.UUID) -> bool:
        """Soft-delete an execution by setting deleted=True.

        Args:
            execution_id: The ID of the execution to soft-delete.

        Returns:
            True if the execution was found and soft-deleted, False otherwise.
        """
        stmt = update(LogicalExecution).where(LogicalExecution.id == execution_id).values(deleted=True)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return bool(getattr(result, "rowcount", 0) > 0)

    async def restore(self, execution_id: uuid.UUID) -> bool:
        """Restore a soft-deleted execution by setting deleted=False.

        Args:
            execution_id: The ID of the execution to restore.

        Returns:
            True if the execution was found and restored, False otherwise.
        """
        stmt = update(LogicalExecution).where(LogicalExecution.id == execution_id).values(deleted=False)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return bool(getattr(result, "rowcount", 0) > 0)

    async def delete(self, execution_id: uuid.UUID) -> bool:
        """Hard-delete an execution by ID (used for manual executions only).

        Args:
            execution_id: The ID of the execution to delete.

        Returns:
            True if an execution was deleted, False if it was not found.
        """
        stmt = delete(LogicalExecution).where(LogicalExecution.id == execution_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return bool(getattr(result, "rowcount", 0) > 0)

    async def reassign_to_trade(self, execution_ids: list[uuid.UUID], trade_id: uuid.UUID | None) -> int:
        """Update the trade_id for multiple executions simultaneously.

        Useful for merges and splits.

        Args:
            execution_ids: List of execution IDs to reassign.
            trade_id: The target trade ID, or None to detach.

        Returns:
            The number of executions updated.
        """
        if not execution_ids:
            return 0

        stmt = update(LogicalExecution).where(LogicalExecution.id.in_(execution_ids)).values(trade_id=trade_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        # Expire any session-cached execution instances so that subsequent
        # queries for the new trade_id see the updated data.
        for instance in list(self.session.identity_map.values()):
            if isinstance(instance, LogicalExecution) and instance.id in execution_ids:
                self.session.expire(instance)
        return int(getattr(result, "rowcount", 0))

    async def update_trade_id(self, execution_id: uuid.UUID, trade_id: uuid.UUID) -> bool:
        """Update trade_id for a single execution (used in split-aware linking).

        Args:
            execution_id: The ID of the execution to update.
            trade_id: The target trade ID to assign.

        Returns:
            True if the execution was found and updated, False otherwise.
        """
        stmt = update(LogicalExecution).where(LogicalExecution.id == execution_id).values(trade_id=trade_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return bool(getattr(result, "rowcount", 0) > 0)

    async def get_by_parent_id(self, parent_id: uuid.UUID) -> list[LogicalExecution]:
        """Query split children by their parent_id (used in split-aware linking).

        Args:
            parent_id: The parent execution ID to find children for.

        Returns:
            List of child executions with the specified parent_id.
        """
        stmt = select(LogicalExecution).where(LogicalExecution.parent_id == parent_id).order_by(LogicalExecution.executed_at.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_orphaned_children(self, user_id: uuid.UUID, account_id: uuid.UUID) -> list[LogicalExecution]:
        """Find execution children with trade_id=NULL after import (cleanup helper).

        Args:
            user_id: Owning user UUID.
            account_id: Account UUID to search within.

        Returns:
            List of orphaned child executions that need trade assignment.
        """
        from app.models.logical_execution import EXECUTION_ORIGIN_SPLIT

        stmt = (
            select(LogicalExecution)
            .where(
                LogicalExecution.user_id == user_id,
                LogicalExecution.account_id == account_id,
                LogicalExecution.origin == EXECUTION_ORIGIN_SPLIT,
                LogicalExecution.trade_id.is_(None),
                LogicalExecution.deleted.is_(False),
            )
            .order_by(LogicalExecution.executed_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def bulk_update_trade_ids(self, execution_trade_pairs: list[tuple[uuid.UUID, uuid.UUID]]) -> int:
        """Bulk update trade_ids for multiple executions for performance.

        Args:
            execution_trade_pairs: List of (execution_id, trade_id) tuples.

        Returns:
            Total number of executions updated.
        """
        if not execution_trade_pairs:
            return 0

        total_updated = 0

        # Group by trade_id to minimize the number of queries
        trade_groups: dict[uuid.UUID, list[uuid.UUID]] = {}
        for execution_id, trade_id in execution_trade_pairs:
            if trade_id not in trade_groups:
                trade_groups[trade_id] = []
            trade_groups[trade_id].append(execution_id)

        # Execute updates in batched chunks per trade_id.
        for trade_id, execution_ids in trade_groups.items():
            for execution_id_batch in self.iter_batches(execution_ids):
                stmt = update(LogicalExecution).where(LogicalExecution.id.in_(execution_id_batch)).values(trade_id=trade_id)
                result = await self.session.execute(stmt)
                total_updated += getattr(result, "rowcount", 0)

        await self.session.flush()

        # Expire cached instances
        all_execution_ids = [pair[0] for pair in execution_trade_pairs]
        for instance in list(self.session.identity_map.values()):
            if isinstance(instance, LogicalExecution) and instance.id in all_execution_ids:
                self.session.expire(instance)

        return total_updated

    async def delete_all_for_account(self, user_id: uuid.UUID, account_id: uuid.UUID) -> int:
        """Hard-delete all executions for a user+account (used in fresh-start).

        Args:
            user_id: Owning user UUID.
            account_id: Account UUID whose executions are deleted.

        Returns:
            Number of rows deleted.
        """
        stmt = delete(LogicalExecution).where(
            LogicalExecution.user_id == user_id,
            LogicalExecution.account_id == account_id,
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return int(getattr(result, "rowcount", 0))

    @staticmethod
    def iter_batches(
        execution_ids: Sequence[uuid.UUID],
        batch_size: int = IMPORT_EXECUTIONS_BATCH_SIZE,
    ) -> Iterator[list[uuid.UUID]]:
        """Yield execution IDs in fixed-size batches.

        Args:
            execution_ids: Execution UUIDs to process.
            batch_size: Maximum IDs per batch.

        Yields:
            Lists of execution UUIDs with size ``<= batch_size``.
        """
        if batch_size <= 0:
            raise ValueError("batch_size must be > 0")
        for offset in range(0, len(execution_ids), batch_size):
            yield list(execution_ids[offset : offset + batch_size])


# Expose origin constants for callers that just need the string values
__all__ = [
    "ExecutionRepository",
    "EXECUTION_ORIGIN_IMPORTED",
    "EXECUTION_ORIGIN_MANUAL",
]
