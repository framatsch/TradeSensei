import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from app.services.trade_service import TradeService
from app.models.trade import Trade
from app.schemas.trade import TradeRead


@pytest.fixture
def repo():
    return AsyncMock()


@pytest.fixture
def service(repo):
    s = TradeService(repo)
    return s


@pytest.mark.asyncio
async def test_merge_trades_happy_path(service, repo):
    user_id = uuid.uuid4()
    t1 = Trade(id=uuid.uuid4(), user_id=user_id, symbol="AAPL", account_id=uuid.uuid4())
    t2 = Trade(
        id=uuid.uuid4(), user_id=user_id, symbol="AAPL", account_id=t1.account_id
    )

    repo.get_by_id.side_effect = [t1, t2]
    # mocked logic ...


@pytest.mark.asyncio
async def test_merge_trades_validation_failures(service, repo):
    # validation tests here
    pass
