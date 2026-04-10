import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.logical_execution import ExecutionStatus, LogicalExecution
from app.repositories.execution import ExecutionRepository
from app.repositories.trade_repository import TradeRepository
from app.schemas.execution import LogicalExecutionCreate, LogicalExecutionUpdate

if TYPE_CHECKING:
    from app.models.trade import Trade


class ExecutionService:
    """Service layer for LogicalExecutions containing business logic."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the ExecutionService.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session
        self.execution_repo = ExecutionRepository(session)
        self.trade_repo = TradeRepository(session)

    async def list_for_trade(
        self, trade_id: uuid.UUID, user_id: uuid.UUID
    ) -> Sequence[LogicalExecution]:
        """List all executions for a specific trade, ensuring user ownership.

        Args:
            trade_id: The target trade ID.
            user_id: The authenticated user's ID.

        Returns:
            A sequence of logical executions.

        Raises:
            HTTPException 404: If the trade is not found or user lacks access.
        """
        trade = await self.trade_repo.get_by_id(trade_id)
        if not trade or trade.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found."
            )

        return await self.execution_repo.list_by_trade_id(trade_id)

    async def create_manual_execution(
        self, trade_id: uuid.UUID, user_id: uuid.UUID, data: LogicalExecutionCreate
    ) -> LogicalExecution:
        """Create a manual execution under a specific trade.

        Args:
            trade_id: Target trade ID.
            user_id: User ownership check.
            data: Payload with execution details.

        Returns:
            The created logical execution.

        Raises:
            HTTPException 404: If the trade is not found.
        """
        trade = await self.trade_repo.get_by_id(trade_id)
        if not trade or trade.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found."
            )

        # Create with status=manual and copy instrument props from trade
        execution = await self.execution_repo.create(
            user_id=user_id,
            account_id=trade.account_id,
            symbol=trade.symbol,
            asset_class=trade.asset_class,
            currency=trade.currency,
            multiplier=trade.multiplier,
            status=ExecutionStatus.MANUAL,
            trade_id=trade_id,
            **data.model_dump(exclude_unset=True),
        )

        await self._re_aggregate_trade(trade_id, user_id)
        await self.session.commit()
        return execution

    async def update_execution(
        self, execution_id: uuid.UUID, user_id: uuid.UUID, data: LogicalExecutionUpdate
    ) -> LogicalExecution:
        """Update an execution by ID and re-aggregate its parent trade.

        Args:
            execution_id: Target execution ID.
            user_id: The requesting user's ID.
            data: Payload containing update fields.

        Returns:
            The updated logical execution.

        Raises:
            HTTPException 404: If execution is not found or not owned by user.
        """
        execution = await self.execution_repo.get_by_id(execution_id)
        if not execution or execution.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found."
            )

        execution = await self.execution_repo.update(
            execution, **data.model_dump(exclude_unset=True)
        )
        if execution.trade_id:
            await self._re_aggregate_trade(execution.trade_id, user_id)

        await self.session.commit()
        return execution

    async def delete_execution(
        self, execution_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """Delete an execution. If the trade becomes empty, it is deleted.

        Args:
            execution_id: Execution to delete.
            user_id: User ownership check.

        Raises:
            HTTPException 404: If execution is not found or not owned by user.
        """
        execution = await self.execution_repo.get_by_id(execution_id)
        if not execution or execution.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found."
            )

        trade_id = execution.trade_id
        await self.execution_repo.delete(execution_id)

        if trade_id:
            remaining_executions = await self.execution_repo.list_by_trade_id(trade_id)
            if not remaining_executions:
                trade_to_delete = await self.trade_repo.get_by_id(trade_id)
                if trade_to_delete:
                    await self.trade_repo.delete(trade_to_delete)
            else:
                await self._re_aggregate_trade(trade_id, user_id)

        await self.session.commit()

    async def reassign_execution(
        self, execution_id: uuid.UUID, target_trade_id: uuid.UUID, user_id: uuid.UUID
    ) -> LogicalExecution:
        """Reassign an execution to another trade.

        Args:
            execution_id: Execution to reassign.
            target_trade_id: The ID of the target trade.
            user_id: User ownership check.

        Returns:
            The updated logical execution.

        Raises:
            HTTPException: If execution/trade is not found, or mismatch in
                symbol/account.
        """
        execution = await self.execution_repo.get_by_id(execution_id)
        if not execution or execution.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found."
            )

        target_trade = await self.trade_repo.get_by_id(target_trade_id)
        if not target_trade or target_trade.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Target trade not found."
            )

        if (
            execution.symbol != target_trade.symbol
            or execution.account_id != target_trade.account_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reassign: symbol or account mismatch.",
            )

        source_trade_id = execution.trade_id

        execution = await self.execution_repo.update(
            execution, trade_id=target_trade_id
        )

        await self._re_aggregate_trade(target_trade_id, user_id)

        if source_trade_id and source_trade_id != target_trade_id:
            remaining_executions = await self.execution_repo.list_by_trade_id(
                source_trade_id
            )
            if not remaining_executions:
                source_trade = await self.trade_repo.get_by_id(source_trade_id)
                if source_trade:
                    await self.trade_repo.delete(source_trade)
            else:
                await self._re_aggregate_trade(source_trade_id, user_id)

        await self.session.commit()
        return execution

    async def detach_execution(
        self, execution_id: uuid.UUID, user_id: uuid.UUID
    ) -> "Trade":
        """Detach an execution from its current trade into a new trade.

        Args:
            execution_id: Execution to detach.
            user_id: User ownership check.

        Returns:
            The newly created Trade.

        Raises:
            HTTPException: If execution is not found or is the only execution
                in the trade.
        """
        from app.schemas.trade import TradeCreate

        execution = await self.execution_repo.get_by_id(execution_id)
        if not execution or execution.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found."
            )

        source_trade_id = execution.trade_id
        if not source_trade_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Execution is not attached to a trade.",
            )

        remaining_executions = await self.execution_repo.list_by_trade_id(
            source_trade_id
        )
        if len(remaining_executions) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot detach the only execution in a trade.",
            )

        # Create a new trade for the execution
        new_trade_data = TradeCreate(
            user_id=user_id,
            symbol=execution.symbol,
            direction=execution.direction,
            asset_class=execution.asset_class,
            quantity=execution.quantity,
            entry_price=execution.price,
            opened_at=execution.executed_at,
            commission=execution.commission,
            currency=execution.currency,
            multiplier=execution.multiplier,
            account_id=execution.account_id,
        )

        new_trade = await self.trade_repo.create(new_trade_data)

        execution = await self.execution_repo.update(execution, trade_id=new_trade.id)

        await self._re_aggregate_trade(new_trade.id, user_id)
        await self._re_aggregate_trade(source_trade_id, user_id)

        await self.session.commit()
        return new_trade

    async def _re_aggregate_trade(
        self, trade_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """Re-aggregate a trade's values from its logical executions using VWAP logic.

        Groups executions by direction relative to the trade's direction:
        - Entry executions (same direction): compute VWAP entry_price, total quantity.
        - Exit executions (opposite direction): compute VWAP exit_price.
        - Commission = sum of all execution commissions.
        - PnL = sum of execution pnl values if available, else computed from prices.
        - Net PnL = PnL - Commission.
        - opened_at = min(executed_at) of entry executions.
        - closed_at = max(executed_at) of exit executions (if fully exited).
        - Status set to CLOSED if fully exited.
        - has_conflict cleared when position is consistent.

        Args:
            trade_id: Target trade ID to re-aggregate.
            user_id: For permissions check.
        """
        trade = await self.trade_repo.get_by_id(trade_id)
        if not trade or trade.user_id != user_id:
            return

        executions = await self.execution_repo.list_by_trade_id(trade_id)
        if not executions:
            return

        from decimal import Decimal

        from app.models.trade import Direction

        is_long = trade.direction == Direction.LONG

        entry_qty = Decimal(0)
        entry_cost = Decimal(0)
        exit_qty = Decimal(0)
        exit_cost = Decimal(0)
        total_commission = Decimal(0)
        total_pnl: Decimal | None = Decimal(0)
        has_broker_pnl = False

        entry_times: list[datetime] = []
        exit_times: list[datetime] = []

        for ex in executions:
            total_commission += ex.commission

            is_entry = (is_long and ex.direction == Direction.LONG) or (
                not is_long and ex.direction == Direction.SHORT
            )

            if is_entry:
                entry_qty += ex.quantity
                entry_cost += ex.quantity * ex.price
                entry_times.append(ex.executed_at)
            else:
                exit_qty += ex.quantity
                exit_cost += ex.quantity * ex.price
                exit_times.append(ex.executed_at)

            # Accumulate broker-reported PnL when available
            if ex.pnl is not None:
                has_broker_pnl = True
                if total_pnl is not None:
                    total_pnl += ex.pnl

        # --- Compute derived fields ---
        trade.quantity = entry_qty
        trade.entry_price = entry_cost / entry_qty if entry_qty > 0 else Decimal(0)
        trade.exit_price = exit_cost / exit_qty if exit_qty > 0 else None
        trade.commission = total_commission

        # opened_at = earliest entry execution
        if entry_times:
            trade.opened_at = min(entry_times)

        # closed_at = latest exit execution, only if fully exited
        if exit_qty >= entry_qty and entry_qty > 0 and exit_times:
            trade.closed_at = max(exit_times)
        else:
            trade.closed_at = None

        # PnL: prefer sum of broker-reported pnl, else compute from prices
        if exit_qty > 0 and trade.exit_price is not None:
            if has_broker_pnl and total_pnl is not None:
                trade.pnl = total_pnl
            else:
                multiplier = Decimal(trade.multiplier)
                if is_long:
                    trade.pnl = (
                        (trade.exit_price - trade.entry_price) * exit_qty * multiplier
                    )
                else:
                    trade.pnl = (
                        (trade.entry_price - trade.exit_price) * exit_qty * multiplier
                    )
            trade.net_pnl = trade.pnl - total_commission
        else:
            trade.pnl = None
            trade.net_pnl = None

        # Clear conflict flag when position totals are consistent
        # (exit qty does not exceed entry qty)
        if exit_qty <= entry_qty:
            trade.has_conflict = False

        trade.updated_at = datetime.now(UTC)
        await self.session.flush()

    async def re_aggregate_trade(self, trade_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Public wrapper for _re_aggregate_trade."""
        await self._re_aggregate_trade(trade_id, user_id)
