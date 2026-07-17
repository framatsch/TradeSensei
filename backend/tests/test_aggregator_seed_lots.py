from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from app.models.trade import AssetClass, Direction
from app.schemas.trade import TradeCreate
from app.utils.parsers.aggregator import aggregate_executions_fifo


@dataclass
class SeedLotStub:
    id: uuid.UUID
    symbol: str
    broker_conid: str | None
    asset_class: AssetClass | str
    quantity: Decimal
    entry_price: Decimal
    commission: Decimal
    opened_at: datetime
    direction: Direction | str
    multiplier: int
    exit_price: Decimal | None = None
    closed_at: datetime | None = None
    pnl: Decimal | None = None


@dataclass
class CorporateActionStub:
    symbol: str
    date: date
    ratio: Decimal
    old_conid: str | None = None
    new_conid: str | None = None


def _exec(
    *,
    symbol: str,
    direction: Direction,
    quantity: str,
    price: str,
    opened_at: datetime,
    pnl: str | None,
    conid: str | None,
) -> TradeCreate:
    return TradeCreate(
        symbol=symbol,
        direction=direction,
        asset_class=AssetClass.EQUITY,
        quantity=Decimal(quantity),
        entry_price=Decimal(price),
        opened_at=opened_at,
        closed_at=opened_at if pnl is not None else None,
        pnl=Decimal(pnl) if pnl is not None else None,
        commission=Decimal("0"),
        broker_conid=conid,
        multiplier=1,
    )


def test_seed_open_lot_close_carries_db_trade_id() -> None:
    t0 = datetime(2024, 1, 1, 9, 30, tzinfo=UTC)
    t1 = datetime(2025, 1, 1, 10, 0, tzinfo=UTC)
    seed_id = uuid.uuid4()
    seed = SeedLotStub(
        id=seed_id,
        symbol="SEEDA",
        broker_conid="500001",
        asset_class=AssetClass.EQUITY,
        quantity=Decimal("10"),
        entry_price=Decimal("100"),
        commission=Decimal("0"),
        opened_at=t0,
        direction=Direction.LONG,
        multiplier=1,
    )

    close_execution = _exec(
        symbol="SEEDA",
        direction=Direction.SHORT,
        quantity="10",
        price="110",
        opened_at=t1,
        pnl="100",
        conid="500001",
    )

    result = aggregate_executions_fifo([close_execution], seed_open_lots=[seed])
    closed = [trade for trade in result if trade.closed_at is not None]
    assert len(closed) == 1
    assert closed[0].db_trade_id == seed_id
    assert closed[0].entry_price == Decimal("100")
    assert closed[0].exit_price == Decimal("110")
    assert closed[0].pnl == Decimal("100")


def test_split_adjusts_seed_open_lot_before_close() -> None:
    t0 = datetime(2024, 11, 15, 10, 0, tzinfo=UTC)
    t1 = datetime(2025, 4, 1, 10, 0, tzinfo=UTC)
    seed = SeedLotStub(
        id=uuid.uuid4(),
        symbol="SPLT",
        broker_conid="600111",
        asset_class=AssetClass.EQUITY,
        quantity=Decimal("100"),
        entry_price=Decimal("10"),
        commission=Decimal("0"),
        opened_at=t0,
        direction=Direction.LONG,
        multiplier=1,
    )
    close_execution = _exec(
        symbol="SPLT",
        direction=Direction.SHORT,
        quantity="10",
        price="80",
        opened_at=t1,
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

    result = aggregate_executions_fifo(
        [close_execution],
        corporate_actions=[split],
        seed_open_lots=[seed],
    )

    closed = [trade for trade in result if trade.closed_at is not None]
    assert len(closed) == 1
    trade = closed[0]
    assert trade.quantity == Decimal("10")
    assert trade.entry_price == Decimal("100")
    assert trade.exit_price == Decimal("80")
    assert trade.pnl == Decimal("-200")


def test_seed_orphaned_lot_fill_reconstructs_pnl_without_sentinel() -> None:
    t_open = datetime(2025, 1, 2, 9, 30, tzinfo=UTC)
    t_close = datetime(2025, 1, 3, 9, 30, tzinfo=UTC)
    opening_execution = _exec(
        symbol="ORPH",
        direction=Direction.LONG,
        quantity="5",
        price="10",
        opened_at=t_open,
        pnl=None,
        conid="700001",
    )
    orphaned = SeedLotStub(
        id=uuid.uuid4(),
        symbol="ORPH",
        broker_conid="700001",
        asset_class=AssetClass.EQUITY,
        quantity=Decimal("5"),
        entry_price=Decimal("0.001"),
        commission=Decimal("0"),
        opened_at=t_close,
        direction=Direction.LONG,
        multiplier=1,
        exit_price=Decimal("12"),
        closed_at=t_close,
        pnl=Decimal("0"),
    )

    result = aggregate_executions_fifo(
        [opening_execution],
        seed_orphaned_lots=[orphaned],
    )

    filled = [trade for trade in result if trade.closed_at is not None]
    assert len(filled) == 1
    trade = filled[0]
    assert trade.entry_price == Decimal("10")
    assert trade.entry_price != Decimal("0.001")
    assert trade.exit_price == Decimal("12")
    assert trade.pnl == Decimal("10")
    assert trade.net_pnl == Decimal("10")


def test_seed_direction_mismatch_does_not_match_or_fill() -> None:
    t0 = datetime(2024, 1, 1, 9, 30, tzinfo=UTC)
    t1 = datetime(2025, 1, 1, 10, 0, tzinfo=UTC)
    seed = SeedLotStub(
        id=uuid.uuid4(),
        symbol="MISM",
        broker_conid="800001",
        asset_class=AssetClass.EQUITY,
        quantity=Decimal("10"),
        entry_price=Decimal("100"),
        commission=Decimal("0"),
        opened_at=t0,
        direction=Direction.LONG,
        multiplier=1,
    )
    same_direction_open = _exec(
        symbol="MISM",
        direction=Direction.LONG,
        quantity="5",
        price="105",
        opened_at=t1,
        pnl=None,
        conid="800001",
    )
    opposite_orphaned = SeedLotStub(
        id=uuid.uuid4(),
        symbol="MISM",
        broker_conid="800001",
        asset_class=AssetClass.EQUITY,
        quantity=Decimal("5"),
        entry_price=Decimal("0.001"),
        commission=Decimal("0"),
        opened_at=t1,
        direction=Direction.SHORT,
        multiplier=1,
        exit_price=Decimal("110"),
        closed_at=t1,
        pnl=Decimal("0"),
    )

    result = aggregate_executions_fifo(
        [same_direction_open],
        seed_open_lots=[seed],
        seed_orphaned_lots=[opposite_orphaned],
    )

    closed = [trade for trade in result if trade.closed_at is not None]
    open_lots = [trade for trade in result if trade.closed_at is None]
    assert closed == []
    assert len(open_lots) == 2
