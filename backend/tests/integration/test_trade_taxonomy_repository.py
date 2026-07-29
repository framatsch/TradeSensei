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

"""Integration tests for TradeTaxonomyRepository."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account, AccountType
from app.models.portfolio import Portfolio
from app.models.taxonomy import Taxonomy
from app.models.trade import AssetClass, Direction, Trade
from app.models.user import User
from app.repositories.trade_taxonomy_repository import TradeTaxonomyRepository

pytestmark = pytest.mark.asyncio


async def _make_user(session: AsyncSession) -> User:
    user = User(username=f"u_{uuid.uuid4().hex[:8]}", email=f"{uuid.uuid4().hex}@test.com", hashed_password="x")
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def _make_taxonomy(session: AsyncSession, user_id: uuid.UUID, name: str = "Tag") -> Taxonomy:
    tax = Taxonomy(user_id=user_id, name=name, scope="trades", color_hex="#FF5733")
    session.add(tax)
    await session.flush()
    await session.refresh(tax)
    return tax


async def _make_trade(session: AsyncSession, user_id: uuid.UUID) -> Trade:
    portfolio = Portfolio(user_id=user_id, name="P", base_currency="USD")
    session.add(portfolio)
    await session.flush()
    account = Account(user_id=user_id, portfolio_id=portfolio.id, name="A", type=AccountType.MANUAL, currency="USD")
    session.add(account)
    await session.flush()
    trade = Trade(
        user_id=user_id,
        account_id=account.id,
        symbol="NVDA",
        direction=Direction.LONG,
        asset_class=AssetClass.EQUITY,
        quantity=Decimal("1"),
        entry_price=Decimal("500"),
        opened_at=datetime(2024, 5, 1, 9, 30, tzinfo=UTC),
        currency="USD",
    )
    session.add(trade)
    await session.flush()
    await session.refresh(trade)
    return trade


@pytest.mark.integration
async def test_assign_and_list_for_trade(db_session: AsyncSession):
    user = await _make_user(db_session)
    tax = await _make_taxonomy(db_session, user.id, name="Momentum")
    trade = await _make_trade(db_session, user.id)
    repo = TradeTaxonomyRepository(db_session)

    assignment = await repo.assign(trade_id=trade.id, taxonomy_id=tax.id)
    assert assignment.trade_id == trade.id
    assert assignment.taxonomy_id == tax.id

    listed = await repo.list_for_trade(trade.id)
    assert len(listed) == 1


@pytest.mark.integration
async def test_list_for_trade_empty(db_session: AsyncSession):
    repo = TradeTaxonomyRepository(db_session)
    result = await repo.list_for_trade(uuid.uuid4())
    assert result == []


@pytest.mark.integration
async def test_remove_existing(db_session: AsyncSession):
    user = await _make_user(db_session)
    tax = await _make_taxonomy(db_session, user.id, name="Reversal")
    trade = await _make_trade(db_session, user.id)
    repo = TradeTaxonomyRepository(db_session)

    await repo.assign(trade_id=trade.id, taxonomy_id=tax.id)
    removed = await repo.remove(trade_id=trade.id, taxonomy_id=tax.id)
    assert removed is True

    listed = await repo.list_for_trade(trade.id)
    assert listed == []


@pytest.mark.integration
async def test_remove_nonexistent_returns_false(db_session: AsyncSession):
    repo = TradeTaxonomyRepository(db_session)
    result = await repo.remove(uuid.uuid4(), uuid.uuid4())
    assert result is False
