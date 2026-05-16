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

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import TradeNotFoundError
from app.models.logical_execution import EXECUTION_ORIGIN_MANUAL, LogicalExecution
from app.models.trade import AssetClass, Direction, Trade
from app.services.trade_service import TradeService


@pytest.fixture
def service(mock_session: AsyncMock) -> TradeService:
    s = TradeService(mock_session)
    s._re_aggregate_trade = AsyncMock()
    return s


def _make_trade(
    id: uuid.UUID,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    symbol: str,
    opened_at: datetime,
) -> Trade:
    now = datetime.now(UTC)
    trade = Trade(
        id=id,
        user_id=user_id,
        account_id=account_id,
        symbol=symbol,
        direction=Direction.LONG,
        asset_class=AssetClass.EQUITY,
        quantity=Decimal("1"),
        entry_price=Decimal("100"),
        commission=Decimal("0"),
        multiplier=1,
        opened_at=opened_at,
        created_at=now,
        updated_at=now,
    )
    trade.image_urls = []
    trade.is_manually_edited = False
    trade.tags = []
    trade.notes = None
    return trade


def _make_execution(id: uuid.UUID, trade_id: uuid.UUID) -> LogicalExecution:
    return LogicalExecution(
        id=id,
        user_id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        symbol="AAPL",
        asset_class=AssetClass.EQUITY,
        direction=Direction.LONG,
        quantity=Decimal("1"),
        price=Decimal("100"),
        commission=Decimal("0"),
        executed_at=datetime.now(UTC),
        origin=EXECUTION_ORIGIN_MANUAL,
        trade_id=trade_id,
        multiplier=1,
    )


@pytest.mark.asyncio
async def test_merge_trades_happy_path(service):
    user_id = uuid.uuid4()
    account_id = uuid.uuid4()
    t1 = _make_trade(
        id=uuid.uuid4(),
        user_id=user_id,
        account_id=account_id,
        symbol="AAPL",
        opened_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    t2 = _make_trade(
        id=uuid.uuid4(),
        user_id=user_id,
        account_id=account_id,
        symbol="AAPL",
        opened_at=datetime(2024, 1, 2, tzinfo=UTC),
    )

    get_by_id_values = [t1, t2, t1]
    service._repo.get_by_id = AsyncMock(side_effect=get_by_id_values)
    service._repo.delete = AsyncMock()

    execution = _make_execution(uuid.uuid4(), t2.id)

    with pytest.MonkeyPatch.context() as m:
        exec_repo = AsyncMock()
        exec_repo.list_by_trade_id.return_value = [execution]
        exec_repo.reassign_to_trade = AsyncMock(return_value=1)
        m.setattr(
            "app.repositories.execution.ExecutionRepository",
            lambda _session: exec_repo,
        )
        result = await service.merge_trades([t1.id, t2.id], user_id)

    assert result.id == t1.id
    exec_repo.reassign_to_trade.assert_awaited_once_with([execution.id], t1.id)
    service._repo.delete.assert_awaited_once_with(t2)
    service._re_aggregate_trade.assert_awaited_once_with(t1.id)


@pytest.mark.asyncio
async def test_merge_trades_validation_failures(service):
    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    account_id = uuid.uuid4()

    owned_trade = _make_trade(
        id=uuid.uuid4(),
        user_id=user_id,
        account_id=account_id,
        symbol="AAPL",
        opened_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    unowned_trade = _make_trade(
        id=uuid.uuid4(),
        user_id=other_user_id,
        account_id=account_id,
        symbol="AAPL",
        opened_at=datetime(2024, 1, 2, tzinfo=UTC),
    )
    mismatch_trade = _make_trade(
        id=uuid.uuid4(),
        user_id=user_id,
        account_id=account_id,
        symbol="TSLA",
        opened_at=datetime(2024, 1, 3, tzinfo=UTC),
    )

    # The real repository returns None when the trade doesn't belong to user_id
    # (ownership enforced at the SQL layer with WHERE user_id = :uid).
    service._repo.get_by_id = AsyncMock(side_effect=[owned_trade, None])
    with pytest.raises(TradeNotFoundError):
        await service.merge_trades([owned_trade.id, unowned_trade.id], user_id)

    service._repo.get_by_id = AsyncMock(side_effect=[owned_trade, mismatch_trade])
    with pytest.raises(ValueError, match="Trades must have the same symbol"):
        await service.merge_trades([owned_trade.id, mismatch_trade.id], user_id)

    service._repo.get_by_id = AsyncMock(return_value=owned_trade)
    with pytest.raises(ValueError, match="at least two unique trades"):
        await service.merge_trades([owned_trade.id, owned_trade.id], user_id)
