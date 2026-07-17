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
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest

from app.schemas.trade import TradeCreate
from app.schemas.corporate_action import CorporateActionCreateRequest
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
