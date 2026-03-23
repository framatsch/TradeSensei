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

import warnings
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
    res = aggregate_executions_fifo(execs)
    assert len(res) == 1
    t = res[0]
    assert t.quantity == Decimal(100)
    assert t.entry_price == Decimal(150)
    assert t.exit_price == Decimal(160)
    assert t.pnl == Decimal(1000)
    assert t.opened_at == t1
    assert t.closed_at == t2
    assert t.direction == Direction.LONG


def test_aggregate_partial_close() -> None:
    t1 = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    t2 = datetime(2024, 1, 1, 11, 0, tzinfo=UTC)
    execs = [
        _tc("AAPL", Direction.LONG, 100, 150, t1),
        _tc("AAPL", Direction.SHORT, 50, 160, t2, pnl=500),
    ]
    res = aggregate_executions_fifo(execs)
    assert len(res) == 2
    closed = [t for t in res if t.exit_price is not None][0]
    open_t = [t for t in res if t.exit_price is None][0]
    assert closed.quantity == Decimal(50)
    assert closed.pnl == Decimal(500)
    assert open_t.quantity == Decimal(50)


def test_aggregate_orphaned_close() -> None:
    t1 = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    execs = [_tc("AAPL", Direction.SHORT, 100, 160, t1, pnl=1000)]
    res = aggregate_executions_fifo(execs)
    assert len(res) == 1
    t = res[0]
    assert t.direction == Direction.LONG  # reversed from SHORT
    assert t.quantity == Decimal(100)
    assert t.exit_price == Decimal(160)
    assert t.pnl == Decimal(1000)


# ---------------------------------------------------------------------------
# Task 4.5 — Backward compatibility
# ---------------------------------------------------------------------------


def test_no_corporate_actions_arg_is_backward_compatible() -> None:
    """Calling without corporate_actions must behave identically to before."""
    t1 = datetime(2024, 3, 1, 9, 0, tzinfo=UTC)
    t2 = datetime(2024, 3, 1, 15, 0, tzinfo=UTC)
    execs = [
        _tc("MSFT", Direction.LONG, 50, 400, t1),
        _tc("MSFT", Direction.SHORT, 50, 410, t2, pnl=500),
    ]
    res_old = aggregate_executions_fifo(execs)
    res_new = aggregate_executions_fifo(execs, corporate_actions=None)
    assert len(res_old) == len(res_new) == 1
    assert res_old[0].entry_price == res_new[0].entry_price


# ---------------------------------------------------------------------------
# Task 4.5 — 2:1 Forward split
# ---------------------------------------------------------------------------


def test_forward_split_2_for_1() -> None:
    """A 2:1 forward split doubles quantity and halves entry price of open lots.

    Scenario from spec:
    - Buy 100 shares at $10.00
    - 2:1 split occurs
    - Sell 200 shares at $6.00
    Expected: quantity=200, entry_price=5.00, exit_price=6.00
    """
    buy_date = datetime(2024, 1, 10, 10, 0, tzinfo=UTC)
    sell_date = datetime(2024, 3, 1, 10, 0, tzinfo=UTC)
    split_date = date(2024, 2, 1)  # between buy and sell

    ca = _CA(symbol="XYZ", date=split_date, ratio=Decimal("2"))

    execs = [
        _tc("XYZ", Direction.LONG, 100, "10.00", buy_date),
        _tc("XYZ", Direction.SHORT, 200, "6.00", sell_date, pnl="200"),
    ]

    res = aggregate_executions_fifo(execs, corporate_actions=[ca])

    assert len(res) == 1, f"Expected 1 closed trade, got {len(res)}"
    trade = res[0]
    assert trade.quantity == Decimal("200")
    assert trade.entry_price == Decimal("5.00")
    assert trade.exit_price == Decimal("6.00")


# ---------------------------------------------------------------------------
# Task 4.5 — 1:20 Reverse split with conid change (OTLK scenario)
# ---------------------------------------------------------------------------


def test_reverse_split_1_for_20_with_conid_remap() -> None:
    """1:20 reverse split with old_conid → new_conid mapping (OTLK case).

    Scenario from spec:
    - Buy 100 shares of OTLK, conid="357194941", at $1.00
    - 1:20 reverse split: old_conid → new_conid, ratio = 1/20 = 0.05
    - Sell 5 shares of OTLK, conid="690184975", at $15.00
    Expected: quantity=5, entry_price=20.00, exit_price=15.00, broker_conid="690184975"
    """
    buy_date = datetime(2024, 1, 5, 9, 30, tzinfo=UTC)
    sell_date = datetime(2024, 4, 1, 9, 30, tzinfo=UTC)
    split_date = date(2024, 3, 1)

    ca = _CA(
        symbol="OTLK",
        date=split_date,
        ratio=Decimal("1") / Decimal("20"),  # 0.05
        old_conid="357194941",
        new_conid="690184975",
    )

    execs = [
        _tc("OTLK", Direction.LONG, 100, "1.00", buy_date, conid="357194941"),
        _tc(
            "OTLK", Direction.SHORT, 5, "15.00", sell_date, pnl="75", conid="690184975"
        ),
    ]

    res = aggregate_executions_fifo(execs, corporate_actions=[ca])

    assert len(res) == 1, f"Expected 1 closed trade, got {len(res)}"
    trade = res[0]
    assert trade.quantity == Decimal("5")
    assert trade.entry_price == Decimal("1.00") / (
        Decimal("1") / Decimal("20")
    )  # 20.00
    assert trade.exit_price == Decimal("15.00")
    assert trade.broker_conid == "690184975"


