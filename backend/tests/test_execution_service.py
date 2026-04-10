"""Unit tests for ExecutionService — no database access (all DB calls mocked)."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.models.logical_execution import ExecutionStatus, LogicalExecution
from app.models.trade import AssetClass, Direction, Trade
from app.schemas.execution import LogicalExecutionCreate, LogicalExecutionUpdate
from app.services.execution import ExecutionService


def _make_trade(
    id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    account_id: uuid.UUID | None = None,
    symbol: str = "AAPL",
    direction: Direction = Direction.LONG,
    asset_class: AssetClass = AssetClass.EQUITY,
    quantity: Decimal = Decimal("10"),
    entry_price: Decimal = Decimal("150.00"),
    currency: str | None = None,
    multiplier: int = 1,
) -> Trade:
    """Helper to create a dummy Trade."""
    trade = Trade(
        id=id or uuid.uuid4(),
        user_id=user_id or uuid.uuid4(),
        account_id=account_id or uuid.uuid4(),
        symbol=symbol,
        direction=direction,
        asset_class=asset_class,
        quantity=quantity,
        entry_price=entry_price,
        currency=currency,
        multiplier=multiplier,
    )
    return trade


def _make_execution(
    id: uuid.UUID | None = None,
    trade_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    account_id: uuid.UUID | None = None,
    symbol: str = "AAPL",
    direction: Direction = Direction.LONG,
    quantity: Decimal = Decimal("10"),
    price: Decimal = Decimal("150.00"),
    commission: Decimal = Decimal("0"),
    executed_at: datetime | None = None,
    status: ExecutionStatus = ExecutionStatus.MANUAL,
) -> LogicalExecution:
    """Helper to create a dummy LogicalExecution."""
    ex = LogicalExecution(
        id=id or uuid.uuid4(),
        trade_id=trade_id or uuid.uuid4(),
        user_id=user_id or uuid.uuid4(),
        account_id=account_id or uuid.uuid4(),
        symbol=symbol,
        asset_class=AssetClass.EQUITY,
        direction=direction,
        quantity=quantity,
        price=price,
        commission=commission,
        executed_at=executed_at or datetime.now(UTC),
        status=status,
        multiplier=1,
    )
    return ex


@pytest.fixture()
def service(mock_session: AsyncMock) -> ExecutionService:
    """Return an ExecutionService instance with mocked repository dependencies."""
    svc = ExecutionService(mock_session)
    svc.execution_repo = AsyncMock()
    svc.trade_repo = AsyncMock()
    # Mock the internal re-aggregation method to isolate tests
    svc._re_aggregate_trade = AsyncMock()
    return svc


class TestExecutionService:
    """Test suite for ExecutionService."""

    async def test_create_manual_execution_success(
        self, service: ExecutionService, mock_session: AsyncMock
    ) -> None:
        """create_manual_execution should create an execution and re-aggregate."""
        user_id = uuid.uuid4()
        trade = _make_trade(user_id=user_id)
        service.trade_repo.get_by_id.return_value = trade

        data = LogicalExecutionCreate(
            direction=Direction.LONG,
            quantity=Decimal("5"),
            price=Decimal("152.00"),
            executed_at=datetime.now(UTC),
        )

        ex = _make_execution(user_id=user_id, trade_id=trade.id)
        service.execution_repo.create.return_value = ex

        result = await service.create_manual_execution(trade.id, user_id, data)

        assert result == ex
        service.execution_repo.create.assert_called_once()
        service._re_aggregate_trade.assert_called_once_with(trade.id, user_id)
        mock_session.commit.assert_called_once()

    async def test_create_manual_execution_not_found(
        self, service: ExecutionService
    ) -> None:
        """Should raise 404 if trade does not exist or user mismatch."""
        service.trade_repo.get_by_id.return_value = None
        data = LogicalExecutionCreate(
            direction=Direction.LONG,
            quantity=Decimal("5"),
            price=Decimal("152.00"),
            executed_at=datetime.now(UTC),
        )

        with pytest.raises(HTTPException) as exc:
            await service.create_manual_execution(uuid.uuid4(), uuid.uuid4(), data)
        assert exc.value.status_code == 404

    async def test_update_execution_success(
        self, service: ExecutionService, mock_session: AsyncMock
    ) -> None:
        """update_execution should update and re-aggregate."""
        user_id = uuid.uuid4()
        trade_id = uuid.uuid4()
        ex = _make_execution(user_id=user_id, trade_id=trade_id)
        service.execution_repo.get_by_id.return_value = ex
        service.execution_repo.update.return_value = ex

        data = LogicalExecutionUpdate(price=Decimal("155.00"))
        result = await service.update_execution(ex.id, user_id, data)

        assert result == ex
        service.execution_repo.update.assert_called_once()
        service._re_aggregate_trade.assert_called_once_with(trade_id, user_id)
        mock_session.commit.assert_called_once()

    async def test_delete_execution_reaggregates_parent(
        self, service: ExecutionService, mock_session: AsyncMock
    ) -> None:
        """delete_execution should delete and re-aggregate if siblings remain."""
        user_id = uuid.uuid4()
        trade_id = uuid.uuid4()
        ex = _make_execution(user_id=user_id, trade_id=trade_id)
        service.execution_repo.get_by_id.return_value = ex

        # Return a non-empty list of remaining executions
        service.execution_repo.list_by_trade_id.return_value = [_make_execution()]

        await service.delete_execution(ex.id, user_id)

        service.execution_repo.delete.assert_called_once_with(ex.id)
        service._re_aggregate_trade.assert_called_once_with(trade_id, user_id)
        service.trade_repo.delete.assert_not_called()
        mock_session.commit.assert_called_once()

    async def test_delete_execution_deletes_empty_trade(
        self, service: ExecutionService, mock_session: AsyncMock
    ) -> None:
        """delete_execution should delete the parent trade if it's the last execution."""
        user_id = uuid.uuid4()
        trade_id = uuid.uuid4()
        ex = _make_execution(user_id=user_id, trade_id=trade_id)
        trade = _make_trade(id=trade_id, user_id=user_id)

        service.execution_repo.get_by_id.return_value = ex
        service.trade_repo.get_by_id.return_value = trade
        # Return empty list, meaning no executions left
        service.execution_repo.list_by_trade_id.return_value = []

        await service.delete_execution(ex.id, user_id)

        service.execution_repo.delete.assert_called_once_with(ex.id)
        service.trade_repo.delete.assert_called_once_with(trade)
        service._re_aggregate_trade.assert_not_called()
        mock_session.commit.assert_called_once()

    async def test_reassign_execution_success(
        self, service: ExecutionService, mock_session: AsyncMock
    ) -> None:
        """reassign_execution should update trade_id and re-aggregate both trades."""
        user_id = uuid.uuid4()
        account_id = uuid.uuid4()
        source_trade_id = uuid.uuid4()
        target_trade_id = uuid.uuid4()

        ex = _make_execution(
            user_id=user_id,
            trade_id=source_trade_id,
            account_id=account_id,
            symbol="AAPL",
        )
        target_trade = _make_trade(
            id=target_trade_id, user_id=user_id, account_id=account_id, symbol="AAPL"
        )

        service.execution_repo.get_by_id.return_value = ex
        service.trade_repo.get_by_id.return_value = target_trade
        service.execution_repo.list_by_trade_id.return_value = [_make_execution()]

        # Setup update mock to return execution with new trade_id
        updated_ex = _make_execution(
            id=ex.id, trade_id=target_trade_id, user_id=user_id
        )
        service.execution_repo.update.return_value = updated_ex

        result = await service.reassign_execution(ex.id, target_trade_id, user_id)

        assert result.trade_id == target_trade_id
        service.execution_repo.update.assert_called_once()
        service._re_aggregate_trade.assert_any_call(target_trade_id, user_id)
        service._re_aggregate_trade.assert_any_call(source_trade_id, user_id)
        mock_session.commit.assert_called_once()

    async def test_reassign_execution_mismatch(self, service: ExecutionService) -> None:
        """reassign_execution should raise 400 if symbol or account differs."""
        user_id = uuid.uuid4()
        ex = _make_execution(user_id=user_id, symbol="AAPL")
        target_trade = _make_trade(user_id=user_id, symbol="TSLA")  # Different symbol

        service.execution_repo.get_by_id.return_value = ex
        service.trade_repo.get_by_id.return_value = target_trade

        with pytest.raises(HTTPException) as exc:
            await service.reassign_execution(ex.id, target_trade.id, user_id)
        assert exc.value.status_code == 400

    async def test_detach_execution_success(
        self, service: ExecutionService, mock_session: AsyncMock
    ) -> None:
        """detach_execution should create a new trade and reassign the execution."""
        user_id = uuid.uuid4()
        source_trade_id = uuid.uuid4()
        ex = _make_execution(user_id=user_id, trade_id=source_trade_id)

        new_trade_id = uuid.uuid4()
        new_trade = _make_trade(id=new_trade_id, user_id=user_id)

        service.execution_repo.get_by_id.return_value = ex
        # Mock > 1 remaining executions
        service.execution_repo.list_by_trade_id.return_value = [ex, _make_execution()]
        service.trade_repo.create.return_value = new_trade

        result = await service.detach_execution(ex.id, user_id)

        assert result == new_trade
        service.trade_repo.create.assert_called_once()
        service.execution_repo.update.assert_called_once()
        service._re_aggregate_trade.assert_any_call(new_trade_id, user_id)
        service._re_aggregate_trade.assert_any_call(source_trade_id, user_id)
        mock_session.commit.assert_called_once()

    async def test_detach_execution_last_one(self, service: ExecutionService) -> None:
        """detach_execution should raise 400 if it's the only execution in the trade."""
        user_id = uuid.uuid4()
        ex = _make_execution(user_id=user_id)

        service.execution_repo.get_by_id.return_value = ex
        # Mock exactly 1 execution
        service.execution_repo.list_by_trade_id.return_value = [ex]

        with pytest.raises(HTTPException) as exc:
            await service.detach_execution(ex.id, user_id)
        assert exc.value.status_code == 400
