"""Unit tests for ExecutionService — no database access (all DB calls mocked)."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import (
    ExecutionNotFoundError,
    ExecutionValidationError,
    TradeNotFoundError,
)
from app.models.logical_execution import (
    EXECUTION_ORIGIN_IMPORTED,
    EXECUTION_ORIGIN_MANUAL,
    EXECUTION_ORIGIN_MERGED,
    LogicalExecution,
)
from app.models.trade import AssetClass, Direction, Trade
from app.schemas.execution import (
    LogicalExecutionCreate,
    LogicalExecutionUpdate,
    MergeExecutionsRequest,
)
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
    origin: str = EXECUTION_ORIGIN_MANUAL,
    deleted: bool = False,
    user_modified: bool = False,
) -> LogicalExecution:
    """Helper to create a dummy LogicalExecution."""
    now = datetime.now(UTC)
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
        executed_at=executed_at or now,
        origin=origin,
        deleted=deleted,
        user_modified=user_modified,
        multiplier=1,
        created_at=now,
        updated_at=now,
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

        with pytest.raises(TradeNotFoundError):
            await service.create_manual_execution(uuid.uuid4(), uuid.uuid4(), data)

    async def test_update_execution_success(
        self, service: ExecutionService, mock_session: AsyncMock
    ) -> None:
        """update_execution should update and re-aggregate."""
        user_id = uuid.uuid4()
        trade_id = uuid.uuid4()
        ex = _make_execution(
            user_id=user_id, trade_id=trade_id, origin=EXECUTION_ORIGIN_MANUAL
        )
        service.execution_repo.get_by_id.return_value = ex
        service.execution_repo.update.return_value = ex

        data = LogicalExecutionUpdate(price=Decimal("155.00"))
        result = await service.update_execution(ex.id, user_id, data)

        assert result == ex
        service.execution_repo.update.assert_called_once()
        service._re_aggregate_trade.assert_called_once_with(trade_id, user_id)
        mock_session.commit.assert_called_once()

    async def test_update_imported_execution_sets_user_modified(
        self, service: ExecutionService, mock_session: AsyncMock
    ) -> None:
        """Patching an imported execution should set user_modified=True."""
        user_id = uuid.uuid4()
        trade_id = uuid.uuid4()
        ex = _make_execution(
            user_id=user_id, trade_id=trade_id, origin=EXECUTION_ORIGIN_IMPORTED
        )
        service.execution_repo.get_by_id.return_value = ex
        service.execution_repo.update.return_value = ex

        data = LogicalExecutionUpdate(price=Decimal("155.00"))
        await service.update_execution(ex.id, user_id, data)

        call_kwargs = service.execution_repo.update.call_args[1]
        assert call_kwargs.get("user_modified") is True

    async def test_update_manual_execution_no_user_modified(
        self, service: ExecutionService, mock_session: AsyncMock
    ) -> None:
        """Patching a manual execution should NOT set user_modified=True."""
        user_id = uuid.uuid4()
        trade_id = uuid.uuid4()
        ex = _make_execution(
            user_id=user_id, trade_id=trade_id, origin=EXECUTION_ORIGIN_MANUAL
        )
        service.execution_repo.get_by_id.return_value = ex
        service.execution_repo.update.return_value = ex

        data = LogicalExecutionUpdate(price=Decimal("155.00"))
        await service.update_execution(ex.id, user_id, data)

        call_kwargs = service.execution_repo.update.call_args[1]
        assert "user_modified" not in call_kwargs

    async def test_delete_manual_execution_hard_delete(
        self, service: ExecutionService, mock_session: AsyncMock
    ) -> None:
        """Deleting a manual execution should hard-delete (return None, 204)."""
        user_id = uuid.uuid4()
        trade_id = uuid.uuid4()
        ex = _make_execution(
            user_id=user_id, trade_id=trade_id, origin=EXECUTION_ORIGIN_MANUAL
        )
        service.execution_repo.get_by_id.return_value = ex

        result = await service.delete_execution(ex.id, user_id)

        assert result is None  # hard-delete → 204
        service.execution_repo.delete.assert_called_once_with(ex.id)
        service.execution_repo.soft_delete.assert_not_called()
        service._re_aggregate_trade.assert_called_once_with(trade_id, user_id)
        mock_session.commit.assert_called_once()

    async def test_delete_imported_execution_soft_delete(
        self, service: ExecutionService, mock_session: AsyncMock
    ) -> None:
        """Deleting an imported execution should soft-delete (return execution, 200)."""
        user_id = uuid.uuid4()
        trade_id = uuid.uuid4()
        ex = _make_execution(
            user_id=user_id, trade_id=trade_id, origin=EXECUTION_ORIGIN_IMPORTED
        )
        soft_deleted_ex = _make_execution(
            id=ex.id, user_id=user_id, trade_id=trade_id,
            origin=EXECUTION_ORIGIN_IMPORTED, deleted=True
        )
        service.execution_repo.get_by_id.side_effect = [ex, soft_deleted_ex]

        result = await service.delete_execution(ex.id, user_id)

        assert result is not None  # soft-delete → 200
        assert result.deleted is True
        service.execution_repo.soft_delete.assert_called_once_with(ex.id)
        service.execution_repo.delete.assert_not_called()
        service._re_aggregate_trade.assert_called_once_with(trade_id, user_id)
        mock_session.commit.assert_called_once()

    async def test_delete_already_deleted_execution_raises_409(
        self, service: ExecutionService
    ) -> None:
        """Delete on already-deleted execution should raise ExecutionValidationError."""
        user_id = uuid.uuid4()
        ex = _make_execution(
            user_id=user_id, origin=EXECUTION_ORIGIN_IMPORTED, deleted=True
        )
        service.execution_repo.get_by_id.return_value = ex

        with pytest.raises(ExecutionValidationError, match="already deleted"):
            await service.delete_execution(ex.id, user_id)

    async def test_restore_deleted_execution(
        self, service: ExecutionService, mock_session: AsyncMock
    ) -> None:
        """restore_execution should set deleted=False and re-aggregate."""
        user_id = uuid.uuid4()
        trade_id = uuid.uuid4()
        ex = _make_execution(
            user_id=user_id, trade_id=trade_id,
            origin=EXECUTION_ORIGIN_IMPORTED, deleted=True
        )
        restored_ex = _make_execution(
            id=ex.id, user_id=user_id, trade_id=trade_id,
            origin=EXECUTION_ORIGIN_IMPORTED, deleted=False
        )
        service.execution_repo.get_by_id.side_effect = [ex, restored_ex]

        result = await service.restore_execution(ex.id, user_id)

        assert result.deleted is False
        service.execution_repo.restore.assert_called_once_with(ex.id)
        service._re_aggregate_trade.assert_called_once_with(trade_id, user_id)
        mock_session.commit.assert_called_once()

    async def test_restore_non_deleted_execution_raises_400(
        self, service: ExecutionService
    ) -> None:
        """restore_execution on non-deleted execution should raise 400."""
        user_id = uuid.uuid4()
        ex = _make_execution(
            user_id=user_id, origin=EXECUTION_ORIGIN_IMPORTED, deleted=False
        )
        service.execution_repo.get_by_id.return_value = ex

        with pytest.raises(ExecutionValidationError, match="not deleted"):
            await service.restore_execution(ex.id, user_id)

    async def test_delete_execution_reaggregates_parent(
        self, service: ExecutionService, mock_session: AsyncMock
    ) -> None:
        """delete_execution should re-aggregate parent trade after deletion."""
        user_id = uuid.uuid4()
        trade_id = uuid.uuid4()
        ex = _make_execution(
            user_id=user_id, trade_id=trade_id, origin=EXECUTION_ORIGIN_MANUAL
        )
        service.execution_repo.get_by_id.return_value = ex

        await service.delete_execution(ex.id, user_id)

        service._re_aggregate_trade.assert_called_once_with(trade_id, user_id)
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

        with pytest.raises(ExecutionValidationError):
            await service.reassign_execution(ex.id, target_trade.id, user_id)

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
        # Mock get_by_id to return the new_trade when reloaded at line 270
        service.trade_repo.get_by_id.return_value = new_trade

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

        with pytest.raises(ExecutionValidationError):
            await service.detach_execution(ex.id, user_id)

    async def test_delete_execution_not_found(
        self, service: ExecutionService
    ) -> None:
        """delete_execution should raise ExecutionNotFoundError if not found."""
        service.execution_repo.get_by_id.return_value = None

        with pytest.raises(ExecutionNotFoundError):
            await service.delete_execution(uuid.uuid4(), uuid.uuid4())

    async def test_merge_executions_success(
        self, service: ExecutionService, mock_session: AsyncMock
    ) -> None:
        """merge_executions should soft-delete sources and create merged execution."""
        user_id = uuid.uuid4()
        trade_id = uuid.uuid4()
        ex_a = _make_execution(
            user_id=user_id,
            trade_id=trade_id,
            quantity=Decimal("5"),
            price=Decimal("100"),
            origin=EXECUTION_ORIGIN_IMPORTED,
        )
        ex_b = _make_execution(
            user_id=user_id,
            trade_id=trade_id,
            quantity=Decimal("5"),
            price=Decimal("110"),
            origin=EXECUTION_ORIGIN_IMPORTED,
        )
        merged_ex = _make_execution(
            user_id=user_id,
            trade_id=trade_id,
            quantity=Decimal("10"),
            price=Decimal("105"),
            origin=EXECUTION_ORIGIN_MERGED,
        )

        # get_by_id is called: ex_a, ex_b, then reloads for ex_a, ex_b
        service.execution_repo.get_by_id.side_effect = [
            ex_a, ex_b, ex_a, ex_b
        ]
        service.execution_repo.create.return_value = merged_ex

        data = MergeExecutionsRequest(
            execution_ids=[ex_a.id, ex_b.id],
            primary_id=ex_a.id,
        )
        result = await service.merge_executions(user_id=user_id, data=data)

        assert result.merged.origin == EXECUTION_ORIGIN_MERGED
        assert len(result.sources) == 2
        assert service.execution_repo.soft_delete.call_count == 2
        service._re_aggregate_trade.assert_called_once_with(trade_id, user_id)
        mock_session.commit.assert_called_once()

    async def test_merge_executions_primary_not_in_ids(
        self, service: ExecutionService
    ) -> None:
        """merge_executions should raise 400 if primary_id not in execution_ids."""
        user_id = uuid.uuid4()
        data = MergeExecutionsRequest(
            execution_ids=[uuid.uuid4(), uuid.uuid4()],
            primary_id=uuid.uuid4(),  # not in list
        )
        with pytest.raises(ExecutionValidationError, match="primary_id"):
            await service.merge_executions(user_id=user_id, data=data)

    async def test_merge_executions_deleted_source_raises(
        self, service: ExecutionService
    ) -> None:
        """merge_executions should raise 400 if any source is already deleted."""
        user_id = uuid.uuid4()
        trade_id = uuid.uuid4()
        ex_deleted = _make_execution(
            user_id=user_id, trade_id=trade_id, deleted=True,
            origin=EXECUTION_ORIGIN_IMPORTED,
        )
        ex_b = _make_execution(
            user_id=user_id, trade_id=trade_id, origin=EXECUTION_ORIGIN_IMPORTED
        )
        service.execution_repo.get_by_id.side_effect = [ex_deleted, ex_b]

        data = MergeExecutionsRequest(
            execution_ids=[ex_deleted.id, ex_b.id],
            primary_id=ex_deleted.id,
        )
        with pytest.raises(ExecutionValidationError, match="already deleted"):
            await service.merge_executions(user_id=user_id, data=data)
