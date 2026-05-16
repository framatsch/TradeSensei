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

"""Integration regressions for repository ownership guards."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account, AccountType
from app.models.account_property import AccountProperty
from app.models.portfolio import Portfolio
from app.models.trade import AssetClass, Direction, Trade
from app.models.user import User
from app.repositories.account_repository import AccountRepository
from app.repositories.trade_repository import TradeRepository
from app.schemas.account import AccountSettings


def _make_user(label: str) -> User:
    return User(
        username=f"ownership_reg_{label}_{uuid.uuid4().hex[:6]}",
        email=f"ownership_reg_{label}_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="not-used",
    )


async def _setup_owned_account(db_session: AsyncSession) -> tuple[User, User, Account]:
    owner = _make_user("owner")
    other = _make_user("other")
    db_session.add_all([owner, other])
    await db_session.flush()

    portfolio = Portfolio(
        user_id=owner.id,
        name="Owner Portfolio",
        base_currency="USD",
        color_hex="#123456",
    )
    db_session.add(portfolio)
    await db_session.flush()

    account = Account(
        user_id=owner.id,
        portfolio_id=portfolio.id,
        name="Owner Account",
        type=AccountType.MANUAL,
        currency="USD",
    )
    db_session.add(account)
    await db_session.flush()

    return owner, other, account


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_settings_non_owner_does_not_write(
    db_session: AsyncSession,
) -> None:
    owner, other, account = await _setup_owned_account(db_session)
    _ = owner
    repo = AccountRepository(db_session)

    await repo.update_settings(
        account_id=account.id,
        user_id=other.id,
        settings=AccountSettings(sync_days=45),
    )

    refreshed = await db_session.get(Account, account.id)
    assert refreshed is not None
    assert refreshed.settings is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upsert_property_non_owner_does_not_write(
    db_session: AsyncSession,
) -> None:
    owner, other, account = await _setup_owned_account(db_session)
    _ = owner
    repo = AccountRepository(db_session)

    await repo.upsert_property(
        account_id=account.id,
        user_id=other.id,
        key="SCHWAB_APP_KEY",
        encrypted_value="ciphertext",
    )

    props = await db_session.execute(
        select(AccountProperty).where(AccountProperty.account_id == account.id)
    )
    assert list(props.scalars().all()) == []


async def _setup_owned_trade(db_session: AsyncSession) -> tuple[User, User, Trade]:
    owner, other, account = await _setup_owned_account(db_session)
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
    return owner, other, trade


@pytest.mark.integration
@pytest.mark.asyncio
async def test_close_open_lot_non_owner_updates_zero_rows(
    db_session: AsyncSession,
) -> None:
    owner, other, trade = await _setup_owned_trade(db_session)
    _ = owner
    repo = TradeRepository(db_session)

    await repo.close_open_lot(
        trade_id=trade.id,
        user_id=other.id,
        exit_price=Decimal("12"),
        closed_at=datetime.now(UTC),
        pnl=Decimal("2"),
        pnl_eur=Decimal("2"),
        net_pnl=Decimal("2"),
        net_pnl_eur=Decimal("2"),
        commission_add=Decimal("1"),
        quantity=Decimal("1"),
    )

    refreshed = await db_session.get(Trade, trade.id)
    assert refreshed is not None
    assert refreshed.closed_at is None
    assert refreshed.exit_price is None
    assert refreshed.pnl is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fill_orphaned_lot_non_owner_updates_zero_rows(
    db_session: AsyncSession,
) -> None:
    owner, other, trade = await _setup_owned_trade(db_session)
    _ = owner
    trade.entry_price = Decimal("0.001")
    trade.closed_at = datetime.now(UTC)
    await db_session.flush()

    repo = TradeRepository(db_session)
    new_opened_at = datetime.now(UTC)
    await repo.fill_orphaned_lot(
        trade_id=trade.id,
        user_id=other.id,
        entry_price=Decimal("10"),
        opened_at=new_opened_at,
        pnl=Decimal("2"),
        pnl_eur=Decimal("2"),
        net_pnl=Decimal("2"),
        net_pnl_eur=Decimal("2"),
        commission_add=Decimal("1"),
        quantity=Decimal("1"),
    )

    refreshed = await db_session.get(Trade, trade.id)
    assert refreshed is not None
    assert refreshed.entry_price == Decimal("0.001")
    assert refreshed.opened_at != new_opened_at
