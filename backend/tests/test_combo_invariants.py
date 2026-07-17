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

"""Unit-level P&L invariants for combo grouping."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest

from app.schemas.trade import TradeCreate
from app.schemas.corporate_action import CorporateActionCreateRequest
from app.models.trade import AssetClass, Direction
from app.utils.parsers.aggregator import (
    ExecutionLike,
    aggregate_executions_fifo,
    build_combo_positions,
    logical_executions_to_trade_creates,
)
from app.utils.parsers.ibkr_xml import IBKRXMLParser


_FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "test_data" / "ibkr" / "combo_positions.xml"


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.00000001"))


def _parse_trade_rows() -> tuple[list[TradeCreate], list[CorporateActionCreateRequest]]:
    parser = IBKRXMLParser()
    raw_rows, corporate_actions = parser.parse_raw(_FIXTURE.read_bytes(), _FIXTURE.name)
    assert parser.warnings == []

    sorted_raw = sorted(raw_rows, key=lambda row: (row.executed_at, row.id))
    trades = logical_executions_to_trade_creates(cast(list[ExecutionLike], sorted_raw))
    for raw, trade in zip(sorted_raw, trades, strict=False):
        trade.broker_order_id = str(raw.raw_data.get("brokerageOrderID") or "") or None
        trade.open_close = raw.open_close
        net_cash_raw = raw.raw_data.get("netCash")
        trade.net_cash = Decimal(str(net_cash_raw)) if net_cash_raw is not None else None
    return trades, corporate_actions


def _yearly_pnl(trades: list[TradeCreate]) -> dict[int, Decimal]:
    yearly: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    for trade in trades:
        if trade.closed_at is None or trade.pnl is None:
            continue
        yearly[trade.closed_at.year] += _quantize(trade.pnl)
    return dict(yearly)


def _closed_pnl_total(trades: list[TradeCreate]) -> Decimal:
    total = Decimal("0")
    for trade in trades:
        if trade.closed_at is None or trade.pnl is None:
            continue
        total += _quantize(trade.pnl)
    return total


@pytest.mark.unit
def test_combo_grouping_preserves_total_pnl() -> None:
    trades, corporate_actions = _parse_trade_rows()

    base_trades = aggregate_executions_fifo(trades, corporate_actions=corporate_actions)
    combo_result = build_combo_positions(trades)
    combo_fifo_trades = aggregate_executions_fifo(
        combo_result.fifo_executions,
        corporate_actions=corporate_actions,
    )
    combo_trades = [row.trade_create for row in combo_result.combo_trades]

    base = _yearly_pnl(base_trades)
    combo = _yearly_pnl([*combo_trades, *combo_fifo_trades])

    assert set(base.keys()) == set(combo.keys())
    for year in base:
        # Compare P&L only: trade count intentionally changes under grouping.
        assert base[year] == combo[year]


@pytest.mark.unit
def test_combo_grouping_changes_trade_count_but_not_pnl() -> None:
    trades, corporate_actions = _parse_trade_rows()

    base_trades = aggregate_executions_fifo(trades, corporate_actions=corporate_actions)
    combo_result = build_combo_positions(trades)
    combo_fifo_trades = aggregate_executions_fifo(
        combo_result.fifo_executions,
        corporate_actions=corporate_actions,
    )
    combo_trades = [row.trade_create for row in combo_result.combo_trades]

    base_yearly = _yearly_pnl(base_trades)
    combo_yearly = _yearly_pnl([*combo_trades, *combo_fifo_trades])

    year = next(iter(base_yearly.keys()))
    assert isinstance(base_yearly[year], Decimal)
    assert base_yearly[year] == combo_yearly[year]
    assert len(base_trades) != len([*combo_trades, *combo_fifo_trades])


@pytest.mark.unit
def test_unmatched_combo_close_contributes_zero_realized_pnl() -> None:
    trades, corporate_actions = _parse_trade_rows()

    anomaly_time = datetime(2026, 7, 14, 10, 0, tzinfo=UTC)
    anomaly_close_a = TradeCreate(
        symbol="QQQ   260731C00712000",
        direction=Direction.SHORT,
        asset_class=AssetClass.OPTION,
        quantity=Decimal("1"),
        entry_price=Decimal("30"),
        opened_at=anomaly_time,
        closed_at=anomaly_time,
        pnl=Decimal("0"),
        commission=Decimal("0"),
        broker_conid="878467678",
        multiplier=100,
        broker_order_id="combo-anomaly-close-1",
        open_close="C",
        net_cash=Decimal("3000"),
    )
    anomaly_close_b = TradeCreate(
        symbol="QQQ   260731C00722000",
        direction=Direction.LONG,
        asset_class=AssetClass.OPTION,
        quantity=Decimal("1"),
        entry_price=Decimal("5"),
        opened_at=anomaly_time,
        closed_at=anomaly_time,
        pnl=Decimal("0"),
        commission=Decimal("0"),
        broker_conid="884162799",
        multiplier=100,
        broker_order_id="combo-anomaly-close-1",
        open_close="C",
        net_cash=Decimal("-500"),
    )

    base_trades = aggregate_executions_fifo(trades, corporate_actions=corporate_actions)
    combo_result = build_combo_positions([*trades, anomaly_close_a, anomaly_close_b])
    combo_fifo_trades = aggregate_executions_fifo(
        combo_result.fifo_executions,
        corporate_actions=corporate_actions,
    )
    combo_trades = [row.trade_create for row in combo_result.combo_trades]

    assert any(
        "combo-anomaly-close-1" in warning for warning in combo_result.warnings
    )

    anomaly_fifo_rows = [
        trade
        for trade in combo_fifo_trades
        if trade.broker_order_id == "combo-anomaly-close-1"
    ]
    assert len(anomaly_fifo_rows) == 2
    assert sum(
        (trade.pnl for trade in anomaly_fifo_rows if trade.pnl is not None),
        Decimal("0"),
    ) == Decimal("0")

    combo_total = _closed_pnl_total([*combo_trades, *combo_fifo_trades])
    base_total = _closed_pnl_total(base_trades)
    assert combo_total == base_total


@pytest.mark.unit
def test_combo_grouping_and_split_coexist_without_pnl_drift() -> None:
    trades, corporate_actions = _parse_trade_rows()

    split_open = TradeCreate(
        symbol="SPLT",
        direction=Direction.LONG,
        asset_class=AssetClass.EQUITY,
        quantity=Decimal("100"),
        entry_price=Decimal("10"),
        opened_at=datetime(2026, 7, 1, 13, 0, tzinfo=UTC),
        pnl=None,
        commission=Decimal("0"),
        broker_conid="600111",
    )
    split_close = TradeCreate(
        symbol="SPLT",
        direction=Direction.SHORT,
        asset_class=AssetClass.EQUITY,
        quantity=Decimal("10"),
        entry_price=Decimal("80"),
        opened_at=datetime(2026, 7, 12, 13, 0, tzinfo=UTC),
        closed_at=datetime(2026, 7, 12, 13, 0, 1, tzinfo=UTC),
        pnl=Decimal("-200"),
        commission=Decimal("0"),
        broker_conid="600222",
    )
    split_ca = CorporateActionCreateRequest(
        symbol="SPLT",
        date=date(2026, 7, 10),
        ratio=Decimal("0.1"),
        old_conid="600111",
        new_conid="600222",
    )

    full_trades = [*trades, split_open, split_close]
    full_corporate_actions = [*corporate_actions, split_ca]

    base_trades = aggregate_executions_fifo(
        full_trades,
        corporate_actions=full_corporate_actions,
    )
    combo_result = build_combo_positions(full_trades)
    combo_fifo_trades = aggregate_executions_fifo(
        combo_result.fifo_executions,
        corporate_actions=full_corporate_actions,
    )
    combo_trades = [row.trade_create for row in combo_result.combo_trades]

    assert _closed_pnl_total(base_trades) == _closed_pnl_total([*combo_trades, *combo_fifo_trades])