# ---------------------------------------------------------------------------
# Task 4.5 — Fractional shares after reverse split
# ---------------------------------------------------------------------------


def test_fractional_shares_after_reverse_split() -> None:
    """15 shares after a 1:20 reverse split → 0.75 shares (no rounding).

    Scenario from spec:
    - Hold 15 shares
    - 1:20 reverse split, ratio = 0.05
    - Result: open lot of 0.75 shares
    """
    buy_date = datetime(2024, 1, 1, 9, 0, tzinfo=UTC)
    split_date = date(2024, 6, 1)

    ca = _CA(symbol="ABC", date=split_date, ratio=Decimal("1") / Decimal("20"))

    execs = [
        _tc("ABC", Direction.LONG, 15, "2.00", buy_date),
    ]

    res = aggregate_executions_fifo(execs, corporate_actions=[ca])

    assert len(res) == 1
    trade = res[0]
    assert trade.exit_price is None  # still open
    assert trade.quantity == Decimal("15") * (Decimal("1") / Decimal("20"))  # 0.75
    assert trade.entry_price == Decimal("2.00") / (
        Decimal("1") / Decimal("20")
    )  # 40.00


# ---------------------------------------------------------------------------
# Task 4.5 — Corporate action for symbol with no open lots
# ---------------------------------------------------------------------------


def test_split_for_symbol_not_in_queue_is_ignored() -> None:
    """A split event for a symbol with no open lots must not raise."""
    buy_date = datetime(2024, 2, 1, 9, 0, tzinfo=UTC)
    split_date = date(2024, 3, 1)

    # Split for "XYZ" but we only have open lots for "AAPL"
    ca = _CA(symbol="XYZ", date=split_date, ratio=Decimal("3"))

    execs = [
        _tc("AAPL", Direction.LONG, 10, "150", buy_date),
    ]

    res = aggregate_executions_fifo(execs, corporate_actions=[ca])

    # AAPL lot is unchanged
    assert len(res) == 1
    trade = res[0]
    assert trade.symbol == "AAPL"
    assert trade.quantity == Decimal("10")
    assert trade.entry_price == Decimal("150")


# ---------------------------------------------------------------------------
# Task 4.5 — Empty corporate_actions list
# ---------------------------------------------------------------------------


def test_empty_corporate_actions_list_is_noop() -> None:
    """An empty list behaves the same as None."""
    t1 = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    t2 = datetime(2024, 1, 2, 10, 0, tzinfo=UTC)
    execs = [
        _tc("TSLA", Direction.LONG, 20, "200", t1),
        _tc("TSLA", Direction.SHORT, 20, "220", t2, pnl="400"),
    ]

    res_none = aggregate_executions_fifo(execs, corporate_actions=None)
    res_empty = aggregate_executions_fifo(execs, corporate_actions=[])

    assert len(res_none) == len(res_empty) == 1
    assert res_none[0].entry_price == res_empty[0].entry_price


# ---------------------------------------------------------------------------
# Task 4.5 — Split applied only to the correct symbol
# ---------------------------------------------------------------------------


def test_split_applied_only_to_matching_symbol() -> None:
    """A split for "XYZ" must not affect open lots for "ABC"."""
    buy_date = datetime(2024, 1, 1, 9, 0, tzinfo=UTC)
    split_date = date(2024, 2, 1)
    sell_date = datetime(2024, 3, 1, 9, 0, tzinfo=UTC)

    ca_xyz = _CA(symbol="XYZ", date=split_date, ratio=Decimal("2"))

    execs = [
        _tc("ABC", Direction.LONG, 100, "10.00", buy_date),
        _tc("XYZ", Direction.LONG, 100, "5.00", buy_date),
        _tc("ABC", Direction.SHORT, 100, "12.00", sell_date, pnl="200"),
        _tc("XYZ", Direction.SHORT, 200, "3.00", sell_date, pnl="-400"),
    ]

    res = aggregate_executions_fifo(execs, corporate_actions=[ca_xyz])
    closed = {t.symbol: t for t in res if t.exit_price is not None}

    # ABC is unaffected — entry_price stays at 10.00
    assert closed["ABC"].entry_price == Decimal("10.00")
    assert closed["ABC"].quantity == Decimal("100")

    # XYZ has been split 2:1 → entry_price = 2.50, quantity = 200
    assert closed["XYZ"].entry_price == Decimal("5.00") / Decimal("2")
    assert closed["XYZ"].quantity == Decimal("200")
