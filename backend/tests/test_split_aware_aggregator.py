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

"""Unit tests for split-aware source tracking in the FIFO aggregator."""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from app.models.trade import AssetClass, Direction
from app.schemas.trade import TradeCreate
from app.utils.parsers.aggregator import (
    ExecutionAllocation,
    TradeCreateWithSources,
    aggregate_executions_fifo_with_sources,
)


@dataclass
class _FakeCorporateAction:
    symbol: str
    date: date
    ratio: Decimal
    old_conid: str | None = None
    new_conid: str | None = None


def _trade(
    *,
    symbol: str,
    direction: Direction,
    quantity: str,
    entry_price: str,
    opened_at: datetime,
    source_execution_id: uuid.UUID,
    pnl: str | None = None,
    commission: str = "0",
) -> TradeCreate:
    return TradeCreate(
        symbol=symbol,
        direction=direction,
        asset_class=AssetClass.EQUITY,
        quantity=Decimal(quantity),
        entry_price=Decimal(entry_price),
        opened_at=opened_at,
        pnl=Decimal(pnl) if pnl is not None else None,
        commission=Decimal(commission),
        source_execution_id=source_execution_id,
    )


def test_execution_allocation_dataclass_creation() -> None:
    execution_id = uuid.uuid4()
    allocation = ExecutionAllocation(
        execution_id=execution_id,
        quantity_used=Decimal("60"),
        commission_used=Decimal("0.60"),
        entry_price=Decimal("100"),
    )

    assert allocation.execution_id == execution_id
    assert allocation.quantity_used == Decimal("60")
    assert allocation.commission_used == Decimal("0.60")
    assert allocation.entry_price == Decimal("100")


def test_trade_create_with_sources_dataclass_creation() -> None:
    trade = _trade(
        symbol="AAPL",
        direction=Direction.LONG,
        quantity="10",
        entry_price="100",
        opened_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        source_execution_id=uuid.uuid4(),
    )
    src = ExecutionAllocation(
        execution_id=trade.source_execution_id or uuid.uuid4(),
        quantity_used=Decimal("10"),
        commission_used=Decimal("0"),
        entry_price=Decimal("100"),
    )

    wrapped = TradeCreateWithSources(trade_create=trade, source_executions=[src])
    assert wrapped.trade_create.symbol == "AAPL"
    assert len(wrapped.source_executions) == 1
    assert wrapped.created_trade is None


def test_aggregate_with_sources_tracks_split_from_single_entry() -> None:
    entry_exec_id = uuid.uuid4()
    close1_exec_id = uuid.uuid4()
    close2_exec_id = uuid.uuid4()

    trades = [
        _trade(
            symbol="SPLIT_A",
            direction=Direction.LONG,
            quantity="100",
            entry_price="100",
            opened_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
            source_execution_id=entry_exec_id,
            commission="1.0",
        ),
        _trade(
            symbol="SPLIT_A",
            direction=Direction.SHORT,
            quantity="60",
            entry_price="110",
            opened_at=datetime(2026, 3, 2, 10, 0, tzinfo=UTC),
            source_execution_id=close1_exec_id,
            pnl="600",
            commission="0",
        ),
        _trade(
            symbol="SPLIT_A",
            direction=Direction.SHORT,
            quantity="40",
            entry_price="105",
            opened_at=datetime(2026, 3, 3, 10, 0, tzinfo=UTC),
            source_execution_id=close2_exec_id,
            pnl="200",
            commission="0",
        ),
    ]

    result = aggregate_executions_fifo_with_sources(trades)

    assert len(result) == 2
    # Each closed trade now has 2 allocations: one for the entry execution and
    # one for the closing execution.
    assert all(len(item.source_executions) == 2 for item in result)
    # First allocation is always the entry execution.
    entry_ids = {item.source_executions[0].execution_id for item in result}
    assert entry_ids == {entry_exec_id}
    # Closing execution IDs are the two close legs.
    closing_ids = {item.source_executions[1].execution_id for item in result}
    assert closing_ids == {close1_exec_id, close2_exec_id}
    assert {item.source_executions[0].quantity_used for item in result} == {
        Decimal("60"),
        Decimal("40"),
    }


