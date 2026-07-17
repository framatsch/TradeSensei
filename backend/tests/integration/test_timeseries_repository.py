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

"""Integration tests for TimeSeriesRepository."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account, AccountType
from app.models.portfolio import Portfolio
from app.models.trade import AssetClass, Direction, Trade
from app.models.user import User
from app.repositories.timeseries_repository import TimeSeriesRepository

pytestmark = pytest.mark.asyncio


async def _make_user(session: AsyncSession) -> User:
    user = User(username=f"u_{uuid.uuid4().hex[:8]}", email=f"{uuid.uuid4().hex}@test.com", hashed_password="x")
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def _make_portfolio(session: AsyncSession, user_id: uuid.UUID) -> Portfolio:
    p = Portfolio(user_id=user_id, name="TestTS", base_currency="USD")
    session.add(p)
    await session.flush()
    await session.refresh(p)
    return p


async def _make_account(session: AsyncSession, user_id: uuid.UUID, portfolio_id: uuid.UUID) -> Account:
    a = Account(user_id=user_id, portfolio_id=portfolio_id, name="TSAccount", type=AccountType.MANUAL, currency="USD")
    session.add(a)
    await session.flush()
    await session.refresh(a)
    return a


async def _make_closed_trade(
    session: AsyncSession,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    symbol: str = "AAPL",
    pnl: Decimal = Decimal("150"),
    closed_at: datetime = datetime(2024, 6, 1, 15, 0, tzinfo=timezone.utc),
    asset_class: AssetClass = AssetClass.EQUITY,
) -> Trade:
    t = Trade(
        user_id=user_id,
        account_id=account_id,
        symbol=symbol,
        direction=Direction.LONG,
        asset_class=asset_class,
        quantity=Decimal("10"),
        entry_price=Decimal("100"),
        exit_price=Decimal("115"),
        pnl=pnl,
        opened_at=datetime(2024, 5, 31, 9, 30, tzinfo=timezone.utc),
        closed_at=closed_at,
        currency="USD",
    )
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t


@pytest.mark.integration
async def test_get_daily_pnl_empty(db_session: AsyncSession):
    user = await _make_user(db_session)
    portfolio = await _make_portfolio(db_session, user.id)
    repo = TimeSeriesRepository(db_session)

    result = await repo.get_daily_pnl(
        user_id=user.id, portfolio_id=portfolio.id, account_id=None, from_dt=None, to_dt=None
    )
    assert result == []


@pytest.mark.integration
async def test_get_daily_pnl_with_trades(db_session: AsyncSession):
    user = await _make_user(db_session)
    portfolio = await _make_portfolio(db_session, user.id)
    account = await _make_account(db_session, user.id, portfolio.id)
    await _make_closed_trade(db_session, user.id, account.id, pnl=Decimal("100"))
    await _make_closed_trade(
        db_session, user.id, account.id,
        pnl=Decimal("50"),
        closed_at=datetime(2024, 6, 2, 15, 0, tzinfo=timezone.utc),
    )
    repo = TimeSeriesRepository(db_session)

    result = await repo.get_daily_pnl(
        user_id=user.id, portfolio_id=portfolio.id, account_id=None, from_dt=None, to_dt=None
    )
    assert len(result) >= 1
    # Each element is (date, Decimal, int)
    trade_date, total_pnl, count = result[0]
    assert isinstance(total_pnl, Decimal)
    assert isinstance(count, int)


@pytest.mark.integration
async def test_get_daily_pnl_with_account_filter(db_session: AsyncSession):
    user = await _make_user(db_session)
    portfolio = await _make_portfolio(db_session, user.id)
    account = await _make_account(db_session, user.id, portfolio.id)
    await _make_closed_trade(db_session, user.id, account.id)
    repo = TimeSeriesRepository(db_session)

    result = await repo.get_daily_pnl(
        user_id=user.id, portfolio_id=portfolio.id, account_id=account.id, from_dt=None, to_dt=None
    )
    assert len(result) >= 1


@pytest.mark.integration
async def test_get_daily_pnl_with_date_range(db_session: AsyncSession):
    user = await _make_user(db_session)
    portfolio = await _make_portfolio(db_session, user.id)
    account = await _make_account(db_session, user.id, portfolio.id)
    await _make_closed_trade(db_session, user.id, account.id)
    repo = TimeSeriesRepository(db_session)

    from_dt = datetime(2024, 6, 1, tzinfo=timezone.utc)
    to_dt = datetime(2024, 6, 30, tzinfo=timezone.utc)
    result = await repo.get_daily_pnl(
        user_id=user.id, portfolio_id=portfolio.id, account_id=None, from_dt=from_dt, to_dt=to_dt
    )
    assert len(result) >= 1


@pytest.mark.integration
async def test_get_closed_pnl_series_empty(db_session: AsyncSession):
    user = await _make_user(db_session)
    portfolio = await _make_portfolio(db_session, user.id)
    repo = TimeSeriesRepository(db_session)

    result = await repo.get_closed_pnl_series(
        user_id=user.id, portfolio_id=portfolio.id, account_id=None, from_dt=None, to_dt=None
    )
    assert result == []


@pytest.mark.integration
async def test_get_closed_pnl_series_with_trades(db_session: AsyncSession):
    user = await _make_user(db_session)
    portfolio = await _make_portfolio(db_session, user.id)
    account = await _make_account(db_session, user.id, portfolio.id)
    await _make_closed_trade(db_session, user.id, account.id, symbol="MSFT", pnl=Decimal("200"))
    repo = TimeSeriesRepository(db_session)

    result = await repo.get_closed_pnl_series(
        user_id=user.id, portfolio_id=portfolio.id, account_id=None, from_dt=None, to_dt=None
    )
    assert len(result) >= 1
    closed_at, pnl, symbol = result[0]
    assert isinstance(pnl, Decimal)
    assert symbol == "MSFT"


@pytest.mark.integration
async def test_get_pnl_by_symbol_empty(db_session: AsyncSession):
    user = await _make_user(db_session)
    portfolio = await _make_portfolio(db_session, user.id)
    repo = TimeSeriesRepository(db_session)

    result = await repo.get_pnl_by_symbol(
        user_id=user.id, portfolio_id=portfolio.id, account_id=None, from_dt=None, to_dt=None
    )
    assert result == []


@pytest.mark.integration
async def test_get_pnl_by_symbol_aggregates(db_session: AsyncSession):
    user = await _make_user(db_session)
    portfolio = await _make_portfolio(db_session, user.id)
    account = await _make_account(db_session, user.id, portfolio.id)
    await _make_closed_trade(db_session, user.id, account.id, symbol="GOOG", pnl=Decimal("300"))
    await _make_closed_trade(
        db_session, user.id, account.id, symbol="GOOG",
        pnl=Decimal("-50"),
        closed_at=datetime(2024, 6, 5, 15, 0, tzinfo=timezone.utc),
    )
    repo = TimeSeriesRepository(db_session)

    result = await repo.get_pnl_by_symbol(
        user_id=user.id, portfolio_id=portfolio.id, account_id=None, from_dt=None, to_dt=None
    )
    assert len(result) >= 1
    symbol, total_pnl, total_count, win_count = result[0]
    assert symbol == "GOOG"
    assert total_count == 2
    assert win_count == 1


@pytest.mark.integration
async def test_get_pnl_by_asset_class_empty(db_session: AsyncSession):
    user = await _make_user(db_session)
    portfolio = await _make_portfolio(db_session, user.id)
    repo = TimeSeriesRepository(db_session)

    result = await repo.get_pnl_by_asset_class(
        user_id=user.id, portfolio_id=portfolio.id, account_id=None, from_dt=None, to_dt=None
    )
    assert result == []


@pytest.mark.integration
async def test_get_pnl_by_asset_class_with_trades(db_session: AsyncSession):
    user = await _make_user(db_session)
    portfolio = await _make_portfolio(db_session, user.id)
    account = await _make_account(db_session, user.id, portfolio.id)
    await _make_closed_trade(
        db_session, user.id, account.id, symbol="SPY", pnl=Decimal("100"), asset_class=AssetClass.EQUITY
    )
    repo = TimeSeriesRepository(db_session)

    result = await repo.get_pnl_by_asset_class(
        user_id=user.id, portfolio_id=portfolio.id, account_id=None, from_dt=None, to_dt=None
    )
    assert len(result) >= 1
    asset_class, total_pnl, total_count, win_count = result[0]
    assert asset_class == "EQUITY"
