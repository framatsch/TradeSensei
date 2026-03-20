from datetime import UTC, datetime
from decimal import Decimal

from app.models.trade import AssetClass, Direction
from app.schemas.trade import TradeCreate
from app.utils.parsers.aggregator import aggregate_executions_fifo


def _tc(sym, dir_, qty, entry, opened, pnl=None, closed=None):
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
    )


def test_aggregate_simple_round_trip():
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


def test_aggregate_partial_close():
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


def test_aggregate_orphaned_close():
    t1 = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    execs = [_tc("AAPL", Direction.SHORT, 100, 160, t1, pnl=1000)]
    res = aggregate_executions_fifo(execs)
    assert len(res) == 1
    t = res[0]
    assert t.direction == Direction.LONG  # reversed from SHORT
    assert t.quantity == Decimal(100)
    assert t.exit_price == Decimal(160)
    assert t.pnl == Decimal(1000)