def test_aggregate_with_sources_quantity_conservation_for_split() -> None:
    entry_exec_id = uuid.uuid4()
    trades = [
        _trade(
            symbol="SPLIT_B",
            direction=Direction.LONG,
            quantity="100",
            entry_price="200",
            opened_at=datetime(2026, 3, 4, 10, 0, tzinfo=UTC),
            source_execution_id=entry_exec_id,
            commission="1.0",
        ),
        _trade(
            symbol="SPLIT_B",
            direction=Direction.SHORT,
            quantity="30",
            entry_price="210",
            opened_at=datetime(2026, 3, 5, 10, 0, tzinfo=UTC),
            source_execution_id=uuid.uuid4(),
            pnl="300",
            commission="0",
        ),
        _trade(
            symbol="SPLIT_B",
            direction=Direction.SHORT,
            quantity="30",
            entry_price="212",
            opened_at=datetime(2026, 3, 6, 10, 0, tzinfo=UTC),
            source_execution_id=uuid.uuid4(),
            pnl="360",
            commission="0",
        ),
        _trade(
            symbol="SPLIT_B",
            direction=Direction.SHORT,
            quantity="40",
            entry_price="205",
            opened_at=datetime(2026, 3, 7, 10, 0, tzinfo=UTC),
            source_execution_id=uuid.uuid4(),
            pnl="200",
            commission="0",
        ),
    ]

    result = aggregate_executions_fifo_with_sources(trades)
    total_allocated = sum(
        item.source_executions[0].quantity_used
        for item in result
        if (
            item.source_executions
            and item.source_executions[0].execution_id == entry_exec_id
        )
    )

    assert total_allocated == Decimal("100")


def test_aggregate_with_sources_commission_allocation_for_split() -> None:
    entry_exec_id = uuid.uuid4()
    trades = [
        _trade(
            symbol="COMM_TEST",
            direction=Direction.LONG,
            quantity="100",
            entry_price="100",
            opened_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
            source_execution_id=entry_exec_id,
            commission="1.0",
        ),
        _trade(
            symbol="COMM_TEST",
            direction=Direction.SHORT,
            quantity="60",
            entry_price="110",
            opened_at=datetime(2026, 3, 2, 10, 0, tzinfo=UTC),
            source_execution_id=uuid.uuid4(),
            pnl="600",
            commission="0",
        ),
        _trade(
            symbol="COMM_TEST",
            direction=Direction.SHORT,
            quantity="40",
            entry_price="105",
            opened_at=datetime(2026, 3, 3, 10, 0, tzinfo=UTC),
            source_execution_id=uuid.uuid4(),
            pnl="200",
            commission="0",
        ),
    ]

    result = aggregate_executions_fifo_with_sources(trades)
    total_allocated_commission = sum(
        item.source_executions[0].commission_used
        for item in result
        if (
            item.source_executions
            and item.source_executions[0].execution_id == entry_exec_id
        )
    )

    assert total_allocated_commission == Decimal("1.0")


def test_aggregate_with_sources_single_allocation_no_split() -> None:
    entry_exec_id = uuid.uuid4()
    close_exec_id = uuid.uuid4()
    trades = [
        _trade(
            symbol="ONE",
            direction=Direction.LONG,
            quantity="10",
            entry_price="100",
            opened_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
            source_execution_id=entry_exec_id,
        ),
        _trade(
            symbol="ONE",
            direction=Direction.SHORT,
            quantity="10",
            entry_price="101",
            opened_at=datetime(2026, 3, 2, 10, 0, tzinfo=UTC),
            source_execution_id=close_exec_id,
            pnl="10",
        ),
    ]

    result = aggregate_executions_fifo_with_sources(trades)
    assert len(result) == 1
    # Closed trade has 2 allocations: entry + exit.
    assert len(result[0].source_executions) == 2
    assert result[0].source_executions[0].execution_id == entry_exec_id
    assert result[0].source_executions[1].execution_id == close_exec_id


def test_execution_allocation_has_slots() -> None:
    """ExecutionAllocation should use slots for reduced per-instance memory."""
    assert hasattr(ExecutionAllocation, "__slots__")


