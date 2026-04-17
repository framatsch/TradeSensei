import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.models.logical_execution import EXECUTION_ORIGIN_MANUAL, LogicalExecution
from app.models.trade import Direction, Trade
from app.services.execution import ExecutionService


@pytest.mark.asyncio
async def test_re_aggregate_trade_vwap_logic():
    # Setup mock session and repos
    mock_session = AsyncMock()
    service = ExecutionService(mock_session)
    
    trade_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # Mock trade
    trade = Trade()
    trade.id = trade_id
    trade.user_id = user_id
    trade.direction = Direction.LONG
    trade.multiplier = 1
    service.trade_repo.get_by_id = AsyncMock(return_value=trade)
    
    # Mock executions: 
    # 1. Buy 100 @ 150 (Entry)
    # 2. Buy 50 @ 160 (Entry)
    # 3. Sell 75 @ 170 (Exit)
    # Commissions: 1.0, 0.5, 1.5 = 3.0
    
    exec1 = LogicalExecution(
        id=uuid.uuid4(),
        trade_id=trade_id,
        direction=Direction.LONG,
        quantity=Decimal("100"),
        price=Decimal("150.00"),
        commission=Decimal("1.00"),
        executed_at=datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
        origin=EXECUTION_ORIGIN_MANUAL
    )
    exec2 = LogicalExecution(
        id=uuid.uuid4(),
        trade_id=trade_id,
        direction=Direction.LONG,
        quantity=Decimal("50"),
        price=Decimal("160.00"),
        commission=Decimal("0.50"),
        executed_at=datetime(2024, 1, 1, 11, 0, tzinfo=UTC),
        origin=EXECUTION_ORIGIN_MANUAL
    )
    exec3 = LogicalExecution(
        id=uuid.uuid4(),
        trade_id=trade_id,
        direction=Direction.SHORT,
        quantity=Decimal("75"),
        price=Decimal("170.00"),
        commission=Decimal("1.50"),
        executed_at=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
        origin=EXECUTION_ORIGIN_MANUAL
    )
    
    service.execution_repo.list_by_trade_id = AsyncMock(return_value=[exec1, exec2, exec3])
    
    # Run re-aggregation
    await service.re_aggregate_trade(trade_id, user_id)
    
    # Assertions
    # Total Entry Qty = 150
    assert trade.quantity == Decimal("150")
    
    # VWAP Entry = (100*150 + 50*160) / 150 = (15000 + 8000) / 150 = 23000 / 150 = 153.333...
    assert trade.entry_price == Decimal("23000") / Decimal("150")
    
    # VWAP Exit = 170 (only one exit execution)
    assert trade.exit_price == Decimal("170.00")
    
    # Total Commission = 1.0 + 0.5 + 1.5 = 3.0
    assert trade.commission == Decimal("3.00")
    
    # PnL (computed) = (Exit - Entry) * ExitQty = (170 - 153.333...) * 75
    # = (170 - 23000/150) * 75 = 170*75 - (23000/150)*75 = 12750 - 23000/2 = 12750 - 11500 = 1250
    assert trade.pnl == Decimal("1250.00")
    
    # Net PnL = 1250 - 3 = 1247
    assert trade.net_pnl == Decimal("1247.00")
    
    # opened_at = earliest entry = 10:00
    assert trade.opened_at == exec1.executed_at
    
    # closed_at = None (since exit_qty < entry_qty)
    assert trade.closed_at is None

@pytest.mark.asyncio
async def test_re_aggregate_trade_full_close():
    mock_session = AsyncMock()
    service = ExecutionService(mock_session)
    trade_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    trade = Trade()
    trade.id = trade_id
    trade.user_id = user_id
    trade.direction = Direction.SHORT
    trade.multiplier = 100 # Options
    
    service.trade_repo.get_by_id = AsyncMock(return_value=trade)
    
    # Short 1 @ 5.00
    # Buy 1 @ 4.00 (Full close)
    exec1 = LogicalExecution(
        id=uuid.uuid4(),
        trade_id=trade_id,
        direction=Direction.SHORT,
        quantity=Decimal("1"),
        price=Decimal("5.00"),
        commission=Decimal("0.50"),
        executed_at=datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    )
    exec2 = LogicalExecution(
        id=uuid.uuid4(),
        trade_id=trade_id,
        direction=Direction.LONG,
        quantity=Decimal("1"),
        price=Decimal("4.00"),
        commission=Decimal("0.50"),
        executed_at=datetime(2024, 1, 1, 11, 0, tzinfo=UTC)
    )
    
    service.execution_repo.list_by_trade_id = AsyncMock(return_value=[exec1, exec2])
    
    await service.re_aggregate_trade(trade_id, user_id)
    
    assert trade.quantity == Decimal("1")
    assert trade.entry_price == Decimal("5.00")
    assert trade.exit_price == Decimal("4.00")
    # PnL = (Entry - Exit) * Qty * Mult = (5.00 - 4.00) * 1 * 100 = 100
    assert trade.pnl == Decimal("100.00")
    assert trade.closed_at == exec2.executed_at
