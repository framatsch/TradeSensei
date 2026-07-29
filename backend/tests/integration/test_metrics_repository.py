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

"""Integration tests for MetricsRepository."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account, AccountType
from app.models.portfolio import Portfolio
from app.models.trade import AssetClass, Direction, Trade
from app.models.user import User
from app.repositories.metrics_repository import MetricsRepository

pytestmark = pytest.mark.asyncio


async def _make_user(session: AsyncSession) -> User:
    user = User(username=f"u_{uuid.uuid4().hex[:8]}", email=f"{uuid.uuid4().hex}@test.com", hashed_password="x")
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def _make_portfolio(session: AsyncSession, user_id: uuid.UUID) -> Portfolio:
    p = Portfolio(user_id=user_id, name="TestPortfolio", base_currency="USD")
    session.add(p)
    await session.flush()
    await session.refresh(p)
    return p


async def _make_account(session: AsyncSession, user_id: uuid.UUID, portfolio_id: uuid.UUID) -> Account:
    a = Account(user_id=user_id, portfolio_id=portfolio_id, name="TestAccount", type=AccountType.MANUAL, currency="USD")
    session.add(a)
    await session.flush()
    await session.refresh(a)
    return a


async def _make_closed_trade(
    session: AsyncSession,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    pnl: Decimal = Decimal("100"),
) -> Trade:
    t = Trade(
        user_id=user_id,
        account_id=account_id,
        symbol="AAPL",
        direction=Direction.LONG,
        asset_class=AssetClass.EQUITY,
        quantity=Decimal("10"),
        entry_price=Decimal("100"),
        exit_price=Decimal("110"),
        pnl=pnl,
        opened_at=datetime(2024, 1, 10, 9, 30, tzinfo=UTC),
        closed_at=datetime(2024, 1, 15, 15, 0, tzinfo=UTC),
        currency="USD",
    )
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t


@pytest.mark.integration
async def test_get_closed_trades_for_account_empty(db_session: AsyncSession):
    """Returns empty list when no matching closed trades exist."""
    user = await _make_user(db_session)
    portfolio = await _make_portfolio(db_session, user.id)
    repo = MetricsRepository(db_session)

    trades = await repo.get_closed_trades_for_account(
        account_id=uuid.uuid4(),
        portfolio_id=portfolio.id,
        user_id=user.id,
    )
    assert trades == []


@pytest.mark.integration
async def test_get_closed_trades_for_account_returns_data(db_session: AsyncSession):
    user = await _make_user(db_session)
    portfolio = await _make_portfolio(db_session, user.id)
    account = await _make_account(db_session, user.id, portfolio.id)
    await _make_closed_trade(db_session, user.id, account.id)
    repo = MetricsRepository(db_session)

    trades = await repo.get_closed_trades_for_account(
        account_id=account.id,
        portfolio_id=portfolio.id,
        user_id=user.id,
    )
    assert len(trades) == 1
    assert trades[0].symbol == "AAPL"


@pytest.mark.integration
async def test_get_closed_trades_for_account_with_date_range(db_session: AsyncSession):
    user = await _make_user(db_session)
    portfolio = await _make_portfolio(db_session, user.id)
    account = await _make_account(db_session, user.id, portfolio.id)
    await _make_closed_trade(db_session, user.id, account.id)
    repo = MetricsRepository(db_session)

    # Filter to a range that includes the trade
    from_dt = datetime(2024, 1, 1, tzinfo=UTC)
    to_dt = datetime(2024, 1, 31, tzinfo=UTC)
    trades = await repo.get_closed_trades_for_account(
        account_id=account.id,
        portfolio_id=portfolio.id,
        user_id=user.id,
        from_dt=from_dt,
        to_dt=to_dt,
    )
    assert len(trades) >= 1


@pytest.mark.integration
async def test_get_closed_trades_for_account_date_range_excludes(db_session: AsyncSession):
    user = await _make_user(db_session)
    portfolio = await _make_portfolio(db_session, user.id)
    account = await _make_account(db_session, user.id, portfolio.id)
    await _make_closed_trade(db_session, user.id, account.id)
    repo = MetricsRepository(db_session)

    # Filter to a range that excludes the trade
    from_dt = datetime(2025, 1, 1, tzinfo=UTC)
    trades = await repo.get_closed_trades_for_account(
        account_id=account.id,
        portfolio_id=portfolio.id,
        user_id=user.id,
        from_dt=from_dt,
    )
    assert len(trades) == 0


@pytest.mark.integration
async def test_get_closed_trades_for_user_empty(db_session: AsyncSession):
    user = await _make_user(db_session)
    portfolio = await _make_portfolio(db_session, user.id)
    repo = MetricsRepository(db_session)

    trades = await repo.get_closed_trades_for_user(
        user_id=user.id,
        portfolio_id=portfolio.id,
    )
    assert trades == []


@pytest.mark.integration
async def test_get_closed_trades_for_user_returns_data(db_session: AsyncSession):
    user = await _make_user(db_session)
    portfolio = await _make_portfolio(db_session, user.id)
    account = await _make_account(db_session, user.id, portfolio.id)
    await _make_closed_trade(db_session, user.id, account.id)
    repo = MetricsRepository(db_session)

    trades = await repo.get_closed_trades_for_user(
        user_id=user.id,
        portfolio_id=portfolio.id,
    )
    assert len(trades) >= 1


@pytest.mark.integration
async def test_get_closed_trades_for_user_with_account_filter(db_session: AsyncSession):
    user = await _make_user(db_session)
    portfolio = await _make_portfolio(db_session, user.id)
    account = await _make_account(db_session, user.id, portfolio.id)
    await _make_closed_trade(db_session, user.id, account.id)
    repo = MetricsRepository(db_session)

    trades = await repo.get_closed_trades_for_user(
        user_id=user.id,
        portfolio_id=portfolio.id,
        account_id=account.id,
    )
    assert len(trades) >= 1


@pytest.mark.integration
async def test_get_closed_trades_for_user_with_date_filters(db_session: AsyncSession):
    user = await _make_user(db_session)
    portfolio = await _make_portfolio(db_session, user.id)
    account = await _make_account(db_session, user.id, portfolio.id)
    await _make_closed_trade(db_session, user.id, account.id)
    repo = MetricsRepository(db_session)

    from_dt = datetime(2024, 1, 1, tzinfo=UTC)
    to_dt = datetime(2024, 12, 31, tzinfo=UTC)
    trades = await repo.get_closed_trades_for_user(
        user_id=user.id,
        portfolio_id=portfolio.id,
        from_dt=from_dt,
        to_dt=to_dt,
    )
    assert len(trades) >= 1