def test_trade_create_with_sources_has_slots() -> None:
    """TradeCreateWithSources should use slots for reduced per-instance memory."""
    assert hasattr(TradeCreateWithSources, "__slots__")


def test_protected_contract_suppresses_orphan_sentinel_trade() -> None:
    """Closing-only execution on a protected contract should not create a sentinel lot."""
    close_exec_id = uuid.uuid4()
    trades = [
        _trade(
            symbol="PROT_ORPH",
            direction=Direction.SHORT,
            quantity="1",
            entry_price="150",
            opened_at=datetime(2026, 3, 2, 10, 0, tzinfo=UTC),
            source_execution_id=close_exec_id,
            pnl="10",
        ),
    ]

    result = aggregate_executions_fifo_with_sources(
        trades,
        protected_contracts={("PROT_ORPH", None)},
    )

    assert result == []


def test_open_protected_seed_lot_closes_without_protected_suppression() -> None:
    open_exec_id = uuid.uuid4()
    close_exec_id = uuid.uuid4()
    trades = [
        _trade(
            symbol="PROT_OPEN",
            direction=Direction.LONG,
            quantity="1",
            entry_price="100",
            opened_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
            source_execution_id=open_exec_id,
        ).model_copy(update={"db_trade_id": uuid.uuid4(), "open_close": "O"}),
        _trade(
            symbol="PROT_OPEN",
            direction=Direction.SHORT,
            quantity="1",
            entry_price="110",
            opened_at=datetime(2026, 3, 2, 10, 0, tzinfo=UTC),
            source_execution_id=close_exec_id,
            pnl="10",
        ),
    ]

    result = aggregate_executions_fifo_with_sources(
        trades,
        protected_contracts={("OTHER_SYMBOL", None)},
    )

    assert len(result) == 1
    closed_trade = result[0].trade_create
    assert closed_trade.entry_price == Decimal("100")
    assert closed_trade.exit_price == Decimal("110")
    assert closed_trade.closed_at is not None


def test_opening_seed_plus_closing_leg_still_closes_when_contract_marked_protected() -> None:
    open_exec_id = uuid.uuid4()
    close_exec_id = uuid.uuid4()
    contract = ("PROT_SEED", "3001")
    trades = [
        _trade(
            symbol="PROT_SEED",
            direction=Direction.LONG,
            quantity="1",
            entry_price="100",
            opened_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
            source_execution_id=open_exec_id,
        ).model_copy(update={"db_trade_id": uuid.uuid4(), "open_close": "O"}),
        _trade(
            symbol="PROT_SEED",
            direction=Direction.SHORT,
            quantity="1",
            entry_price="120",
            opened_at=datetime(2026, 3, 2, 10, 0, tzinfo=UTC),
            source_execution_id=close_exec_id,
            pnl="20",
        ),
    ]

    result = aggregate_executions_fifo_with_sources(
        trades,
        protected_contracts={contract},
    )

    assert len(result) == 1
    assert result[0].trade_create.entry_price == Decimal("100")
    assert result[0].trade_create.exit_price == Decimal("120")


def test_non_protected_contract_still_creates_orphan_sentinel_trade() -> None:
    """Closing-only execution on an unrelated contract keeps prior orphan behavior."""
    close_exec_id = uuid.uuid4()
    trades = [
        _trade(
            symbol="NONPROT_ORPH",
            direction=Direction.SHORT,
            quantity="1",
            entry_price="150",
            opened_at=datetime(2026, 3, 2, 10, 0, tzinfo=UTC),
            source_execution_id=close_exec_id,
            pnl="10",
        ),
    ]

    result = aggregate_executions_fifo_with_sources(
        trades,
        protected_contracts={("OTHER_SYMBOL", None)},
    )

    assert len(result) == 1
    assert result[0].trade_create.entry_price == Decimal("0.001")


