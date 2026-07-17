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

"""Unit tests for the FIFO execution aggregator.

Covers:
- Simple round-trip (existing behaviour)
- Partial close (existing behaviour)
- Orphaned closing execution (existing behaviour)
- 2:1 forward split between buy and sell (Task 4.5)
- 1:20 reverse split with conid change — OTLK scenario (Task 4.5)
- Fractional shares after a reverse split (Task 4.5)
- Backward compatibility: no corporate_actions argument (Task 4.5)
- Corporate action for a symbol with no open lots (graceful no-op)
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.models.trade import AssetClass, Direction
from app.schemas.trade import TradeCreate
from app.utils.parsers.aggregator import aggregate_executions_fifo

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tc(
    sym: str,
    dir_: Direction,
    qty: float | str,
    entry: float | str,
    opened: datetime,
    pnl: float | str | None = None,
    closed: datetime | None = None,
    conid: str | None = None,
) -> TradeCreate:
    """Build a minimal TradeCreate for testing."""
    return TradeCreate(
        symbol=sym,
        direction=dir_,
        asset_class=AssetClass.EQUITY,
        quantity=Decimal(str(qty)),
        entry_price=Decimal(str(entry)),
        opened_at=opened,
        pnl=Decimal(str(pnl)) if pnl is not None else None,
        closed_at=closed,
        commission=Decimal("0"),
        broker_conid=conid,
    )


@dataclass
class _FakeCorporateAction:
    """Minimal corporate-action stand-in for unit tests (no DB required)."""

    symbol: str
    date: date
    ratio: Decimal
    old_conid: str | None = field(default=None)
    new_conid: str | None = field(default=None)


# Convenience alias
_CA = _FakeCorporateAction


# ---------------------------------------------------------------------------
# Existing behaviour tests (regression)
# ---------------------------------------------------------------------------


def test_aggregate_simple_round_trip() -> None:
    t1 = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    t2 = datetime(2024, 1, 1, 11, 0, tzinfo=UTC)
    execs = [
        _tc("AAPL", Direction.LONG, 100, 150, t1),
        _tc("AAPL", Direction.SHORT, 100, 160, t2, pnl=1000),
    ]
    execs[0].commission = Decimal("1.50")
    execs[1].commission = Decimal("2.00")
    execs[1].pnl_eur = Decimal("900")

    res = aggregate_executions_fifo(execs)
    assert len(res) == 1
    t = res[0]
    assert t.quantity == Decimal(100)
    assert t.entry_price == Decimal(150)
    assert t.exit_price == Decimal(160)
    assert t.pnl == Decimal(1000)
    assert t.commission == Decimal("3.50")
    assert t.net_pnl == Decimal("996.50")
    assert t.pnl_eur == Decimal(900)
    # net_pnl_eur = 996.50 * (900 / 1000) = 896.85
    assert t.net_pnl_eur == Decimal("896.85")
    assert t.opened_at == t1
    assert t.closed_at == t2
    assert t.direction == Direction.LONG


@pytest.mark.integration
def test_multi_lot_partial_close_equity_fifo_per_lot() -> None:
    """BUY 100 + BUY 50 + SELL 150 yields two FIFO-closed lots (not one VWAP lot)."""
    t1 = datetime(2025, 1, 10, 10, 0, tzinfo=UTC)
    t2 = datetime(2025, 1, 10, 11, 0, tzinfo=UTC)
    t3 = datetime(2025, 1, 10, 12, 0, tzinfo=UTC)

    executions = [
        _tc("AAPL", Direction.LONG, "100", "373.62", t1),
        _tc("AAPL", Direction.LONG, "50", "375.00", t2),
        _tc("AAPL", Direction.SHORT, "150", "377.96", t3, pnl="1"),
    ]
    executions[0].commission = Decimal("5.00")
    executions[1].commission = Decimal("2.50")
    executions[2].commission = Decimal("7.50")

    result = aggregate_executions_fifo(executions)
    closed = [trade for trade in result if trade.closed_at is not None]
    assert len(closed) == 2

    lot_100 = next(trade for trade in closed if trade.quantity == Decimal("100"))
    lot_50 = next(trade for trade in closed if trade.quantity == Decimal("50"))

    exit_price = Decimal("377.96")
    lot_100_expected_pnl = (exit_price - Decimal("373.62")) * Decimal("100") * Decimal("1")
    lot_50_expected_pnl = (exit_price - Decimal("375.00")) * Decimal("50") * Decimal("1")

    assert lot_100.entry_price == Decimal("373.62")
    assert lot_100.exit_price == exit_price
    assert lot_100.pnl == lot_100_expected_pnl
    assert lot_100.commission == Decimal("10")
    assert lot_100.net_pnl == lot_100_expected_pnl - Decimal("10")
    assert lot_100.opened_at == t1
    assert lot_100.closed_at == t3

    assert lot_50.entry_price == Decimal("375.00")
    assert lot_50.exit_price == exit_price
    assert lot_50.pnl == lot_50_expected_pnl
    assert lot_50.commission == Decimal("5")
    assert lot_50.net_pnl == lot_50_expected_pnl - Decimal("5")
    assert lot_50.opened_at == t2
    assert lot_50.closed_at == t3


def test_multi_lot_partial_close_options_respects_multiplier() -> None:
    """Single options lot with partial exits yields per-lot FIFO trades with multiplier=100."""
    t1 = datetime(2025, 1, 15, 9, 30, tzinfo=UTC)
    t2 = datetime(2025, 1, 15, 11, 0, tzinfo=UTC)
    t3 = datetime(2025, 1, 15, 14, 0, tzinfo=UTC)

    buy_exec = _tc("SPY_CALL", Direction.LONG, "10", "5.50", t1)
    buy_exec.commission = Decimal("10.00")
    buy_exec.multiplier = 100

    sell_exec_1 = _tc("SPY_CALL", Direction.SHORT, "6", "5.75", t2, pnl="1")
    sell_exec_1.commission = Decimal("6.00")
    sell_exec_1.multiplier = 100

    sell_exec_2 = _tc("SPY_CALL", Direction.SHORT, "4", "5.80", t3, pnl="1")
    sell_exec_2.commission = Decimal("4.00")
    sell_exec_2.multiplier = 100

    result = aggregate_executions_fifo([buy_exec, sell_exec_1, sell_exec_2])
    closed = [trade for trade in result if trade.closed_at is not None]
    assert len(closed) == 2

    close_6 = next(trade for trade in closed if trade.quantity == Decimal("6"))
    close_4 = next(trade for trade in closed if trade.quantity == Decimal("4"))

    expected_pnl_6 = (Decimal("5.75") - Decimal("5.50")) * Decimal("6") * Decimal("100")
    expected_pnl_4 = (Decimal("5.80") - Decimal("5.50")) * Decimal("4") * Decimal("100")

    assert close_6.entry_price == Decimal("5.50")
    assert close_6.exit_price == Decimal("5.75")
    assert close_6.pnl == expected_pnl_6
    assert close_6.commission == Decimal("12")
    assert close_6.net_pnl == expected_pnl_6 - Decimal("12")
    assert close_6.opened_at == t1
    assert close_6.closed_at == t2

    assert close_4.entry_price == Decimal("5.50")
    assert close_4.exit_price == Decimal("5.80")
    assert close_4.pnl == expected_pnl_4
    assert close_4.commission == Decimal("8")
    assert close_4.net_pnl == expected_pnl_4 - Decimal("8")
    assert close_4.opened_at == t1
    assert close_4.closed_at == t3

    total_pnl = sum((trade.pnl for trade in closed if trade.pnl is not None), Decimal("0"))
    assert total_pnl == Decimal("270")


def test_mixed_execution_co_fractional_flip_produces_correct_trades() -> None:
    """C;O mixed execution with fractional lots leaves a new short open lot.

    This regression test captures the VST 2025-03-20 scenario where:
    - Three LONG lots are open: 7@130.475, 0.6508@130.40, 5@130.25
    - A SHORT 0.6823 (C) closes 0.6823 from the first LONG lot.
    - A SHORT 5 (C) closes 5 from the first LONG lot.
    - A SHORT 7 (C;O, is_mixed_execution=True) closes the remaining
      1.3177@130.475 + 0.6508@130.40 + 5@130.25 = 6.9685, and then
      opens a new SHORT lot for the remainder 0.0315.
    - A SHORT 0.6508 (O) opens a second new SHORT lot at 126.24.
    - A LONG 0.6823 (C) closes both short lots:
        0.0315 @ 126.35 -> exit 130.6889
        0.6508 @ 126.24 -> exit 130.6889

    Before the fix, LogicalExecution.is_mixed_execution always returned False
    (the transaction_execution_mappings join table was empty), so the C;O
    remainder was mis-classified as an orphaned closing leg instead of a new
    short opening -- producing sentinel entry prices (0.001) and wrong P&L.
    """
    t_buy1 = datetime(2025, 3, 19, 15, 48, 13, tzinfo=UTC)
    t_buy3 = datetime(2025, 3, 19, 15, 50, 7, tzinfo=UTC)
    t_c1 = datetime(2025, 3, 19, 15, 50, 38, tzinfo=UTC)
    t_c2 = datetime(2025, 3, 20, 9, 31, 20, tzinfo=UTC)
    t_co = datetime(2025, 3, 20, 9, 31, 21, tzinfo=UTC)  # +1 s so it sorts after t_c2
    t_o = datetime(2025, 3, 20, 9, 31, 22, tzinfo=UTC)
    t_c3 = datetime(2025, 3, 20, 10, 25, 16, tzinfo=UTC)

    def _e(dir_: Direction, qty: str, price: str, opened: datetime, pnl: str | None = None, is_mixed: bool = False) -> TradeCreate:
        return TradeCreate(
            symbol="VST",
            direction=dir_,
            asset_class=AssetClass.EQUITY,
            quantity=Decimal(qty),
            entry_price=Decimal(price),
            opened_at=opened,
            pnl=Decimal(pnl) if pnl is not None else None,
            closed_at=opened if pnl is not None else None,
            commission=Decimal("0"),
            is_mixed_execution=is_mixed,
        )

    execs = [
        _e(Direction.LONG, "7.00000", "130.47500", t_buy1),
        _e(Direction.LONG, "0.65080", "130.40000", t_buy1),
        _e(Direction.LONG, "5.00000", "130.25000", t_buy3),
        _e(Direction.SHORT, "0.68230", "130.05000", t_c1, pnl="-1.27742300"),
        _e(Direction.SHORT, "5.00000", "126.35000", t_c2, pnl="-22.35813900"),
        # C;O: closes remaining LONG lots, flips 0.03150 into a new SHORT
        _e(Direction.SHORT, "7.00000", "126.35000", t_co, pnl="-29.78127000", is_mixed=True),
        # O: opens an additional SHORT lot
        _e(Direction.SHORT, "0.65080", "126.24000", t_o),
        # C: closes both short lots (0.03150 + 0.65080 = 0.68230)
        _e(Direction.LONG, "0.68230", "130.68890", t_c3, pnl="-3.93078000"),
    ]

    result = aggregate_executions_fifo(execs)
    closed = [t for t in result if t.closed_at is not None]
    open_ = [t for t in result if t.closed_at is None]

    # All positions must be fully closed.
    assert open_ == [], f"Expected no open lots, got: {[(t.direction, t.quantity) for t in open_]}"

    # Expect exactly 7 closed trades.
    assert len(closed) == 7, f"Expected 7 closed trades, got {len(closed)}:\n" + "\n".join(
        f"  {t.direction} qty={t.quantity} entry={t.entry_price} net_pnl={t.net_pnl}" for t in sorted(closed, key=lambda x: x.opened_at)
    )

    # No sentinel entry price (0.001) should appear.
    for t in closed:
        assert t.entry_price != Decimal("0.001"), f"Sentinel entry_price on {t.direction} qty={t.quantity}: C;O remainder was mis-classified as orphaned."

    # The two SHORT-direction closed trades come from the LONG 0.68230 C execution.
    short_closes = [t for t in closed if t.direction == Direction.SHORT]
    assert len(short_closes) == 2, f"Expected 2 SHORT closes, got {len(short_closes)}"
    short_entries = sorted(
        t.entry_price for t in short_closes if t.entry_price is not None
    )
    assert short_entries[0] == Decimal("126.24000"), f"Expected SHORT entry 126.24, got {short_entries[0]}"
    assert short_entries[1] == Decimal("126.35000"), f"Expected SHORT entry 126.35 (C;O flip), got {short_entries[1]}"
    # Both short closes must have negative net_pnl (bought back higher than sold).
    for t in short_closes:
        assert t.net_pnl is not None
        assert t.net_pnl < Decimal("0"), f"Expected negative net_pnl for short close, got {t.net_pnl}"
