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

"""Integration tests for PortfolioRepository."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account, AccountType
from app.models.portfolio import Portfolio
from app.models.trade import AssetClass, Direction, Trade
from app.models.user import User
from app.repositories.portfolio_repository import PortfolioRepository
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate


def _make_user(suffix: str) -> User:
    return User(
        username=f"portfolio_repo_{suffix}",
        email=f"portfolio_repo_{suffix}@example.com",
        hashed_password="not-used-in-tests",
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_portfolio_repository_crud_and_list_order(
    db_session: AsyncSession,
) -> None:
    owner = _make_user("owner")
    db_session.add(owner)
    await db_session.flush()

    repo = PortfolioRepository(db_session)

    first = await repo.create(
        owner.id,
        PortfolioCreate(name="Alpha", base_currency="USD", color_hex="#112233"),
    )
    second = await repo.create(
        owner.id,
        PortfolioCreate(name="Beta", base_currency="EUR", color_hex="#445566"),
    )

    fetched = await repo.get_by_id(first.id, owner.id)
    assert fetched is not None
    assert fetched.name == "Alpha"

    listed = await repo.list_by_user(owner.id)
    assert [item.id for item in listed] == [first.id, second.id]

    updated = await repo.update(first, PortfolioUpdate(name="Alpha Renamed"))
    assert updated.name == "Alpha Renamed"

    await repo.delete(second)
    deleted = await repo.get_by_id(second.id, owner.id)
    assert deleted is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_portfolio_repository_enforces_name_uniqueness_per_user(
    db_session: AsyncSession,
) -> None:
    owner = _make_user("unique")
    db_session.add(owner)
    await db_session.flush()

    repo = PortfolioRepository(db_session)
    await repo.create(
        owner.id,
        PortfolioCreate(name="Main", base_currency="USD", color_hex="#123456"),
    )

    with pytest.raises(IntegrityError):
        await repo.create(
            owner.id,
            PortfolioCreate(name="Main", base_currency="USD", color_hex="#654321"),
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_portfolio_repository_has_accounts_and_has_trades(
    db_session: AsyncSession,
) -> None:
    owner = _make_user("flags")
    db_session.add(owner)
    await db_session.flush()

    portfolio = Portfolio(
        user_id=owner.id,
        name="Flag Portfolio",
        base_currency="USD",
        color_hex="#AA11CC",
    )
    db_session.add(portfolio)
    await db_session.flush()

    repo = PortfolioRepository(db_session)

    assert await repo.has_accounts(portfolio.id) is False
    assert await repo.has_trades(portfolio.id) is False

    account = Account(
        user_id=owner.id,
        portfolio_id=portfolio.id,
        name="Owner Account",
        type=AccountType.MANUAL,
        currency="USD",
    )
    db_session.add(account)
    await db_session.flush()

    assert await repo.has_accounts(portfolio.id) is True
    assert await repo.has_trades(portfolio.id) is False

    trade = Trade(
        user_id=owner.id,
        account_id=account.id,
        symbol="AAPL",
        direction=Direction.LONG,
        asset_class=AssetClass.EQUITY,
        quantity=Decimal("1"),
        entry_price=Decimal("10"),
        opened_at=datetime.now(UTC),
        position_id=uuid.uuid4(),
        commission=Decimal("0"),
        multiplier=1,
        currency="USD",
        is_manually_edited=False,
    )
    db_session.add(trade)
    await db_session.flush()

    assert await repo.has_trades(portfolio.id) is True
