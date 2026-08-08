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

"""Unit tests for split-aware linking methods in ImportService."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import OperationalError

from app.core.exceptions import (
    ExecutionNotFoundError,
    ExecutionValidationError,
    TradeNotFoundError,
)
from app.services.import_service import ImportService
from app.utils.parsers.aggregator import ExecutionAllocation, TradeCreateWithSources


def _service() -> ImportService:
    return ImportService(AsyncMock())


class _AsyncNullContext:
    """Minimal async context manager used for begin_nested mocking."""

    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> bool:
        del exc_type, exc, tb
        return False


@pytest.mark.unit
async def test_backfill_direct_assignment_for_single_usage() -> None:
    service = _service()
    service._assign_execution_to_trade = AsyncMock(return_value=True)
    service._process_execution_split = AsyncMock()
    service._validate_split_backfill_consistency = AsyncMock()
    service._find_orphaned_children_for_trades = AsyncMock(return_value=0)
    service._trade_repo.get_by_id = AsyncMock()

    trade = MagicMock()
    trade.id = uuid.uuid4()
    trade.account_id = uuid.uuid4()
    allocation = ExecutionAllocation(
        execution_id=uuid.uuid4(),
        quantity_used=Decimal("10"),
        commission_used=Decimal("0.2"),
        entry_price=Decimal("100"),
    )
    tws = TradeCreateWithSources(
        trade_create=MagicMock(), source_executions=[allocation]
    )
    tws.created_trade = trade
    user_id = uuid.uuid4()
    execution = MagicMock(
        id=allocation.execution_id,
        user_id=user_id,
        quantity=Decimal("10"),
        commission=Decimal("0.2"),
    )
    service._exec_repo.list_by_ids = AsyncMock(return_value=[execution])
    service._exec_repo.bulk_update_trade_ids = AsyncMock(return_value=1)
    service._session.begin_nested = MagicMock(return_value=_AsyncNullContext())

    await service._backfill_execution_trade_links([tws], user_id)

    service._exec_repo.bulk_update_trade_ids.assert_awaited_once()
    service._process_execution_split.assert_not_called()


@pytest.mark.unit
async def test_backfill_uses_split_for_multi_trade_usage() -> None:
    service = _service()
    service._assign_execution_to_trade = AsyncMock(return_value=True)
    service._process_execution_split = AsyncMock(return_value=2)
    service._validate_split_backfill_consistency = AsyncMock()
    service._find_orphaned_children_for_trades = AsyncMock(return_value=0)
    service._trade_repo.get_by_id = AsyncMock()

    shared_exec = uuid.uuid4()
    trade1 = MagicMock(id=uuid.uuid4())
    trade2 = MagicMock(id=uuid.uuid4())
    trade1.account_id = uuid.uuid4()
    trade2.account_id = trade1.account_id

    tws1 = TradeCreateWithSources(
        trade_create=MagicMock(),
        source_executions=[
            ExecutionAllocation(
                execution_id=shared_exec,
                quantity_used=Decimal("60"),
                commission_used=Decimal("0.6"),
                entry_price=Decimal("100"),
            )
        ],
    )
    tws1.created_trade = trade1

    tws2 = TradeCreateWithSources(
        trade_create=MagicMock(),
        source_executions=[
            ExecutionAllocation(
                execution_id=shared_exec,
                quantity_used=Decimal("40"),
                commission_used=Decimal("0.4"),
                entry_price=Decimal("100"),
            )
        ],
    )
    tws2.created_trade = trade2

    user_id = uuid.uuid4()
    execution = MagicMock(
        id=shared_exec,
        user_id=user_id,
        quantity=Decimal("100"),
        commission=Decimal("1.0"),
    )
    service._exec_repo.list_by_ids = AsyncMock(return_value=[execution])
    service._exec_repo.bulk_update_trade_ids = AsyncMock(return_value=0)
    service._session.begin_nested = MagicMock(return_value=_AsyncNullContext())

    await service._backfill_execution_trade_links([tws1, tws2], user_id)

    service._process_execution_split.assert_awaited_once()
    service._exec_repo.bulk_update_trade_ids.assert_not_called()


@pytest.mark.unit
async def test_validate_split_quantities_overflow_raises() -> None:
    service = _service()
    allocations = [
        ExecutionAllocation(
            uuid.uuid4(), Decimal("70"), Decimal("0.7"), Decimal("100")
        ),
        ExecutionAllocation(
            uuid.uuid4(), Decimal("40"), Decimal("0.3"), Decimal("100")
        ),
    ]

    with pytest.raises(ExecutionValidationError, match="Allocation overflow"):
        service._validate_split_quantities(Decimal("100"), allocations)


@pytest.mark.unit
async def test_validate_split_commissions_overflow_raises() -> None:
    service = _service()
    allocations = [
        ExecutionAllocation(
            uuid.uuid4(), Decimal("60"), Decimal("0.8"), Decimal("100")
        ),
        ExecutionAllocation(
            uuid.uuid4(), Decimal("40"), Decimal("0.3"), Decimal("100")
        ),
    ]

    with pytest.raises(ExecutionValidationError, match="Commission overflow"):
        service._validate_split_commissions(Decimal("1.0"), allocations)


@pytest.mark.unit
async def test_process_execution_split_quantity_conservation() -> None:
    service = _service()
    execution_id = uuid.uuid4()
    parent = MagicMock()
    parent.id = execution_id
    parent.user_id = uuid.uuid4()
    parent.account_id = uuid.uuid4()
    parent.symbol = "SPLIT_A"
    parent.conid = "999001"
    parent.asset_class = "EQUITY"
    parent.direction = "LONG"
    parent.quantity = Decimal("100")
    parent.price = Decimal("100")
    parent.commission = Decimal("1.0")
    parent.executed_at = MagicMock()
    parent.pnl = Decimal("800")
    parent.currency = "USD"
    parent.multiplier = 1

    service._exec_repo.get_by_id = AsyncMock(return_value=parent)
    service._exec_repo.soft_delete = AsyncMock(return_value=True)
    service._exec_repo.create = AsyncMock()

    trade1_id = uuid.uuid4()
    trade2_id = uuid.uuid4()
    usage = [
        (
            trade1_id,
            ExecutionAllocation(
                execution_id=execution_id,
                quantity_used=Decimal("60"),
                commission_used=Decimal("0.6"),
                entry_price=Decimal("100"),
            ),
        ),
        (
            trade2_id,
            ExecutionAllocation(
                execution_id=execution_id,
                quantity_used=Decimal("40"),
                commission_used=Decimal("0.4"),
                entry_price=Decimal("100"),
            ),
        ),
    ]

    created_count = await service._process_execution_split(
        parent, usage, parent.user_id
    )

    assert service._exec_repo.create.await_count == 2
    assert created_count == 2
    create_calls = service._exec_repo.create.await_args_list
    created_qty = [call.kwargs["quantity"] for call in create_calls]
    assert sum(created_qty) == Decimal("100")
    assert all(call.kwargs["parent_id"] == execution_id for call in create_calls)


@pytest.mark.unit
async def test_process_execution_split_missing_parent_raises() -> None:
    service = _service()
    parent = MagicMock()
    parent.id = uuid.uuid4()
    parent.user_id = uuid.uuid4()
    parent.quantity = Decimal("1")
    parent.commission = Decimal("0.1")
    service._exec_repo.soft_delete = AsyncMock(return_value=False)

    with pytest.raises(ExecutionNotFoundError, match="soft-delete"):
        await service._process_execution_split(
            execution=parent,
            usage_list=[],
            user_id=parent.user_id,
        )


@pytest.mark.unit
async def test_assign_execution_to_trade_validates_trade_and_execution() -> None:
    service = _service()
    user_id = uuid.uuid4()
    trade_id = uuid.uuid4()
    execution_id = uuid.uuid4()

    service._trade_repo.get_by_id = AsyncMock(return_value=None)
    service._exec_repo.get_by_id = AsyncMock()

    with pytest.raises(TradeNotFoundError):
        await service._assign_execution_to_trade(execution_id, trade_id, user_id)

    service._trade_repo.get_by_id = AsyncMock(return_value=MagicMock())
    service._exec_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(ExecutionNotFoundError):
        await service._assign_execution_to_trade(execution_id, trade_id, user_id)


@pytest.mark.unit
async def test_validate_split_backfill_consistency_checks_conservation() -> None:
    service = _service()
    parent_id = uuid.uuid4()
    trade_id = uuid.uuid4()
    parent = MagicMock(quantity=Decimal("100"), commission=Decimal("1.0"))
    usage_list = [
        (
            trade_id,
            ExecutionAllocation(
                execution_id=parent_id,
                quantity_used=Decimal("100"),
                commission_used=Decimal("1.0"),
                entry_price=Decimal("100"),
            ),
        )
    ]

    child = MagicMock(
        trade_id=trade_id,
        parent_id=parent_id,
        origin="split",
        quantity=Decimal("100"),
        commission=Decimal("1.0"),
    )
    service._exec_repo.get_by_parent_id = AsyncMock(return_value=[child])

    await service._validate_split_backfill_consistency(
        {parent_id: (parent, usage_list)}
    )


@pytest.mark.unit
async def test_validate_split_backfill_consistency_fails_assignment_completeness() -> (
    None
):
    service = _service()
    parent_id = uuid.uuid4()
    trade_id = uuid.uuid4()
    parent = MagicMock(quantity=Decimal("100"), commission=Decimal("1.0"))
    usage_list = [
        (
            trade_id,
            ExecutionAllocation(
                execution_id=parent_id,
                quantity_used=Decimal("100"),
                commission_used=Decimal("1.0"),
                entry_price=Decimal("100"),
            ),
        )
    ]

    orphan_child = MagicMock(
        trade_id=None,
        parent_id=parent_id,
        origin="split",
        quantity=Decimal("100"),
        commission=Decimal("1.0"),
    )
    service._exec_repo.get_by_parent_id = AsyncMock(return_value=[orphan_child])

    with pytest.raises(ExecutionValidationError, match="assignment completeness"):
        await service._validate_split_backfill_consistency(
            {parent_id: (parent, usage_list)}
        )


@pytest.mark.unit
async def test_resolve_orphaned_children_assigns_unassigned_trade_ids() -> None:
    service = _service()
    user_id = uuid.uuid4()
    account_id = uuid.uuid4()
    parent_id = uuid.uuid4()
    trade_1 = MagicMock(id=uuid.uuid4(), account_id=account_id)
    trade_2 = MagicMock(id=uuid.uuid4(), account_id=account_id)

    tws_1 = TradeCreateWithSources(
        trade_create=MagicMock(),
        source_executions=[
            ExecutionAllocation(
                execution_id=parent_id,
                quantity_used=Decimal("60"),
                commission_used=Decimal("0.6"),
                entry_price=Decimal("100"),
            )
        ],
    )
    tws_1.created_trade = trade_1

    tws_2 = TradeCreateWithSources(
        trade_create=MagicMock(),
        source_executions=[
            ExecutionAllocation(
                execution_id=parent_id,
                quantity_used=Decimal("40"),
                commission_used=Decimal("0.4"),
                entry_price=Decimal("100"),
            )
        ],
    )
    tws_2.created_trade = trade_2

    orphan = MagicMock(id=uuid.uuid4(), parent_id=parent_id)
    assigned_child = MagicMock(trade_id=trade_1.id)
    unassigned_child = MagicMock(trade_id=None)

    service._exec_repo.find_orphaned_children = AsyncMock(return_value=[orphan])
    service._exec_repo.get_by_parent_id = AsyncMock(
        return_value=[assigned_child, unassigned_child]
    )
    service._exec_repo.update_trade_id = AsyncMock(return_value=True)

    resolved = await service._resolve_orphaned_children_for_trades(
        [tws_1, tws_2],
        user_id,
    )

    assert resolved == 1
    service._exec_repo.update_trade_id.assert_awaited_once_with(orphan.id, trade_2.id)


@pytest.mark.unit
async def test_with_retry_retries_transient_error_then_succeeds() -> None:
    service = _service()
    attempts = 0

    async def operation() -> int:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OperationalError("SELECT 1", {}, Exception("transient"))
        return 42

    result = await service._with_retry("test_operation", operation)

    assert result == 42
    assert attempts == 2


@pytest.mark.unit
async def test_iter_trade_creates_from_logical_batches_pages_results() -> None:
    service = _service()
    execution_1 = MagicMock(
        id=uuid.uuid4(),
        symbol="AAPL",
        conid="123",
        asset_class="EQUITY",
        direction="LONG",
        quantity=Decimal("1"),
        price=Decimal("100"),
        commission=Decimal("0"),
        executed_at=datetime(2026, 1, 1, 10, 0, 0),
        pnl=None,
        multiplier=1,
    )
    execution_2 = MagicMock(
        id=uuid.uuid4(),
        symbol="AAPL",
        conid="123",
        asset_class="EQUITY",
        direction="SHORT",
        quantity=Decimal("1"),
        price=Decimal("101"),
        commission=Decimal("0"),
        executed_at=datetime(2026, 1, 1, 10, 1, 0),
        pnl=Decimal("1"),
        multiplier=1,
    )
    service._logical_svc.list_by_user = AsyncMock(
        side_effect=[[execution_1], [execution_2], []]
    )

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.services.import_service.IMPORT_EXECUTIONS_BATCH_SIZE", 1)
        collected = await service._collect_trade_creates_from_logical_batches(
            user_id=uuid.uuid4(),
            account_id=uuid.uuid4(),
        )

    assert len(collected) == 2
    assert service._logical_svc.list_by_user.await_count == 3


@pytest.mark.unit
async def test_backfill_logs_memory_threshold_warning() -> None:
    service = _service()
    service._trade_repo.get_by_id = AsyncMock(return_value=MagicMock())
    service._exec_repo.get_by_id = AsyncMock()
    service._exec_repo.bulk_update_trade_ids = AsyncMock(return_value=0)
    service._process_execution_split = AsyncMock(return_value=0)
    service._validate_split_backfill_consistency = AsyncMock()
    service._find_orphaned_children_for_trades = AsyncMock(return_value=0)
    service._resolve_orphaned_children_for_trades = AsyncMock(return_value=0)
    service._list_executions_for_backfill = AsyncMock(return_value=[])

    service._session.get_bind = MagicMock(
        return_value=MagicMock(sync_engine=MagicMock())
    )

    trade = MagicMock(id=uuid.uuid4(), account_id=uuid.uuid4())
    tws = TradeCreateWithSources(trade_create=MagicMock(), source_executions=[])
    tws.created_trade = trade

    with (
        pytest.MonkeyPatch.context() as mp,
    ):
        mp.setattr(
            "app.services.import_service.tracemalloc.is_tracing",
            lambda: False,
        )
        mp.setattr(
            "app.services.import_service.tracemalloc.start",
            lambda: None,
        )
        mp.setattr(
            "app.services.import_service.tracemalloc.stop",
            lambda: None,
        )
        mp.setattr(
            "app.services.import_service.tracemalloc.get_traced_memory",
            lambda: (0, 200_000_000),
        )
        warning_logger = MagicMock()
        mp.setattr("app.services.import_service.logger.warning", warning_logger)

        await service._backfill_execution_trade_links([tws], uuid.uuid4())

    warning_logger.assert_called()


# ---------------------------------------------------------------------------
# Task 15.3 — _resolve_anchor_trade_ids (D9 anchor derivation)
# ---------------------------------------------------------------------------


def _allocation(execution_id: uuid.UUID) -> ExecutionAllocation:
    """Build a minimal ExecutionAllocation referencing ``execution_id``."""
    return ExecutionAllocation(
        execution_id=execution_id,
        quantity_used=Decimal("1"),
        commission_used=Decimal("0"),
        entry_price=Decimal("1"),
    )


@pytest.mark.unit
async def test_resolve_anchor_trade_ids_picks_earliest_execution_with_id_tiebreak() -> None:
    service = _service()

    t_early = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    t_late = datetime(2026, 1, 2, 9, 0, tzinfo=UTC)
    t_tie = datetime(2026, 1, 3, 9, 0, tzinfo=UTC)

    # Index 0: two candidates with distinct executed_at — earliest wins.
    exec_late_id, exec_early_id = uuid.uuid4(), uuid.uuid4()
    trade_late_id, trade_early_id = uuid.uuid4(), uuid.uuid4()
    exec_late = MagicMock(id=exec_late_id, executed_at=t_late, trade_id=trade_late_id)
    exec_early = MagicMock(id=exec_early_id, executed_at=t_early, trade_id=trade_early_id)

    # Index 1: two candidates sharing the same executed_at — lower id wins.
    tie_low_id, tie_high_id = sorted([uuid.uuid4(), uuid.uuid4()])
    trade_low_id, trade_high_id = uuid.uuid4(), uuid.uuid4()
    exec_tie_low = MagicMock(id=tie_low_id, executed_at=t_tie, trade_id=trade_low_id)
    exec_tie_high = MagicMock(id=tie_high_id, executed_at=t_tie, trade_id=trade_high_id)

    tws0 = TradeCreateWithSources(
        trade_create=MagicMock(),
        source_executions=[_allocation(exec_late_id), _allocation(exec_early_id)],
    )
    tws1 = TradeCreateWithSources(
        trade_create=MagicMock(),
        source_executions=[_allocation(tie_high_id), _allocation(tie_low_id)],
    )

    service._list_executions_for_backfill = AsyncMock(
        return_value=[exec_late, exec_early, exec_tie_low, exec_tie_high]
    )

    result = await service._resolve_anchor_trade_ids([tws0, tws1], uuid.uuid4())

    assert result == {0: trade_early_id, 1: trade_low_id}


@pytest.mark.unit
async def test_resolve_anchor_trade_ids_omits_index_with_no_resolvable_anchor() -> None:
    service = _service()

    unresolvable_id = uuid.uuid4()
    tws = TradeCreateWithSources(
        trade_create=MagicMock(),
        source_executions=[_allocation(unresolvable_id)],
    )
    # Simulates a brand-new position: the referenced execution id is not
    # present in the batch-loaded executions (e.g. it was never loaded, or
    # belongs to another user and got filtered out upstream).
    service._list_executions_for_backfill = AsyncMock(return_value=[])

    result = await service._resolve_anchor_trade_ids([tws], uuid.uuid4())

    assert result == {}


@pytest.mark.unit
async def test_resolve_anchor_trade_ids_returns_empty_dict_when_no_execution_ids() -> None:
    service = _service()
    service._list_executions_for_backfill = AsyncMock()

    tws = TradeCreateWithSources(trade_create=MagicMock(), source_executions=[])

    result = await service._resolve_anchor_trade_ids([tws], uuid.uuid4())

    assert result == {}
    service._list_executions_for_backfill.assert_not_called()


# ---------------------------------------------------------------------------
# Task 15.4 — _carry_forward_orphaned_protected_metadata (D10 carry-forward)
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_carry_forward_transfers_metadata_to_next_oldest_surviving_trade() -> None:
    service = _service()
    service._transfer_protected_trade_metadata = AsyncMock()

    old_trade = MagicMock(
        id=uuid.uuid4(), is_manually_edited=True, symbol="AAA", opened_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    removed_anchor_id = uuid.uuid4()  # E1: prior anchor, no longer present.
    surviving_leg_id = uuid.uuid4()  # E2: next-oldest surviving leg.

    new_trade = MagicMock(id=uuid.uuid4())
    tws = TradeCreateWithSources(trade_create=MagicMock(), source_executions=[])
    tws.created_trade = new_trade

    current_exec_removed = MagicMock(id=removed_anchor_id, trade_id=None)
    current_exec_surviving = MagicMock(id=surviving_leg_id, trade_id=new_trade.id)
    service._list_executions_for_backfill = AsyncMock(
        return_value=[current_exec_removed, current_exec_surviving]
    )

    await service._carry_forward_orphaned_protected_metadata(
        leftover_protected=[old_trade],
        protected_ordered_legs={old_trade.id: [removed_anchor_id, surviving_leg_id]},
        trades_with_sources=[tws],
        user_id=uuid.uuid4(),
    )

    service._transfer_protected_trade_metadata.assert_awaited_once_with(old_trade, new_trade)


@pytest.mark.unit
async def test_carry_forward_logs_warning_and_skips_when_no_target_found(
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = _service()
    service._transfer_protected_trade_metadata = AsyncMock()

    old_trade = MagicMock(
        id=uuid.uuid4(), is_manually_edited=True, symbol="BBB", opened_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    removed_leg_id = uuid.uuid4()  # resolves to no current trade at all.
    still_here_leg_id = uuid.uuid4()  # still belongs to the same old trade.

    current_exec_removed = MagicMock(id=removed_leg_id, trade_id=None)
    current_exec_still_here = MagicMock(id=still_here_leg_id, trade_id=old_trade.id)
    service._list_executions_for_backfill = AsyncMock(
        return_value=[current_exec_removed, current_exec_still_here]
    )

    # No resolvable target trade exists in `trades_with_sources`, so carry-forward
    # should no-op without attempting transfer. Logger capture is best-effort only.
    with caplog.at_level("WARNING", logger="app.services.import_service"):
        await service._carry_forward_orphaned_protected_metadata(
            leftover_protected=[old_trade],
            protected_ordered_legs={old_trade.id: [removed_leg_id, still_here_leg_id]},
            trades_with_sources=[],
            user_id=uuid.uuid4(),
        )

    service._transfer_protected_trade_metadata.assert_not_called()


@pytest.mark.unit
async def test_carry_forward_returns_early_when_no_candidate_execution_ids() -> None:
    service = _service()
    service._list_executions_for_backfill = AsyncMock()
    service._transfer_protected_trade_metadata = AsyncMock()

    old_trade = MagicMock(id=uuid.uuid4())

    await service._carry_forward_orphaned_protected_metadata(
        leftover_protected=[old_trade],
        protected_ordered_legs={},
        trades_with_sources=[],
        user_id=uuid.uuid4(),
    )

    service._list_executions_for_backfill.assert_not_called()
    service._transfer_protected_trade_metadata.assert_not_called()
