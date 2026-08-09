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

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from app.models.trade import AssetClass, Direction
from app.schemas.trade import TradeCreate
from app.utils.parsers.aggregator import (
    aggregate_executions_fifo,
    logical_executions_to_trade_creates,
)


@dataclass
class CorporateActionStub:
    symbol: str
    date: date
    ratio: Decimal
    old_conid: str | None = None
    new_conid: str | None = None


@dataclass
class ExecutionStub:
    id: uuid.UUID
    symbol: str
    conid: str | None
    asset_class: AssetClass | str
    direction: Direction | str
    quantity: Decimal
    price: Decimal
    commission: Decimal
    executed_at: datetime
    pnl: Decimal | None
    multiplier: int
    currency: str | None


def _exec(
    *,
    id: str,
    symbol: str,
    direction: Direction,
    quantity: str,
    price: str,
    executed_at: datetime,
    pnl: str | None,
    conid: str | None,
    multiplier: int = 1,
    currency: str | None = "USD",
) -> ExecutionStub:
    return ExecutionStub(
        id=uuid.uuid5(uuid.NAMESPACE_DNS, id),
        symbol=symbol,
        conid=conid,
        asset_class=AssetClass.EQUITY,
        direction=direction,
        quantity=Decimal(quantity),
        price=Decimal(price),
        commission=Decimal("0"),
        executed_at=executed_at,
        pnl=Decimal(pnl) if pnl is not None else None,
        multiplier=multiplier,
        currency=currency,
    )


def test_logical_rebuild_split_adjust_applies_exactly_once_before_close() -> None:
    open_execution = _exec(
        id="ex-open",
        symbol="SPLT",
        direction=Direction.LONG,
        quantity="100",
        price="10",
        executed_at=datetime(2024, 11, 15, 10, 0, tzinfo=UTC),
        pnl=None,
        conid="600111",
    )
    close_execution = _exec(
        id="ex-close",
        symbol="SPLT",
        direction=Direction.SHORT,
        quantity="10",
        price="80",
        executed_at=datetime(2025, 4, 1, 10, 0, tzinfo=UTC),
        pnl="-200",
        conid="600222",
    )
    split = CorporateActionStub(
        symbol="SPLT",
        date=date(2025, 3, 1),
        ratio=Decimal("0.1"),
        old_conid="600111",
        new_conid="600222",
    )

    execution_trades: list[TradeCreate] = logical_executions_to_trade_creates([open_execution, close_execution])
    result = aggregate_executions_fifo(
        execution_trades,
        corporate_actions=[split],
    )

    closed = [trade for trade in result if trade.closed_at is not None]
    assert len(closed) == 1
    trade = closed[0]
    assert trade.quantity == Decimal("10")
    assert trade.entry_price == Decimal("100")
    assert trade.exit_price == Decimal("80")
    assert trade.pnl == Decimal("-200")


def test_logical_rebuild_preserves_multiplier_for_cross_period_option_like_execution() -> None:
    open_execution = _exec(
        id="opt-open",
        symbol="VST",
        direction=Direction.LONG,
        quantity="1",
        price="2.5",
        executed_at=datetime(2024, 12, 20, 10, 0, tzinfo=UTC),
        pnl=None,
        conid="opt-1",
        multiplier=100,
    )
    close_execution = _exec(
        id="opt-close",
        symbol="VST",
        direction=Direction.SHORT,
        quantity="1",
        price="3.0",
        executed_at=datetime(2025, 1, 15, 10, 0, tzinfo=UTC),
        pnl="50",
        conid="opt-1",
        multiplier=100,
    )

    execution_trades: list[TradeCreate] = logical_executions_to_trade_creates([open_execution, close_execution])
    result = aggregate_executions_fifo(execution_trades)

    closed = [trade for trade in result if trade.closed_at is not None]
    assert len(closed) == 1
    trade = closed[0]
    assert trade.multiplier == 100
    assert trade.pnl == Decimal("50")
