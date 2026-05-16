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
from datetime import UTC, datetime
from decimal import Decimal

from app.models.trade import AssetClass, Direction
from app.schemas.trade import TradeCreate
from app.utils.parsers.aggregator import (
    ExecutionAllocation,
    TradeCreateWithSources,
    aggregate_executions_fifo_with_sources,
)


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
        execution_id=trade.source_execution_id,
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
