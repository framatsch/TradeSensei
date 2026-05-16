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

from app.core.exceptions import ExecutionValidationError
from app.models.logical_execution import EXECUTION_ORIGIN_MANUAL, LogicalExecution
from app.models.trade import AssetClass, Direction, Trade
from app.services.execution import ExecutionService


def _make_trade(
    id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    account_id: uuid.UUID | None = None,
    symbol: str = "AAPL",
) -> Trade:
    return Trade(
        image_urls=[],
        id=id or uuid.uuid4(),
        user_id=user_id or uuid.uuid4(),
        account_id=account_id or uuid.uuid4(),
        symbol=symbol,
        direction=Direction.LONG,
        asset_class=AssetClass.EQUITY,
        quantity=Decimal("10"),
        entry_price=Decimal("100"),
        opened_at=datetime.now(UTC),
    )


def _make_execution(
    id: uuid.UUID | None = None,
    trade_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    account_id: uuid.UUID | None = None,
    symbol: str = "AAPL",
) -> LogicalExecution:
    return LogicalExecution(
        id=id or uuid.uuid4(),
        user_id=user_id or uuid.uuid4(),
        account_id=account_id or uuid.uuid4(),
        symbol=symbol,
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


@pytest.fixture()
def service(mock_session: AsyncMock) -> ExecutionService:
    svc = ExecutionService(mock_session)
    svc.execution_repo = AsyncMock()
    svc.trade_repo = AsyncMock()
    svc._re_aggregate_trade = AsyncMock()
    return svc


@pytest.mark.asyncio
async def test_reassign_execution_happy_path(
    service: ExecutionService, mock_session: AsyncMock
) -> None:
    user_id = uuid.uuid4()
    source_trade_id = uuid.uuid4()
    target_trade_id = uuid.uuid4()
    account_id = uuid.uuid4()

    execution = _make_execution(
        trade_id=source_trade_id,
        user_id=user_id,
        account_id=account_id,
        symbol="AAPL",
    )
    target_trade = _make_trade(
        id=target_trade_id,
        user_id=user_id,
        account_id=account_id,
        symbol="AAPL",
    )
    updated = _make_execution(
        id=execution.id,
        trade_id=target_trade_id,
        user_id=user_id,
        account_id=account_id,
        symbol="AAPL",
    )

    service.execution_repo.get_by_id.return_value = execution
    service.trade_repo.get_by_id.return_value = target_trade
    service.execution_repo.update.return_value = updated
    service.execution_repo.list_by_trade_id.return_value = [_make_execution()]

    result = await service.reassign_execution(execution.id, target_trade_id, user_id)

    assert result.trade_id == target_trade_id
    service.execution_repo.update.assert_awaited_once_with(
        execution, trade_id=target_trade_id
    )
    service._re_aggregate_trade.assert_any_await(target_trade_id, user_id)
    service._re_aggregate_trade.assert_any_await(source_trade_id, user_id)
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_reassign_execution_symbol_mismatch(service: ExecutionService) -> None:
    user_id = uuid.uuid4()
    execution = _make_execution(user_id=user_id, symbol="AAPL")
    target_trade = _make_trade(user_id=user_id, symbol="TSLA")

    service.execution_repo.get_by_id.return_value = execution
    service.trade_repo.get_by_id.return_value = target_trade

    with pytest.raises(ExecutionValidationError):
        await service.reassign_execution(execution.id, target_trade.id, user_id)


@pytest.mark.asyncio
async def test_reassign_execution_account_mismatch(service: ExecutionService) -> None:
    user_id = uuid.uuid4()
    execution = _make_execution(user_id=user_id, account_id=uuid.uuid4())
    target_trade = _make_trade(user_id=user_id, account_id=uuid.uuid4())

    service.execution_repo.get_by_id.return_value = execution
    service.trade_repo.get_by_id.return_value = target_trade

    with pytest.raises(ExecutionValidationError):
        await service.reassign_execution(execution.id, target_trade.id, user_id)


@pytest.mark.asyncio
async def test_reassign_execution_source_trade_deleted_when_empty(
    service: ExecutionService,
) -> None:
    user_id = uuid.uuid4()
    source_trade_id = uuid.uuid4()
    target_trade_id = uuid.uuid4()
    account_id = uuid.uuid4()

    execution = _make_execution(
        trade_id=source_trade_id,
        user_id=user_id,
        account_id=account_id,
    )
    target_trade = _make_trade(
        id=target_trade_id,
        user_id=user_id,
        account_id=account_id,
    )
    source_trade = _make_trade(
        id=source_trade_id,
        user_id=user_id,
        account_id=account_id,
    )

    service.execution_repo.get_by_id.return_value = execution
    service.trade_repo.get_by_id.side_effect = [target_trade, source_trade]
    service.execution_repo.update.return_value = _make_execution(
        id=execution.id,
        trade_id=target_trade_id,
        user_id=user_id,
        account_id=account_id,
    )
    service.execution_repo.list_by_trade_id.return_value = []

    await service.reassign_execution(execution.id, target_trade_id, user_id)

    service.trade_repo.delete.assert_awaited_once_with(source_trade)


@pytest.mark.asyncio
async def test_detach_execution_happy_path(
    service: ExecutionService, mock_session: AsyncMock
) -> None:
    user_id = uuid.uuid4()
    source_trade_id = uuid.uuid4()
    execution = _make_execution(trade_id=source_trade_id, user_id=user_id)
    new_trade = _make_trade(id=uuid.uuid4(), user_id=user_id)

    service.execution_repo.get_by_id.return_value = execution
    service.execution_repo.list_by_trade_id.return_value = [
        execution,
        _make_execution(trade_id=source_trade_id, user_id=user_id),
    ]
    service.trade_repo.create.return_value = new_trade
    service.trade_repo.get_by_id.return_value = new_trade

    result = await service.detach_execution(execution.id, user_id)

    assert result.id == new_trade.id
    service.trade_repo.create.assert_awaited_once()
    service.execution_repo.update.assert_awaited_once()
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_detach_execution_cannot_detach_last(service: ExecutionService) -> None:
    user_id = uuid.uuid4()
    source_trade_id = uuid.uuid4()
    execution = _make_execution(trade_id=source_trade_id, user_id=user_id)

    service.execution_repo.get_by_id.return_value = execution
    service.execution_repo.list_by_trade_id.return_value = [execution]

    with pytest.raises(ExecutionValidationError):
        await service.detach_execution(execution.id, user_id)


@pytest.mark.asyncio
async def test_detach_execution_new_trade_aggregated(service: ExecutionService) -> None:
    user_id = uuid.uuid4()
    source_trade_id = uuid.uuid4()
    execution = _make_execution(trade_id=source_trade_id, user_id=user_id)
    new_trade = _make_trade(id=uuid.uuid4(), user_id=user_id)

    service.execution_repo.get_by_id.return_value = execution
    service.execution_repo.list_by_trade_id.return_value = [
        execution,
        _make_execution(trade_id=source_trade_id, user_id=user_id),
    ]
    service.trade_repo.create.return_value = new_trade
    service.trade_repo.get_by_id.return_value = new_trade

    await service.detach_execution(execution.id, user_id)

    service._re_aggregate_trade.assert_any_await(new_trade.id, user_id)
    service._re_aggregate_trade.assert_any_await(source_trade_id, user_id)
