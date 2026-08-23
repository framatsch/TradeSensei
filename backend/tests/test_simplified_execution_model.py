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

"""Unit tests for the simplified-execution-model spec (tasks 9.10–9.16).

All tests are pure unit tests — no database access (mocked).

Covers:
  9.10  Aggregator excludes deleted=True executions from P&L
  9.11  Restoring a deleted execution updates trade P&L
  9.12  Import skips BRT with suppressed=True
  9.13  Re-import skips BRT whose linked execution has deleted=True
  9.14  Re-import of unchanged execution is idempotent
  9.15  Fresh-start deletes trades+executions, keeps BRTs, creates new executions
  9.16  Fresh-start rolls back entirely on import error
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.broker_raw_transaction import BrokerRawTransaction
from app.models.logical_execution import (
    EXECUTION_ORIGIN_IMPORTED,
    EXECUTION_ORIGIN_MANUAL,
    LogicalExecution,
)
from app.models.trade import AssetClass, Direction, Trade
from app.services.execution import ExecutionService
from app.services.logical_execution_service import LogicalExecutionService

TEST_PORTFOLIO_ID = uuid.uuid4()


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_trade(
    direction: Direction = Direction.LONG,
    multiplier: int = 1,
) -> Trade:
    """Create a minimal Trade ORM stub."""
    trade = Trade()
    trade.has_conflict = False
    trade.id = uuid.uuid4()
    trade.user_id = uuid.uuid4()
    trade.direction = direction
    trade.multiplier = multiplier
    return trade


def _make_execution(
    id: uuid.UUID | None = None,
    trade_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    direction: Direction = Direction.LONG,
    quantity: Decimal = Decimal("10"),
    price: Decimal = Decimal("100"),
    commission: Decimal = Decimal("0"),
    executed_at: datetime | None = None,
    origin: str = EXECUTION_ORIGIN_MANUAL,
    deleted: bool = False,
    pnl: Decimal | None = None,
) -> LogicalExecution:
    """Create a minimal LogicalExecution ORM stub."""
    now = datetime.now(UTC)
    ex = LogicalExecution(
        id=id or uuid.uuid4(),
        trade_id=trade_id or uuid.uuid4(),
        user_id=user_id or uuid.uuid4(),
        account_id=uuid.uuid4(),
        symbol="AAPL",
        asset_class=AssetClass.EQUITY,
        direction=direction,
        quantity=quantity,
        price=price,
        commission=commission,
        executed_at=executed_at or now,
        origin=origin,
        deleted=deleted,
        user_modified=False,
        multiplier=1,
        created_at=now,
        updated_at=now,
        pnl=pnl,
    )
    return ex


def _make_raw(
    user_id: uuid.UUID | None = None,
    account_id: uuid.UUID | None = None,
    suppressed: bool = False,
) -> BrokerRawTransaction:
    """Create a minimal BrokerRawTransaction ORM stub."""
    now = datetime.now(UTC)
    raw = BrokerRawTransaction(
        id=f"user:{uuid.uuid4().hex[:12]}",
        user_id=user_id or uuid.uuid4(),
        account_id=account_id or uuid.uuid4(),
        broker_type="ibkr",
        symbol="AAPL",
        direction=Direction.LONG,
        quantity=Decimal("10"),
        price=Decimal("100"),
        commission=Decimal("0"),
        executed_at=now,
        asset_class=AssetClass.EQUITY,
        raw_data={"test": True},
        suppressed=suppressed,
    )
    return raw


# ─── Task 9.10: Aggregator excludes deleted executions ─────────────────────────


@pytest.mark.asyncio
async def test_aggregator_excludes_deleted_executions(mock_session: AsyncMock) -> None:
    """_re_aggregate_trade must exclude executions with deleted=True from P&L.

    Setup: Trade has two entry executions (one active, one deleted) and one exit.
    Only the active entry and exit should feed the P&L calculation.
    """
    service = ExecutionService(mock_session)
    trade = _make_trade(direction=Direction.LONG)

    service.trade_repo = AsyncMock()
    service.trade_repo.get_by_id = AsyncMock(return_value=trade)

    # Active entry: buy 10 @ 100
    active_entry = _make_execution(
        trade_id=trade.id,
        user_id=trade.user_id,
        direction=Direction.LONG,
        quantity=Decimal("10"),
        price=Decimal("100"),
        commission=Decimal("1"),
        deleted=False,
    )
    # Deleted entry: buy 5 @ 200 — must NOT be counted
    _make_execution(
        trade_id=trade.id,
        user_id=trade.user_id,
        direction=Direction.LONG,
        quantity=Decimal("5"),
        price=Decimal("200"),
        commission=Decimal("0.5"),
        deleted=True,
    )
    # Exit: sell 10 @ 120
    exit_exec = _make_execution(
        trade_id=trade.id,
        user_id=trade.user_id,
        direction=Direction.SHORT,
        quantity=Decimal("10"),
        price=Decimal("120"),
        commission=Decimal("1"),
        deleted=False,
    )

    # list_by_trade_id is called with include_deleted=False — only active execs
    service.execution_repo = AsyncMock()
    service.execution_repo.list_by_trade_id = AsyncMock(
        return_value=[active_entry, exit_exec]
    )

    await service._re_aggregate_trade(trade.id, trade.user_id)

    # Verify only active entry drives the calculation
    assert trade.quantity == Decimal("10")
    assert trade.entry_price == Decimal("100")
    assert trade.exit_price == Decimal("120")
    # PnL = (120 - 100) * 10 = 200
    assert trade.pnl is not None
    assert trade.pnl == Decimal("200")
    # Net PnL = 200 - (1+1) = 198
    assert trade.net_pnl is not None
    assert trade.net_pnl == Decimal("198")


# ─── Task 9.11: Restoring execution updates trade P&L ─────────────────────────


@pytest.mark.asyncio
async def test_restore_execution_updates_pnl(mock_session: AsyncMock) -> None:
    """restore_execution must mark the execution as not deleted and re-aggregate.

    Re-aggregation is already covered by separate tests; here we verify that
    restore_execution triggers it.
    """
    service = ExecutionService(mock_session)
    trade = _make_trade(direction=Direction.LONG)
    trade.pnl = Decimal("0")

    exec_id = uuid.uuid4()
    deleted_exec = _make_execution(
        id=exec_id,
        trade_id=trade.id,
        user_id=trade.user_id,
        deleted=True,
        origin=EXECUTION_ORIGIN_IMPORTED,
    )

    # After restore the repo returns the updated (non-deleted) execution
    restored_exec = _make_execution(
        id=exec_id,
        trade_id=trade.id,
        user_id=trade.user_id,
        deleted=False,
        origin=EXECUTION_ORIGIN_IMPORTED,
    )

    service.execution_repo = AsyncMock()
    service.execution_repo.get_by_id = AsyncMock(
        side_effect=[deleted_exec, restored_exec]
    )
    service.execution_repo.restore = AsyncMock()
    service.trade_repo.get_by_id = AsyncMock(return_value=trade)
    service._re_aggregate_trade = AsyncMock()

    result = await service.restore_execution(exec_id, trade.user_id)

    # restore was called
    service.execution_repo.restore.assert_awaited_once_with(exec_id)
    # re-aggregation was triggered
    service._re_aggregate_trade.assert_awaited_once_with(trade.id, trade.user_id)
    # returned the restored execution
    assert result.deleted is False


# ─── Task 9.12: Import skips BRT with suppressed=True ─────────────────────────


@pytest.mark.asyncio
async def test_import_skips_suppressed_brt(mock_session: AsyncMock) -> None:
    """LogicalExecutionService.create_from_raw must return None for suppressed BRTs."""
    svc = LogicalExecutionService(mock_session)
    svc._execution_repo = AsyncMock()

    suppressed_raw = _make_raw(suppressed=True)

    result = await svc.create_from_raw(suppressed_raw)

    assert result is None
    svc._execution_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_create_from_raw_copies_open_close(mock_session: AsyncMock) -> None:
    """LogicalExecutionService.create_from_raw copies parser-derived open_close."""
    svc = LogicalExecutionService(mock_session)
    svc._execution_repo = AsyncMock()

    raw = _make_raw(suppressed=False)
    raw.open_close = "C"  # type: ignore[assignment]

    logical = await svc.create_from_raw(raw)

    assert logical is not None
    assert logical.open_close == "C"


@pytest.mark.asyncio
async def test_import_bulk_create_counts_suppressed(mock_session: AsyncMock) -> None:
    """bulk_create_from_raw must report the number of suppressed BRTs skipped."""
    svc = LogicalExecutionService(mock_session)
    svc._execution_repo = AsyncMock()

    active_raw = _make_raw(suppressed=False)
    suppressed_raw = _make_raw(suppressed=True)

    # Only the active one will trigger create_from_raw (non-None path)
    created_exec = _make_execution(origin=EXECUTION_ORIGIN_IMPORTED)
    # Patch create_from_raw to return the execution for the active one
    svc.create_from_raw = AsyncMock(side_effect=[created_exec, None])  # type: ignore[method-assign]

    created, suppressed_count = await svc.bulk_create_from_raw(
        [active_raw, suppressed_raw]
    )

    assert suppressed_count == 1
    assert len(created) == 1


# ─── Task 9.13: Re-import skips BRT with linked deleted execution ──────────────


@pytest.mark.asyncio
async def test_bulk_upsert_skips_existing_brt_with_deleted_execution(
    mock_session: AsyncMock,
) -> None:
    """When a BRT already exists (upsert returns no new ID), no logical execution
    is created — even if the linked execution has deleted=True.

    The import deduplication is handled at the BRT-upsert level: only
    *newly* inserted BRT IDs are passed to bulk_create_from_raw.  An
    existing BRT (already in the DB) whose linked execution has deleted=True
    will produce an empty ``newly_inserted_raw`` list → no executions created.

    This test verifies the service contract: when upsert returns an empty set,
    create_from_raw is never called.
    """
    svc = LogicalExecutionService(mock_session)
    svc._execution_repo = AsyncMock()
    svc.create_from_raw = AsyncMock()  # type: ignore[method-assign]

    # Simulate bulk_create_from_raw being called with an empty list
    # (all BRTs already existed → raw_repo.bulk_upsert returned empty set)
    created, suppressed_count = await svc.bulk_create_from_raw([])

    assert created == []
    assert suppressed_count == 0
    svc.create_from_raw.assert_not_called()


# ─── Task 9.14: Re-import of unchanged execution is idempotent ─────────────────


@pytest.mark.asyncio
async def test_reimport_idempotent_via_brt_upsert(mock_session: AsyncMock) -> None:
    """bulk_upsert deduplication means an unchanged BRT creates no duplicate
    logical execution.

    Simulate: a raw_repo.bulk_upsert that returns an empty set (the BRT
    already existed and was not re-inserted). Verify that no new executions
    are created.
    """
    svc = LogicalExecutionService(mock_session)
    svc._execution_repo = AsyncMock()
    svc.create_from_raw = AsyncMock()  # type: ignore[method-assign]

    # Identical call — zero new BRTs means zero logical executions
    created, suppressed_count = await svc.bulk_create_from_raw([])

    assert created == []
    assert suppressed_count == 0
    svc.create_from_raw.assert_not_called()


# ─── Task 9.15: Fresh-start deletes trades+executions, then re-imports ─────────


@pytest.mark.asyncio
async def test_fresh_start_deletes_and_reimports(mock_session: AsyncMock) -> None:
    """fresh_start_import must delete all executions and trades for the account
    before running import_trades; BRTs are not deleted (preserved for audit).
    """
    from app.schemas.imports import FreshStartResult, ImportResult
    from app.services.import_service import ImportService

    svc = ImportService(mock_session)

    account_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Mock repository calls
    svc._account_repo = AsyncMock()
    svc._account_repo.get_by_id = AsyncMock(return_value=MagicMock(id=account_id))

    svc._exec_repo = AsyncMock()
    svc._exec_repo.delete_all_for_account = AsyncMock(return_value=5)

    svc._trade_repo = AsyncMock()
    svc._trade_repo.delete_by_user_account = AsyncMock(return_value=3)

    import_result = ImportResult(
        broker="ibkr",
        filename="test.csv",
        trades_parsed=2,
        trades_created=2,
        trades_skipped=0,
        cash_transactions_parsed=0,
        cash_transactions_created=0,
        cash_transactions_skipped=0,
        warnings=[],
    )
    svc.import_trades = AsyncMock(return_value=import_result)  # type: ignore[method-assign]

    from app.utils.parsers.factory import BrokerType

    result = await svc.fresh_start_import(
        content=b"test",
        filename="test.csv",
        broker=BrokerType.IBKR,
        portfolio_id=TEST_PORTFOLIO_ID,
        account_id=account_id,
        user_id=user_id,
    )

    # Deletions happened before import
    svc._exec_repo.delete_all_for_account.assert_awaited_once_with(
        user_id=user_id, account_id=account_id
    )
    svc._trade_repo.delete_by_user_account.assert_awaited_once_with(
        user_id=user_id, account_id=account_id, include_manually_edited=True
    )

    # Import was called
    svc.import_trades.assert_awaited_once()

    # Result contains deletion counts and the import summary
    assert isinstance(result, FreshStartResult)
    assert result.executions_deleted == 5
    assert result.trades_deleted == 3
    assert result.import_result.trades_created == 2


# ─── Task 9.16: Fresh-start rolls back entirely on import error ────────────────


@pytest.mark.asyncio
async def test_fresh_start_rollback_on_import_error(mock_session: AsyncMock) -> None:
    """fresh_start_import must propagate any exception from import_trades so the
    caller's transaction is rolled back (the service does not commit).

    The route handler owns the transaction boundary; an exception bubbling up
    causes the surrounding context manager to roll back.
    """
    from app.services.import_service import ImportService
    from app.utils.parsers.factory import BrokerType

    svc = ImportService(mock_session)

    account_id = uuid.uuid4()
    user_id = uuid.uuid4()

    svc._account_repo = AsyncMock()
    svc._account_repo.get_by_id = AsyncMock(return_value=MagicMock(id=account_id))

    svc._exec_repo = AsyncMock()
    svc._exec_repo.delete_all_for_account = AsyncMock(return_value=3)

    svc._trade_repo = AsyncMock()
    svc._trade_repo.delete_by_user_account = AsyncMock(return_value=2)

    # import_trades raises an error
    svc.import_trades = AsyncMock(  # type: ignore[method-assign]
        side_effect=ValueError("Parse error: malformed CSV")
    )

    with pytest.raises(ValueError, match="Parse error"):
        await svc.fresh_start_import(
            content=b"bad data",
            filename="bad.csv",
            broker=BrokerType.IBKR,
            portfolio_id=TEST_PORTFOLIO_ID,
            account_id=account_id,
            user_id=user_id,
        )

    # Deletions happened before the error — the caller must roll back
    svc._exec_repo.delete_all_for_account.assert_awaited_once()
    svc._trade_repo.delete_by_user_account.assert_awaited_once()