def test_seeded_partial_close_keeps_remaining_open_quantity_and_links_both_legs() -> None:
    open_exec_id = uuid.uuid4()
    close_exec_id = uuid.uuid4()

    trades = [
        _trade(
            symbol="PROT_PART",
            direction=Direction.LONG,
            quantity="10",
            entry_price="100",
            opened_at=datetime(2026, 4, 1, 10, 0, tzinfo=UTC),
            source_execution_id=open_exec_id,
        ).model_copy(update={"db_trade_id": uuid.uuid4(), "open_close": "O"}),
        _trade(
            symbol="PROT_PART",
            direction=Direction.SHORT,
            quantity="4",
            entry_price="110",
            opened_at=datetime(2026, 4, 2, 10, 0, tzinfo=UTC),
            source_execution_id=close_exec_id,
            pnl="40",
        ),
    ]

    result = aggregate_executions_fifo_with_sources(trades)

    closed = [row for row in result if row.trade_create.closed_at is not None]
    open_rows = [row for row in result if row.trade_create.closed_at is None]
    assert len(closed) == 1
    assert len(open_rows) == 1

    assert closed[0].trade_create.quantity == Decimal("4")
    assert {alloc.execution_id for alloc in closed[0].source_executions} == {
        open_exec_id,
        close_exec_id,
    }

    assert open_rows[0].trade_create.quantity == Decimal("6")
    assert len(open_rows[0].source_executions) == 1
    assert open_rows[0].source_executions[0].execution_id == open_exec_id


def test_seeded_over_close_matches_seed_and_keeps_orphan_remainder_behavior() -> None:
    open_exec_id = uuid.uuid4()
    close_exec_id = uuid.uuid4()

    trades = [
        _trade(
            symbol="PROT_OVER",
            direction=Direction.LONG,
            quantity="3",
            entry_price="100",
            opened_at=datetime(2026, 4, 1, 10, 0, tzinfo=UTC),
            source_execution_id=open_exec_id,
        ).model_copy(update={"db_trade_id": uuid.uuid4(), "open_close": "O"}),
        _trade(
            symbol="PROT_OVER",
            direction=Direction.SHORT,
            quantity="5",
            entry_price="115",
            opened_at=datetime(2026, 4, 2, 10, 0, tzinfo=UTC),
            source_execution_id=close_exec_id,
            pnl="75",
        ),
    ]

    result = aggregate_executions_fifo_with_sources(trades)

    closed = [row.trade_create for row in result if row.trade_create.entry_price != Decimal("0.001")]
    sentinel = [row.trade_create for row in result if row.trade_create.entry_price == Decimal("0.001")]

    assert len(closed) == 1
    assert closed[0].quantity == Decimal("3")
    assert len(sentinel) == 1
    assert sentinel[0].quantity == Decimal("2")


def test_split_adjusted_seed_matches_close_after_corporate_action() -> None:
    open_exec_id = uuid.uuid4()
    close_exec_id = uuid.uuid4()
    conid = "900100"

    trades = [
        _trade(
            symbol="PROT_SPLIT",
            direction=Direction.LONG,
            quantity="10",
            entry_price="100",
            opened_at=datetime(2026, 4, 1, 10, 0, tzinfo=UTC),
            source_execution_id=open_exec_id,
        ).model_copy(update={"db_trade_id": uuid.uuid4(), "open_close": "O", "broker_conid": conid}),
        _trade(
            symbol="PROT_SPLIT",
            direction=Direction.SHORT,
            quantity="20",
            entry_price="60",
            opened_at=datetime(2026, 4, 3, 10, 0, tzinfo=UTC),
            source_execution_id=close_exec_id,
            pnl="200",
        ).model_copy(update={"broker_conid": conid}),
    ]

    result = aggregate_executions_fifo_with_sources(
        trades,
        corporate_actions=[
            _FakeCorporateAction(
                symbol="PROT_SPLIT",
                date=date(2026, 4, 2),
                ratio=Decimal("2"),
            )
        ],
    )

    assert len(result) == 1
    trade = result[0].trade_create
    assert trade.quantity == Decimal("20")
    assert trade.entry_price == Decimal("50")
    assert trade.exit_price == Decimal("60")
    opening_alloc = next(
        allocation
        for allocation in result[0].source_executions
        if allocation.execution_id == open_exec_id
    )
    assert opening_alloc.quantity_used == Decimal("10")
