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

"""Unit tests for combo position building from enriched execution legs."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest

from app.models.trade import AssetClass, Direction
from app.schemas.trade import TradeCreate
from app.utils.parsers.aggregator import (
    ExecutionLike,
    build_combo_positions,
    logical_executions_to_trade_creates,
)
from app.utils.parsers.ibkr_xml import IBKRXMLParser

_FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "test_data" / "ibkr" / "combo_positions.xml"


def _enriched_trade_rows() -> list[TradeCreate]:
    parser = IBKRXMLParser()
    raw_rows, _ = parser.parse_raw(_FIXTURE.read_bytes(), _FIXTURE.name)
    assert parser.warnings == []

    trade_rows = logical_executions_to_trade_creates(cast(list[ExecutionLike], raw_rows))
    for raw, trade in zip(raw_rows, trade_rows, strict=False):
        trade.broker_order_id = str(raw.raw_data.get("brokerageOrderID") or "") or None
        trade.open_close = raw.open_close
        net_cash_raw = raw.raw_data.get("netCash")
        trade.net_cash = Decimal(str(net_cash_raw)) if net_cash_raw is not None else None
    return trade_rows


@pytest.mark.unit
def test_build_combo_positions_closed_and_direction_from_fixture() -> None:
    rows = _enriched_trade_rows()
    source_by_id = {row.source_execution_id: row for row in rows}
    result = build_combo_positions(rows)

    assert result.fifo_executions == []
    assert result.warnings == []
    assert len(result.combo_trades) == 4  # QQQ + META pair 1 + META pair 2 + XSP

    qqq_combo = next((row for row in result.combo_trades if row.trade_create.symbol == "QQQ"), None)
    assert qqq_combo is not None
    assert qqq_combo.trade_create.is_combo is True
    assert qqq_combo.trade_create.closed_at is not None
    assert qqq_combo.trade_create.direction == Direction.LONG
    assert qqq_combo.trade_create.pnl == Decimal("77")
    assert len(qqq_combo.source_executions) == 4

    # Ensure at least one credit spread resolves to SHORT direction.
    assert any(row.trade_create.direction == Direction.SHORT for row in result.combo_trades)

    for combo in result.combo_trades:
        source_rows = [source_by_id[src.execution_id] for src in combo.source_executions]
        expected_commission = sum((row.commission or Decimal("0")) for row in source_rows)
        assert combo.trade_create.commission == expected_commission

        if combo.trade_create.closed_at is not None:
            expected_pnl = sum(
                (row.pnl or Decimal("0"))
                for row in source_rows
                if row.open_close == "C"
            )
            assert combo.trade_create.pnl == expected_pnl


@pytest.mark.unit
def test_build_combo_positions_open_only_combo() -> None:
    rows = _enriched_trade_rows()[:2]  # QQQ opening order only
    result = build_combo_positions(rows)

    assert len(result.combo_trades) == 1
    combo = result.combo_trades[0].trade_create
    assert combo.symbol == "QQQ"
    assert combo.closed_at is None
    assert combo.pnl is None
    assert combo.direction == Direction.LONG


@pytest.mark.unit
def test_build_combo_positions_unmatched_close_warns_and_keeps_open() -> None:
    open_leg_a = TradeCreate(
        symbol="TEST",
        direction=Direction.LONG,
        asset_class=AssetClass.OPTION,
        quantity=Decimal("1"),
        entry_price=Decimal("10"),
        commission=Decimal("1"),
        opened_at=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        broker_conid="A",
        source_execution_id="open-a",
        broker_order_id="order-open",
        open_close="O",
        net_cash=Decimal("-1000"),
    )
    open_leg_b = TradeCreate(
        symbol="TEST",
        direction=Direction.SHORT,
        asset_class=AssetClass.OPTION,
        quantity=Decimal("1"),
        entry_price=Decimal("8"),
        commission=Decimal("1"),
        opened_at=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        broker_conid="B",
        source_execution_id="open-b",
        broker_order_id="order-open",
        open_close="O",
        net_cash=Decimal("800"),
    )
    close_leg_a = TradeCreate(
        symbol="TEST",
        direction=Direction.SHORT,
        asset_class=AssetClass.OPTION,
        quantity=Decimal("1"),
        entry_price=Decimal("11"),
        commission=Decimal("1"),
        opened_at=datetime(2026, 1, 2, 10, 0, tzinfo=UTC),
        broker_conid="A",
        source_execution_id="close-a",
        broker_order_id="order-close",
        open_close="C",
        net_cash=Decimal("1100"),
        pnl=Decimal("100"),
    )
    close_leg_c = TradeCreate(
        symbol="TEST",
        direction=Direction.LONG,
        asset_class=AssetClass.OPTION,
        quantity=Decimal("1"),
        entry_price=Decimal("3"),
        commission=Decimal("1"),
        opened_at=datetime(2026, 1, 2, 10, 0, tzinfo=UTC),
        broker_conid="C",
        source_execution_id="close-c",
        broker_order_id="order-close",
        open_close="C",
        net_cash=Decimal("-300"),
        pnl=Decimal("-50"),
    )

    result = build_combo_positions([open_leg_a, open_leg_b, close_leg_a, close_leg_c])

    assert len(result.warnings) == 1
    assert "order-close" in result.warnings[0]
    assert len(result.combo_trades) == 1


@pytest.mark.unit
def test_build_combo_positions_unmatched_close_suppressed_for_protected_contracts() -> None:
    """A close order whose missing open belongs to a closed protected trade must not warn.

    The opening legs were excluded from the aggregation input upstream (they
    belong to an isolated closed metadata-protected trade), so the closing
    order legitimately has no open counterpart here. That is expected, not
    an anomaly — the warning is demoted to a debug log instead.
    """
    close_leg_a = TradeCreate(
        symbol="TEST",
        direction=Direction.SHORT,
        asset_class=AssetClass.OPTION,
        quantity=Decimal("1"),
        entry_price=Decimal("11"),
        commission=Decimal("1"),
        opened_at=datetime(2026, 1, 2, 10, 0, tzinfo=UTC),
        broker_conid="A",
        source_execution_id="close-a",
        broker_order_id="order-close",
        open_close="C",
        net_cash=Decimal("1100"),
        pnl=Decimal("100"),
    )
    close_leg_b = TradeCreate(
        symbol="TEST",
        direction=Direction.LONG,
        asset_class=AssetClass.OPTION,
        quantity=Decimal("1"),
        entry_price=Decimal("8"),
        commission=Decimal("1"),
        opened_at=datetime(2026, 1, 2, 10, 0, tzinfo=UTC),
        broker_conid="B",
        source_execution_id="close-b",
        broker_order_id="order-close",
        open_close="C",
        net_cash=Decimal("-800"),
        pnl=Decimal("-50"),
    )

    result = build_combo_positions(
        [close_leg_a, close_leg_b],
        protected_contracts={("TEST", "A"), ("TEST", "B")},
    )

    assert result.warnings == []
    assert result.combo_trades == []


@pytest.mark.unit
def test_build_combo_positions_unmatched_close_still_warns_when_not_fully_protected() -> None:
    """Only warning suppression requires EVERY leg's contract to be protected.

    Same fixture as ``test_build_combo_positions_unmatched_close_warns_and_keeps_open``:
    the close order's contract set ("A", "C") does not match the open
    position's ("A", "B"). Only "A" is protected — "C" is not — so this
    remains a genuine anomaly and must still warn.
    """
    open_leg_a = TradeCreate(
        symbol="TEST",
        direction=Direction.LONG,
        asset_class=AssetClass.OPTION,
        quantity=Decimal("1"),
        entry_price=Decimal("10"),
        commission=Decimal("1"),
        opened_at=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        broker_conid="A",
        source_execution_id="open-a",
        broker_order_id="order-open",
        open_close="O",
        net_cash=Decimal("-1000"),
    )
    open_leg_b = TradeCreate(
        symbol="TEST",
        direction=Direction.SHORT,
        asset_class=AssetClass.OPTION,
        quantity=Decimal("1"),
        entry_price=Decimal("8"),
        commission=Decimal("1"),
        opened_at=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        broker_conid="B",
        source_execution_id="open-b",
        broker_order_id="order-open",
        open_close="O",
        net_cash=Decimal("800"),
    )
    close_leg_a = TradeCreate(
        symbol="TEST",
        direction=Direction.SHORT,
        asset_class=AssetClass.OPTION,
        quantity=Decimal("1"),
        entry_price=Decimal("11"),
        commission=Decimal("1"),
        opened_at=datetime(2026, 1, 2, 10, 0, tzinfo=UTC),
        broker_conid="A",
        source_execution_id="close-a",
        broker_order_id="order-close",
        open_close="C",
        net_cash=Decimal("1100"),
        pnl=Decimal("100"),
    )
    close_leg_c = TradeCreate(
        symbol="TEST",
        direction=Direction.LONG,
        asset_class=AssetClass.OPTION,
        quantity=Decimal("1"),
        entry_price=Decimal("3"),
        commission=Decimal("1"),
        opened_at=datetime(2026, 1, 2, 10, 0, tzinfo=UTC),
        broker_conid="C",
        source_execution_id="close-c",
        broker_order_id="order-close",
        open_close="C",
        net_cash=Decimal("-300"),
        pnl=Decimal("-50"),
    )

    result = build_combo_positions(
        [open_leg_a, open_leg_b, close_leg_a, close_leg_c],
        protected_contracts={("TEST", "A")},
    )

    assert len(result.warnings) == 1
    assert "order-close" in result.warnings[0]
    assert len(result.combo_trades) == 1


@pytest.mark.unit
def test_build_combo_positions_two_opens_split_close_produces_two_trades() -> None:
    """Real-world META scenario: two separate opening orders build the same
    spread (620C/640C) at different prices, then a single closing order
    closes the combined quantity in one broker order.

    This must resolve to TWO separate closed combo trades (FIFO-matched, each
    getting a proportional slice of the closing legs) — NOT one merged trade.
    Each opening order represents its own distinct round trip (e.g. the user
    scaled in twice, by accident or otherwise); a shared closing order does not
    retroactively make them a single trade. Total P&L across both resulting
    trades must equal the sum of the broker-reported closing leg P&L exactly
    (see memory: "Combo grouping preserves total P&L").
    """
    open_1_a = TradeCreate(
        symbol="META",
        direction=Direction.SHORT,
        asset_class=AssetClass.OPTION,
        quantity=Decimal("1"),
        entry_price=Decimal("63.42"),
        commission=Decimal("1"),
        opened_at=datetime(2026, 7, 13, 9, 30, tzinfo=UTC),
        broker_conid="620C",
        source_execution_id="open1-620",
        broker_order_id="order-open-1",
        open_close="O",
        net_cash=Decimal("6340"),
    )
    open_1_b = TradeCreate(
        symbol="META",
        direction=Direction.LONG,
        asset_class=AssetClass.OPTION,
        quantity=Decimal("1"),
        entry_price=Decimal("50.97"),
        commission=Decimal("1"),
        opened_at=datetime(2026, 7, 13, 9, 30, tzinfo=UTC),
        broker_conid="640C",
        source_execution_id="open1-640",
        broker_order_id="order-open-1",
        open_close="O",
        net_cash=Decimal("-5098"),
    )
    open_2_a = TradeCreate(
        symbol="META",
        direction=Direction.SHORT,
        asset_class=AssetClass.OPTION,
        quantity=Decimal("1"),
        entry_price=Decimal("63.03"),
        commission=Decimal("1"),
        opened_at=datetime(2026, 7, 13, 9, 50, tzinfo=UTC),
        broker_conid="620C",
        source_execution_id="open2-620",
        broker_order_id="order-open-2",
        open_close="O",
        net_cash=Decimal("6300"),
    )
    open_2_b = TradeCreate(
        symbol="META",
        direction=Direction.LONG,
        asset_class=AssetClass.OPTION,
        quantity=Decimal("1"),
        entry_price=Decimal("50.48"),
        commission=Decimal("1"),
        opened_at=datetime(2026, 7, 13, 9, 50, tzinfo=UTC),
        broker_conid="640C",
        source_execution_id="open2-640",
        broker_order_id="order-open-2",
        open_close="O",
        net_cash=Decimal("-5048"),
    )
    close_a = TradeCreate(
        symbol="META",
        direction=Direction.LONG,
        asset_class=AssetClass.OPTION,
        quantity=Decimal("2"),
        entry_price=Decimal("63.03"),
        commission=Decimal("1"),
        opened_at=datetime(2026, 7, 13, 9, 57, tzinfo=UTC),
        broker_conid="620C",
        source_execution_id="close-620",
        broker_order_id="order-close",
        open_close="C",
        net_cash=Decimal("-12607"),
        pnl=Decimal("87.27"),
    )
    close_b = TradeCreate(
        symbol="META",
        direction=Direction.SHORT,
        asset_class=AssetClass.OPTION,
        quantity=Decimal("2"),
        entry_price=Decimal("50.48"),
        commission=Decimal("1"),
        opened_at=datetime(2026, 7, 13, 9, 57, tzinfo=UTC),
        broker_conid="640C",
        source_execution_id="close-640",
        broker_order_id="order-close",
        open_close="C",
        net_cash=Decimal("10094"),
        pnl=Decimal("-159.67"),
    )

    result = build_combo_positions([open_1_a, open_1_b, open_2_a, open_2_b, close_a, close_b])

    assert result.warnings == []
    assert len(result.combo_trades) == 2

    trades = sorted(result.combo_trades, key=lambda row: row.trade_create.opened_at)
    first, second = trades[0].trade_create, trades[1].trade_create

    # Both round trips are individually closed (FIFO-matched, oldest first).
    assert first.opened_at == datetime(2026, 7, 13, 9, 30, tzinfo=UTC)
    assert second.opened_at == datetime(2026, 7, 13, 9, 50, tzinfo=UTC)
    assert first.closed_at is not None
    assert second.closed_at is not None

    # Total P&L is conserved exactly (each closing leg's P&L is split
    # proportionally by matched quantity across the two open positions).
    assert first.pnl is not None
    assert second.pnl is not None
    assert first.pnl + second.pnl == Decimal("87.27") + Decimal("-159.67")

    # Total commission is conserved exactly (4 opening legs @ 1 + 2 closing
    # legs @ 1, split proportionally across the two trades).
    assert first.commission + second.commission == Decimal("6")

    # Each trade carries its own 2 opening legs + proportional slices of the
    # 2 closing legs (4 source executions each; the two closing execution IDs
    # are shared across both trades since they were split).
    assert len(trades[0].source_executions) == 4
    assert len(trades[1].source_executions) == 4
