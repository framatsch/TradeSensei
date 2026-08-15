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

"""Unit tests for ExecutionService — no database access (all DB calls mocked)."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

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
from app.schemas.trade import TradeCreate
from app.services.execution import ExecutionService
from app.utils.parsers.aggregator import aggregate_executions_fifo


def _make_trade(
    id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    account_id: uuid.UUID | None = None,
    symbol: str = "AAPL",
    direction: Direction = Direction.LONG,
    asset_class: AssetClass = AssetClass.EQUITY,
    quantity: Decimal = Decimal("10"),
    entry_price: Decimal = Decimal("150.00"),
    opened_at: datetime | None = None,
    closed_at: datetime | None = None,
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
        opened_at=opened_at or datetime.now(UTC),
        closed_at=closed_at,
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
    currency: str | None = None,
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
        currency=currency,
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
    svc.corporate_action_service = AsyncMock()
    # list_for_trade now scopes corporate actions per execution leg via
    # list_for_execution(symbol=, conid=) rather than list_for_aggregator.
    svc.corporate_action_service.list_for_execution = AsyncMock(return_value=[])
    svc.raw_transaction_repo = AsyncMock()
    svc._audit = MagicMock()
    # Mock the internal re-aggregation method to isolate tests
    svc._re_aggregate_trade = AsyncMock()
    return svc


def _make_corporate_action(
    *,
    symbol: str = "AAPL",
    ratio: Decimal = Decimal("10"),
    date_value: datetime | None = None,
    old_conid: str | None = None,
    new_conid: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        symbol=symbol,
        ratio=ratio,
        date=(date_value or datetime(2024, 1, 10, tzinfo=UTC)).date(),
        old_conid=old_conid,
        new_conid=new_conid,
    )


class TestExecutionService:
    """Test suite for ExecutionService."""

    async def test_create_manual_execution_success(self, service: ExecutionService, mock_session: AsyncMock) -> None:
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

    async def test_create_manual_execution_not_found(self, service: ExecutionService) -> None:
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

    async def test_create_manual_execution_combo_uses_leg_overrides(self, service: ExecutionService, mock_session: AsyncMock) -> None:
        """COMBO leg creation should use per-leg asset_class/multiplier overrides."""
        user_id = uuid.uuid4()
        trade = _make_trade(
            user_id=user_id,
            asset_class=AssetClass.EQUITY,
            multiplier=1,
        )
        trade.is_combo = True
        service.trade_repo.get_by_id.return_value = trade

        data = LogicalExecutionCreate(
            direction=Direction.LONG,
            quantity=Decimal("1"),
            price=Decimal("5.00"),
            executed_at=datetime.now(UTC),
            asset_class=AssetClass.OPTION,
            multiplier=100,
        )

        created = _make_execution(user_id=user_id, trade_id=trade.id)
        service.execution_repo.create.return_value = created

        result = await service.create_manual_execution(trade.id, user_id, data)

        assert result == created
        create_kwargs = service.execution_repo.create.call_args.kwargs
        assert create_kwargs["asset_class"] == AssetClass.OPTION
        assert create_kwargs["multiplier"] == 100
        service._re_aggregate_trade.assert_called_once_with(trade.id, user_id)
        mock_session.commit.assert_called_once()

    async def test_update_execution_success(self, service: ExecutionService, mock_session: AsyncMock) -> None:
        """update_execution should update and re-aggregate."""
        user_id = uuid.uuid4()
        trade_id = uuid.uuid4()
        ex = _make_execution(user_id=user_id, trade_id=trade_id, origin=EXECUTION_ORIGIN_MANUAL)
        service.execution_repo.get_by_id.return_value = ex
        service.execution_repo.update.return_value = ex

        data = LogicalExecutionUpdate(price=Decimal("155.00"))
        result = await service.update_execution(ex.id, user_id, data)

        assert result == ex
        service.execution_repo.update.assert_called_once()
        service._re_aggregate_trade.assert_called_once_with(trade_id, user_id)
        mock_session.commit.assert_called_once()

    async def test_update_imported_execution_sets_user_modified(self, service: ExecutionService, mock_session: AsyncMock) -> None:
        """Patching an imported execution should set user_modified=True."""
        user_id = uuid.uuid4()
        trade_id = uuid.uuid4()
        ex = _make_execution(user_id=user_id, trade_id=trade_id, origin=EXECUTION_ORIGIN_IMPORTED)
        service.execution_repo.get_by_id.return_value = ex
        service.execution_repo.update.return_value = ex

        data = LogicalExecutionUpdate(price=Decimal("155.00"))
        await service.update_execution(ex.id, user_id, data)

        call_kwargs = service.execution_repo.update.call_args[1]
        assert call_kwargs.get("user_modified") is True

    async def test_update_manual_execution_no_user_modified(self, service: ExecutionService, mock_session: AsyncMock) -> None:
        """Patching a manual execution should NOT set user_modified=True."""
        user_id = uuid.uuid4()
        trade_id = uuid.uuid4()
        ex = _make_execution(user_id=user_id, trade_id=trade_id, origin=EXECUTION_ORIGIN_MANUAL)
        service.execution_repo.get_by_id.return_value = ex
        service.execution_repo.update.return_value = ex

        data = LogicalExecutionUpdate(price=Decimal("155.00"))
        await service.update_execution(ex.id, user_id, data)

        call_kwargs = service.execution_repo.update.call_args[1]
        assert "user_modified" not in call_kwargs

    async def test_update_execution_symbol_change_reaggregates_old_symbol_chain(self, service: ExecutionService, mock_session: AsyncMock) -> None:
        user_id = uuid.uuid4()
        account_id = uuid.uuid4()
        source_trade_id = uuid.uuid4()
        old_symbol_trade_id = uuid.uuid4()
        ex = _make_execution(
            user_id=user_id,
            account_id=account_id,
            trade_id=source_trade_id,
            symbol="AAA",
            origin=EXECUTION_ORIGIN_IMPORTED,
        )
        moved_ex = _make_execution(
            id=ex.id,
            user_id=user_id,
            account_id=account_id,
            trade_id=source_trade_id,
            symbol="BBB",
            origin=EXECUTION_ORIGIN_IMPORTED,
        )

        service.execution_repo.get_by_id.return_value = ex
        service.execution_repo.update.return_value = moved_ex
        service.trade_repo.list_by_user_account.return_value = [
            _make_trade(id=source_trade_id, user_id=user_id, account_id=account_id, symbol="BBB"),
            _make_trade(id=old_symbol_trade_id, user_id=user_id, account_id=account_id, symbol="AAA"),
        ]

        data = LogicalExecutionUpdate(symbol="BBB")
        await service.update_execution(ex.id, user_id, data)

        assert service._re_aggregate_trade.await_count == 2
        service._re_aggregate_trade.assert_any_await(source_trade_id, user_id)
        service._re_aggregate_trade.assert_any_await(old_symbol_trade_id, user_id)

    async def test_delete_manual_execution_hard_delete(self, service: ExecutionService, mock_session: AsyncMock) -> None:
        """Deleting a manual execution should hard-delete (return None, 204)."""
        user_id = uuid.uuid4()
        trade_id = uuid.uuid4()
        ex = _make_execution(user_id=user_id, trade_id=trade_id, origin=EXECUTION_ORIGIN_MANUAL)
        service.execution_repo.get_by_id.return_value = ex

        result = await service.delete_execution(ex.id, user_id)

        assert result is None  # hard-delete → 204
        service.execution_repo.delete.assert_called_once_with(ex.id)
        service.execution_repo.soft_delete.assert_not_called()
        service._re_aggregate_trade.assert_called_once_with(trade_id, user_id)
        # Regression test for round-1 Should Fix #8: exactly one audit event
        # must fire for the manual hard-delete branch.
        service._audit.create_audit_event.assert_called_once()
        assert service._audit.create_audit_event.call_args.kwargs["action"] == "execution.deleted"
        mock_session.commit.assert_called_once()

    async def test_delete_imported_execution_soft_delete(self, service: ExecutionService, mock_session: AsyncMock) -> None:
        """Deleting an imported execution should soft-delete (return execution, 200)."""
        user_id = uuid.uuid4()
        trade_id = uuid.uuid4()
        ex = _make_execution(user_id=user_id, trade_id=trade_id, origin=EXECUTION_ORIGIN_IMPORTED)
        soft_deleted_ex = _make_execution(id=ex.id, user_id=user_id, trade_id=trade_id, origin=EXECUTION_ORIGIN_IMPORTED, deleted=True)
        service.execution_repo.get_by_id.side_effect = [ex, soft_deleted_ex]

        result = await service.delete_execution(ex.id, user_id)

        assert result is not None  # soft-delete → 200
        assert result.deleted is True
        service.execution_repo.soft_delete.assert_called_once_with(ex.id)
        service.execution_repo.delete.assert_not_called()
        service._re_aggregate_trade.assert_called_once_with(trade_id, user_id)
        # Regression test for round-1 Should Fix #8: exactly one audit event
        # must fire for the soft-delete branch.
        service._audit.create_audit_event.assert_called_once()
        assert service._audit.create_audit_event.call_args.kwargs["action"] == "execution.deleted"
        mock_session.commit.assert_called_once()

    async def test_delete_already_deleted_execution_raises_409(self, service: ExecutionService) -> None:
        """Delete on already-deleted execution should raise ExecutionValidationError."""
        user_id = uuid.uuid4()
        ex = _make_execution(user_id=user_id, origin=EXECUTION_ORIGIN_IMPORTED, deleted=True)
        service.execution_repo.get_by_id.return_value = ex

        with pytest.raises(ExecutionValidationError, match="already deleted"):
            await service.delete_execution(ex.id, user_id)

    async def test_restore_deleted_execution(self, service: ExecutionService, mock_session: AsyncMock) -> None:
        """restore_execution should set deleted=False and re-aggregate."""
        user_id = uuid.uuid4()
        trade_id = uuid.uuid4()
        ex = _make_execution(user_id=user_id, trade_id=trade_id, origin=EXECUTION_ORIGIN_IMPORTED, deleted=True)
        restored_ex = _make_execution(id=ex.id, user_id=user_id, trade_id=trade_id, origin=EXECUTION_ORIGIN_IMPORTED, deleted=False)
        service.execution_repo.get_by_id.side_effect = [ex, restored_ex]

        result = await service.restore_execution(ex.id, user_id)

        assert result.deleted is False
        service.execution_repo.restore.assert_called_once_with(ex.id)
        service._re_aggregate_trade.assert_called_once_with(trade_id, user_id)
        mock_session.commit.assert_called_once()

    async def test_restore_non_deleted_execution_raises_400(self, service: ExecutionService) -> None:
        """restore_execution on non-deleted execution should raise 400."""
        user_id = uuid.uuid4()
        ex = _make_execution(user_id=user_id, origin=EXECUTION_ORIGIN_IMPORTED, deleted=False)
        service.execution_repo.get_by_id.return_value = ex

        with pytest.raises(ExecutionValidationError, match="not deleted"):
            await service.restore_execution(ex.id, user_id)

    async def test_delete_imported_execution_reset_true_hard_deletes_and_audits_once(self, service: ExecutionService, mock_session: AsyncMock) -> None:
        """An imported execution with reset=True hard-deletes and audits once.

        Deletes the execution, releases the linked BrokerRawTransaction guard,
        and fires exactly one ``execution.reset`` audit event. Regression test
        for round-1 Should Fix #8 (audit-event deduplication) on the reset
        branch.
        """
        user_id = uuid.uuid4()
        trade_id = uuid.uuid4()
        source_id = uuid.uuid4()
        ex = _make_execution(
            user_id=user_id,
            trade_id=trade_id,
            origin=EXECUTION_ORIGIN_IMPORTED,
        )
        ex.source_id = source_id
        service.execution_repo.get_by_id.return_value = ex
        service.execution_repo.list_by_trade_id.return_value = [_make_execution(trade_id=trade_id)]

        result = await service.delete_execution(ex.id, user_id, reset=True)

        assert result is None  # hard-delete → 204
        service.execution_repo.delete.assert_called_once_with(ex.id)
        service.execution_repo.soft_delete.assert_not_called()
        service.raw_transaction_repo.set_suppressed.assert_called_once_with(source_id, False, user_id=user_id)
        service._re_aggregate_trade.assert_called_once_with(trade_id, user_id)
        service._audit.create_audit_event.assert_called_once()
        assert service._audit.create_audit_event.call_args.kwargs["action"] == "execution.reset"
        mock_session.commit.assert_called_once()

    async def test_delete_execution_reaggregates_parent(self, service: ExecutionService, mock_session: AsyncMock) -> None:
        """delete_execution should re-aggregate parent trade after deletion."""
        user_id = uuid.uuid4()
        trade_id = uuid.uuid4()
        ex = _make_execution(user_id=user_id, trade_id=trade_id, origin=EXECUTION_ORIGIN_MANUAL)
        service.execution_repo.get_by_id.return_value = ex

        await service.delete_execution(ex.id, user_id)

        service._re_aggregate_trade.assert_called_once_with(trade_id, user_id)
        mock_session.commit.assert_called_once()

    async def test_reassign_execution_success(self, service: ExecutionService, mock_session: AsyncMock) -> None:
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
        target_trade = _make_trade(id=target_trade_id, user_id=user_id, account_id=account_id, symbol="AAPL")

        service.execution_repo.get_by_id.return_value = ex
        service.trade_repo.get_by_id.return_value = target_trade
        service.execution_repo.list_by_trade_id.return_value = [_make_execution()]

        # Setup update mock to return execution with new trade_id
        updated_ex = _make_execution(id=ex.id, trade_id=target_trade_id, user_id=user_id)
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

    async def test_detach_execution_success(self, service: ExecutionService, mock_session: AsyncMock) -> None:
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

    async def test_delete_execution_not_found(self, service: ExecutionService) -> None:
        """delete_execution should raise ExecutionNotFoundError if not found."""
        service.execution_repo.get_by_id.return_value = None

        with pytest.raises(ExecutionNotFoundError):
            await service.delete_execution(uuid.uuid4(), uuid.uuid4())

    async def test_merge_executions_success(self, service: ExecutionService, mock_session: AsyncMock) -> None:
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
        service.execution_repo.get_by_id.side_effect = [ex_a, ex_b, ex_a, ex_b]
        service.execution_repo.create.return_value = merged_ex
        service.trade_repo.mark_manually_edited = AsyncMock(return_value=None)

        data = MergeExecutionsRequest(
            execution_ids=[ex_a.id, ex_b.id],
            primary_id=ex_a.id,
        )
        result = await service.merge_executions(user_id=user_id, data=data)

        assert result.merged.origin == EXECUTION_ORIGIN_MERGED
        assert len(result.sources) == 2
        assert service.execution_repo.soft_delete.call_count == 2
        assert service.execution_repo.create.call_args.kwargs["user_modified"] is True
        service.trade_repo.mark_manually_edited.assert_awaited_once_with(trade_id, user_id)
        service._re_aggregate_trade.assert_called_once_with(trade_id, user_id)
        mock_session.commit.assert_called_once()

    async def test_reaggregate_trade_clears_has_unlinked_executions(self, service: ExecutionService) -> None:
        user_id = uuid.uuid4()
        trade = _make_trade(user_id=user_id)
        trade.has_unlinked_executions = True
        execution = _make_execution(
            user_id=user_id,
            trade_id=trade.id,
            symbol=trade.symbol,
            direction=trade.direction,
            quantity=Decimal("5"),
            price=Decimal("100"),
            origin=EXECUTION_ORIGIN_IMPORTED,
        )

        service.trade_repo.get_by_id.return_value = trade
        service.execution_repo.list_by_trade_id.return_value = [execution]
        service.execution_repo.has_unlinked_for_trade_contracts = AsyncMock(return_value=False)

        service._re_aggregate_trade = ExecutionService._re_aggregate_trade.__get__(service, ExecutionService)
        await service._re_aggregate_trade(trade.id, user_id, corporate_actions=[])

        assert trade.has_unlinked_executions is False

    async def test_merge_executions_primary_not_in_ids(self, service: ExecutionService) -> None:
        """merge_executions should raise 400 if primary_id not in execution_ids."""
        user_id = uuid.uuid4()
        data = MergeExecutionsRequest(
            execution_ids=[uuid.uuid4(), uuid.uuid4()],
            primary_id=uuid.uuid4(),  # not in list
        )
        with pytest.raises(ExecutionValidationError, match="primary_id"):
            await service.merge_executions(user_id=user_id, data=data)

    async def test_merge_executions_deleted_source_raises(self, service: ExecutionService) -> None:
        """merge_executions should raise 400 if any source is already deleted."""
        user_id = uuid.uuid4()
        trade_id = uuid.uuid4()
        ex_deleted = _make_execution(
            user_id=user_id,
            trade_id=trade_id,
            deleted=True,
            origin=EXECUTION_ORIGIN_IMPORTED,
        )
        ex_b = _make_execution(user_id=user_id, trade_id=trade_id, origin=EXECUTION_ORIGIN_IMPORTED)
        service.execution_repo.get_by_id.side_effect = [ex_deleted, ex_b]

        data = MergeExecutionsRequest(
            execution_ids=[ex_deleted.id, ex_b.id],
            primary_id=ex_deleted.id,
        )
        with pytest.raises(ExecutionValidationError, match="already deleted"):
            await service.merge_executions(user_id=user_id, data=data)

    async def test_list_for_trade_applies_split_adjustment_and_keeps_raw_values(self, service: ExecutionService) -> None:
        user_id = uuid.uuid4()
        trade = _make_trade(user_id=user_id, symbol="AAPL")
        execution = _make_execution(
            user_id=user_id,
            trade_id=trade.id,
            symbol="AAPL",
            quantity=Decimal("1"),
            price=Decimal("500"),
            executed_at=datetime(2024, 1, 1, tzinfo=UTC),
            origin=EXECUTION_ORIGIN_IMPORTED,
        )
        service.trade_repo.get_by_id.return_value = trade
        service.execution_repo.list_by_trade_id.return_value = [execution]
        service.corporate_action_service.list_for_execution.return_value = [
            _make_corporate_action(ratio=Decimal("10"), date_value=datetime(2024, 1, 10, tzinfo=UTC))
        ]

        result = await service.list_for_trade(trade.id, user_id)

        assert len(result) == 1
        item = result[0]
        assert item.raw_price == Decimal("500")
        assert item.raw_quantity == Decimal("1")
        assert item.price == Decimal("50")
        assert item.quantity == Decimal("10")

    async def test_list_for_trade_compounds_splits_and_handles_no_corporate_actions(self, service: ExecutionService) -> None:
        user_id = uuid.uuid4()
        trade = _make_trade(user_id=user_id, symbol="AAPL")
        split_execution = _make_execution(
            user_id=user_id,
            trade_id=trade.id,
            symbol="AAPL",
            quantity=Decimal("2"),
            price=Decimal("500"),
            executed_at=datetime(2024, 1, 1, tzinfo=UTC),
            origin=EXECUTION_ORIGIN_IMPORTED,
        )
        no_split_execution = _make_execution(
            user_id=user_id,
            trade_id=trade.id,
            symbol="AAPL",
            quantity=Decimal("3"),
            price=Decimal("150"),
            executed_at=datetime(2025, 1, 1, tzinfo=UTC),
            origin=EXECUTION_ORIGIN_IMPORTED,
        )
        service.trade_repo.get_by_id.return_value = trade
        service.execution_repo.list_by_trade_id.return_value = [
            split_execution,
            no_split_execution,
        ]
        service.corporate_action_service.list_for_execution.return_value = [
            _make_corporate_action(ratio=Decimal("2"), date_value=datetime(2024, 1, 10, tzinfo=UTC)),
            _make_corporate_action(ratio=Decimal("5"), date_value=datetime(2024, 2, 10, tzinfo=UTC)),
        ]

        result = await service.list_for_trade(trade.id, user_id)

        assert result[0].price == Decimal("50")
        assert result[0].quantity == Decimal("20")
        assert result[1].price == Decimal("150")
        assert result[1].quantity == Decimal("3")
        assert result[1].price == result[1].raw_price
        assert result[1].quantity == result[1].raw_quantity

    async def test_reaggregate_trade_holding_period_does_not_adjust_pre_split_closed_trade(
        self,
        service: ExecutionService,
    ) -> None:
        user_id = uuid.uuid4()
        trade = _make_trade(
            user_id=user_id,
            symbol="OTLK",
            direction=Direction.LONG,
            opened_at=datetime(2023, 5, 22, 14, 0, tzinfo=UTC),
            closed_at=datetime(2023, 5, 24, 14, 0, tzinfo=UTC),
        )
        ex_open = _make_execution(
            user_id=user_id,
            trade_id=trade.id,
            symbol="OTLK",
            direction=Direction.LONG,
            quantity=Decimal("69"),
            price=Decimal("1.44"),
            executed_at=datetime(2023, 5, 22, 14, 0, tzinfo=UTC),
            origin=EXECUTION_ORIGIN_IMPORTED,
        )
        ex_close = _make_execution(
            user_id=user_id,
            trade_id=trade.id,
            symbol="OTLK",
            direction=Direction.SHORT,
            quantity=Decimal("69"),
            price=Decimal("1.50"),
            executed_at=datetime(2023, 5, 24, 14, 0, tzinfo=UTC),
            origin=EXECUTION_ORIGIN_IMPORTED,
        )

        service.trade_repo.get_by_id.return_value = trade
        service.execution_repo.list_by_trade_id.return_value = [ex_open, ex_close]

        service._re_aggregate_trade = ExecutionService._re_aggregate_trade.__get__(service, ExecutionService)
        split = _make_corporate_action(symbol="ATOS", ratio=Decimal("0.05"), date_value=datetime(2024, 3, 13, 0, 0, tzinfo=UTC))
        ex_close.currency = "USD"
        await service._re_aggregate_trade(trade.id, user_id, corporate_actions=[split])

        assert trade.quantity == Decimal("69")
        assert trade.entry_price == Decimal("1.44")

    async def test_reaggregate_trade_effective_date_execution_is_post_split(
        self,
        service: ExecutionService,
    ) -> None:
        user_id = uuid.uuid4()
        trade = _make_trade(
            user_id=user_id,
            symbol="ATOS",
            direction=Direction.LONG,
            opened_at=datetime(2024, 3, 1, 14, 0, tzinfo=UTC),
            closed_at=datetime(2024, 3, 13, 15, 0, tzinfo=UTC),
        )
        ex_open = _make_execution(
            user_id=user_id,
            trade_id=trade.id,
            symbol="ATOS",
            direction=Direction.LONG,
            quantity=Decimal("100"),
            price=Decimal("2"),
            executed_at=datetime(2024, 3, 1, 14, 0, tzinfo=UTC),
            origin=EXECUTION_ORIGIN_IMPORTED,
        )
        ex_close = _make_execution(
            user_id=user_id,
            trade_id=trade.id,
            symbol="ATOS",
            direction=Direction.SHORT,
            quantity=Decimal("5"),
            price=Decimal("40"),
            executed_at=datetime(2024, 3, 13, 15, 0, tzinfo=UTC),
            origin=EXECUTION_ORIGIN_IMPORTED,
        )

        service.trade_repo.get_by_id.return_value = trade
        service.execution_repo.list_by_trade_id.return_value = [ex_open, ex_close]

        service._re_aggregate_trade = ExecutionService._re_aggregate_trade.__get__(service, ExecutionService)
        split = _make_corporate_action(symbol="ATOS", ratio=Decimal("0.05"), date_value=datetime(2024, 3, 13, 0, 0, tzinfo=UTC))
        ex_close.currency = "USD"
        await service._re_aggregate_trade(trade.id, user_id, corporate_actions=[split])

        assert trade.quantity == Decimal("5")
        assert trade.entry_price == Decimal("40")

    async def test_reaggregate_trade_holding_period_adjusts_open_position_once(
        self,
        service: ExecutionService,
    ) -> None:
        user_id = uuid.uuid4()
        trade = _make_trade(
            user_id=user_id,
            symbol="ATOS",
            direction=Direction.LONG,
            opened_at=datetime(2024, 3, 1, 14, 0, tzinfo=UTC),
            closed_at=datetime(2024, 4, 1, 14, 0, tzinfo=UTC),
        )
        ex_open = _make_execution(
            user_id=user_id,
            trade_id=trade.id,
            symbol="ATOS",
            direction=Direction.LONG,
            quantity=Decimal("150"),
            price=Decimal("2"),
            executed_at=datetime(2024, 3, 1, 14, 0, tzinfo=UTC),
            origin=EXECUTION_ORIGIN_IMPORTED,
        )
        ex_close = _make_execution(
            user_id=user_id,
            trade_id=trade.id,
            symbol="ATOS",
            direction=Direction.SHORT,
            quantity=Decimal("7.5"),
            price=Decimal("42"),
            executed_at=datetime(2024, 4, 1, 14, 0, tzinfo=UTC),
            origin=EXECUTION_ORIGIN_IMPORTED,
        )

        service.trade_repo.get_by_id.return_value = trade
        service.execution_repo.list_by_trade_id.return_value = [ex_open, ex_close]

        service._re_aggregate_trade = ExecutionService._re_aggregate_trade.__get__(service, ExecutionService)
        split = _make_corporate_action(symbol="ATOS", ratio=Decimal("0.05"), date_value=datetime(2024, 3, 13, 0, 0, tzinfo=UTC))
        ex_close.currency = "USD"
        await service._re_aggregate_trade(trade.id, user_id, corporate_actions=[split])

        assert trade.quantity == Decimal("7.5")
        assert trade.entry_price == Decimal("40")

    async def test_reaggregate_trade_after_hours_uses_exchange_local_date(
        self,
        service: ExecutionService,
    ) -> None:
        user_id = uuid.uuid4()
        trade = _make_trade(
            user_id=user_id,
            symbol="AFTER",
            direction=Direction.LONG,
            opened_at=datetime(2024, 3, 13, 1, 30, tzinfo=UTC),
            closed_at=datetime(2024, 3, 14, 15, 0, tzinfo=UTC),
        )
        ex_open = _make_execution(
            user_id=user_id,
            trade_id=trade.id,
            symbol="AFTER",
            direction=Direction.LONG,
            quantity=Decimal("100"),
            price=Decimal("2"),
            executed_at=datetime(2024, 3, 13, 1, 30, tzinfo=UTC),
            origin=EXECUTION_ORIGIN_IMPORTED,
            currency="USD",
        )
        ex_close = _make_execution(
            user_id=user_id,
            trade_id=trade.id,
            symbol="AFTER",
            direction=Direction.SHORT,
            quantity=Decimal("5"),
            price=Decimal("40"),
            executed_at=datetime(2024, 3, 14, 15, 0, tzinfo=UTC),
            origin=EXECUTION_ORIGIN_IMPORTED,
            currency="USD",
        )

        service.trade_repo.get_by_id.return_value = trade
        service.execution_repo.list_by_trade_id.return_value = [ex_open, ex_close]

        service._re_aggregate_trade = ExecutionService._re_aggregate_trade.__get__(service, ExecutionService)
        split = _make_corporate_action(symbol="AFTER", ratio=Decimal("0.05"), date_value=datetime(2024, 3, 13, 0, 0, tzinfo=UTC))
        ex_close.currency = "USD"
        await service._re_aggregate_trade(trade.id, user_id, corporate_actions=[split])

        assert trade.quantity == Decimal("5")
        assert trade.entry_price == Decimal("40")

    async def test_reaggregate_trade_commission_is_not_split_scaled(
        self,
        service: ExecutionService,
    ) -> None:
        user_id = uuid.uuid4()
        trade = _make_trade(
            user_id=user_id,
            symbol="COMM",
            direction=Direction.LONG,
            opened_at=datetime(2024, 1, 1, 14, 0, tzinfo=UTC),
            closed_at=datetime(2024, 6, 1, 14, 0, tzinfo=UTC),
        )
        ex_open = _make_execution(
            user_id=user_id,
            trade_id=trade.id,
            symbol="COMM",
            direction=Direction.LONG,
            quantity=Decimal("100"),
            price=Decimal("2"),
            commission=Decimal("3"),
            executed_at=datetime(2024, 1, 1, 14, 0, tzinfo=UTC),
            origin=EXECUTION_ORIGIN_IMPORTED,
        )
        ex_close = _make_execution(
            user_id=user_id,
            trade_id=trade.id,
            symbol="COMM",
            direction=Direction.SHORT,
            quantity=Decimal("5"),
            price=Decimal("44"),
            commission=Decimal("2"),
            executed_at=datetime(2024, 6, 1, 14, 0, tzinfo=UTC),
            origin=EXECUTION_ORIGIN_IMPORTED,
        )

        service.trade_repo.get_by_id.return_value = trade
        service.execution_repo.list_by_trade_id.return_value = [ex_open, ex_close]

        service._re_aggregate_trade = ExecutionService._re_aggregate_trade.__get__(service, ExecutionService)
        split = _make_corporate_action(symbol="COMM", ratio=Decimal("0.05"), date_value=datetime(2024, 3, 13, 0, 0, tzinfo=UTC))
        await service._re_aggregate_trade(trade.id, user_id, corporate_actions=[split])

        assert trade.commission == Decimal("5")

    async def test_reaggregate_trade_matches_import_aggregator_values(
        self,
        service: ExecutionService,
    ) -> None:
        user_id = uuid.uuid4()
        opened_at = datetime(2024, 1, 1, 14, 0, tzinfo=UTC)
        closed_at = datetime(2024, 6, 1, 14, 0, tzinfo=UTC)
        trade = _make_trade(
            user_id=user_id,
            symbol="ALIGN",
            direction=Direction.LONG,
            opened_at=opened_at,
            closed_at=closed_at,
        )
        ex_open = _make_execution(
            user_id=user_id,
            trade_id=trade.id,
            symbol="ALIGN",
            direction=Direction.LONG,
            quantity=Decimal("100"),
            price=Decimal("2"),
            commission=Decimal("3"),
            executed_at=opened_at,
            origin=EXECUTION_ORIGIN_IMPORTED,
        )
        ex_close = _make_execution(
            user_id=user_id,
            trade_id=trade.id,
            symbol="ALIGN",
            direction=Direction.SHORT,
            quantity=Decimal("5"),
            price=Decimal("44"),
            commission=Decimal("2"),
            executed_at=closed_at,
            origin=EXECUTION_ORIGIN_IMPORTED,
        )
        service._re_aggregate_trade = ExecutionService._re_aggregate_trade.__get__(service, ExecutionService)
        split = _make_corporate_action(symbol="ALIGN", ratio=Decimal("0.05"), date_value=datetime(2024, 3, 13, 0, 0, tzinfo=UTC))

        service.trade_repo.get_by_id.return_value = trade
        service.execution_repo.list_by_trade_id.return_value = [ex_open, ex_close]
        await service._re_aggregate_trade(trade.id, user_id, corporate_actions=[split])

        import_trades = [
            TradeCreate(
                symbol="ALIGN",
                direction=Direction.LONG,
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("100"),
                entry_price=Decimal("2"),
                opened_at=opened_at,
                commission=Decimal("3"),
                currency="USD",
                broker_conid=None,
            ),
            TradeCreate(
                symbol="ALIGN",
                direction=Direction.SHORT,
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("5"),
                entry_price=Decimal("44"),
                opened_at=closed_at,
                pnl=Decimal("20"),
                commission=Decimal("2"),
                currency="USD",
                broker_conid=None,
            ),
        ]
        fifo_result = aggregate_executions_fifo(import_trades, corporate_actions=[split])
        completed = [row for row in fifo_result if row.closed_at is not None]
        assert len(completed) == 1
        expected = completed[0]

        assert trade.quantity == expected.quantity
        assert trade.entry_price == expected.entry_price
        assert trade.exit_price == expected.exit_price
        assert trade.commission == expected.commission
        assert trade.net_pnl == expected.net_pnl

    async def test_reaggregate_trade_idempotent_for_same_inputs(
        self,
        service: ExecutionService,
    ) -> None:
        user_id = uuid.uuid4()
        trade = _make_trade(
            user_id=user_id,
            symbol="IDEMP",
            direction=Direction.LONG,
            opened_at=datetime(2024, 1, 1, 14, 0, tzinfo=UTC),
            closed_at=datetime(2024, 6, 1, 14, 0, tzinfo=UTC),
        )
        ex_open = _make_execution(
            user_id=user_id,
            trade_id=trade.id,
            symbol="IDEMP",
            direction=Direction.LONG,
            quantity=Decimal("100"),
            price=Decimal("2"),
            commission=Decimal("3"),
            executed_at=datetime(2024, 1, 1, 14, 0, tzinfo=UTC),
            origin=EXECUTION_ORIGIN_IMPORTED,
        )
        ex_close = _make_execution(
            user_id=user_id,
            trade_id=trade.id,
            symbol="IDEMP",
            direction=Direction.SHORT,
            quantity=Decimal("5"),
            price=Decimal("44"),
            commission=Decimal("2"),
            executed_at=datetime(2024, 6, 1, 14, 0, tzinfo=UTC),
            origin=EXECUTION_ORIGIN_IMPORTED,
        )
        service._re_aggregate_trade = ExecutionService._re_aggregate_trade.__get__(service, ExecutionService)
        split = _make_corporate_action(ratio=Decimal("0.05"), date_value=datetime(2024, 3, 13, 0, 0, tzinfo=UTC))

        service.trade_repo.get_by_id.return_value = trade
        service.execution_repo.list_by_trade_id.return_value = [ex_open, ex_close]

        await service._re_aggregate_trade(trade.id, user_id, corporate_actions=[split])
        first = (
            trade.quantity,
            trade.entry_price,
            trade.exit_price,
            trade.commission,
            trade.pnl,
            trade.net_pnl,
            trade.closed_at,
        )

        await service._re_aggregate_trade(trade.id, user_id, corporate_actions=[split])
        second = (
            trade.quantity,
            trade.entry_price,
            trade.exit_price,
            trade.commission,
            trade.pnl,
            trade.net_pnl,
            trade.closed_at,
        )

        assert second == first

    async def test_list_for_trade_manual_leg_fallback_and_adjustment(self, service: ExecutionService) -> None:
        user_id = uuid.uuid4()
        trade = _make_trade(user_id=user_id, symbol="AAPL")
        manual_no_ca = _make_execution(
            user_id=user_id,
            trade_id=trade.id,
            symbol="AAPL",
            quantity=Decimal("4"),
            price=Decimal("80"),
            executed_at=datetime(2025, 1, 1, tzinfo=UTC),
            origin=EXECUTION_ORIGIN_MANUAL,
        )
        manual_with_ca = _make_execution(
            user_id=user_id,
            trade_id=trade.id,
            symbol="AAPL",
            quantity=Decimal("1"),
            price=Decimal("500"),
            executed_at=datetime(2024, 1, 1, tzinfo=UTC),
            origin=EXECUTION_ORIGIN_MANUAL,
        )
        service.trade_repo.get_by_id.return_value = trade
        service.execution_repo.list_by_trade_id.return_value = [manual_no_ca, manual_with_ca]
        service.corporate_action_service.list_for_execution.return_value = [
            _make_corporate_action(ratio=Decimal("10"), date_value=datetime(2024, 1, 10, tzinfo=UTC))
        ]

        result = await service.list_for_trade(trade.id, user_id)

        assert result[0].price == result[0].raw_price
        assert result[0].quantity == result[0].raw_quantity
        assert result[1].price != result[1].raw_price
        assert result[1].quantity != result[1].raw_quantity
        assert result[1].raw_price == Decimal("500")
        assert result[1].raw_quantity == Decimal("1")

    async def test_list_for_trade_notional_invariant_after_adjustment(self, service: ExecutionService) -> None:
        user_id = uuid.uuid4()
        trade = _make_trade(user_id=user_id, symbol="AAPL")
        execution = _make_execution(
            user_id=user_id,
            trade_id=trade.id,
            symbol="AAPL",
            quantity=Decimal("3"),
            price=Decimal("125"),
            executed_at=datetime(2024, 1, 1, tzinfo=UTC),
            origin=EXECUTION_ORIGIN_IMPORTED,
        )
        service.trade_repo.get_by_id.return_value = trade
        service.execution_repo.list_by_trade_id.return_value = [execution]
        service.corporate_action_service.list_for_execution.return_value = [
            _make_corporate_action(ratio=Decimal("2.5"), date_value=datetime(2024, 1, 10, tzinfo=UTC))
        ]

        result = await service.list_for_trade(trade.id, user_id)

        item = result[0]
        tolerance = Decimal("0.0000001")
        adjusted_notional = item.price * item.quantity
        raw_notional = item.raw_price * item.raw_quantity
        assert abs(adjusted_notional - raw_notional) <= tolerance
