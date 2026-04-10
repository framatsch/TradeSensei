import uuid
from collections.abc import Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.logical_execution import ExecutionStatus, LogicalExecution


class ExecutionRepository:
    """Repository for logical_executions table."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: The SQLAlchemy async session to use.
        """
        self.session = session

    async def list_by_trade_id(self, trade_id: uuid.UUID) -> Sequence[LogicalExecution]:
        """Fetch all executions belonging to a specific trade.

        Args:
            trade_id: The ID of the trade.

        Returns:
            A sequence of execution models ordered by execution time.
        """
        stmt = (
            select(LogicalExecution)
            .where(LogicalExecution.trade_id == trade_id)
            .order_by(LogicalExecution.executed_at.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, execution_id: uuid.UUID) -> LogicalExecution | None:
        """Fetch an execution by its primary key.

        Args:
            execution_id: The ID of the execution.

        Returns:
            The execution model if found, otherwise None.
        """
        stmt = select(LogicalExecution).where(LogicalExecution.id == execution_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_ids(
        self, execution_ids: list[uuid.UUID]
    ) -> list[LogicalExecution]:
        """Fetch executions by primary keys.

        Args:
            execution_ids: Execution UUIDs to fetch.

        Returns:
            Matching execution rows.
        """
        if not execution_ids:
            return []
        result = await self.session.execute(
            select(LogicalExecution).where(LogicalExecution.id.in_(execution_ids))
        )
        return list(result.scalars().all())

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID | None = None,
        status: ExecutionStatus | None = None,
    ) -> list[LogicalExecution]:
        """Return executions for a user with optional filters.

        Args:
            user_id: Owning user UUID.
            account_id: Optional account UUID filter.
            status: Optional execution status filter.

        Returns:
            Matching executions ordered by execution time.
        """
        stmt = select(LogicalExecution).where(LogicalExecution.user_id == user_id)
        if account_id is not None:
            stmt = stmt.where(LogicalExecution.account_id == account_id)
        if status is not None:
            stmt = stmt.where(LogicalExecution.status == status)
        stmt = stmt.order_by(LogicalExecution.executed_at.asc())
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

    async def update(
        self, execution: LogicalExecution, **kwargs: object
    ) -> LogicalExecution:
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

    async def delete(self, execution_id: uuid.UUID) -> bool:
        """Delete an execution by ID.

        Args:
            execution_id: The ID of the execution to delete.

        Returns:
            True if an execution was deleted, False if it was not found.
        """
        stmt = delete(LogicalExecution).where(LogicalExecution.id == execution_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return bool(getattr(result, "rowcount", 0) > 0)

    async def reassign_to_trade(
        self, execution_ids: list[uuid.UUID], trade_id: uuid.UUID | None
    ) -> int:
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

        stmt = (
            update(LogicalExecution)
            .where(LogicalExecution.id.in_(execution_ids))
            .values(trade_id=trade_id)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return int(getattr(result, "rowcount", 0))
