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

"""Integration tests for combo-specific TradeRepository methods."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account, AccountType
from app.models.logical_execution import EXECUTION_ORIGIN_IMPORTED, LogicalExecution
from app.models.portfolio import Portfolio
from app.models.trade import AssetClass, Direction, Trade
from app.models.user import User
from app.repositories.trade_repository import TradeRepository


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_open_combo_positions_by_user_returns_only_open_combos(
    db_session: AsyncSession,
) -> None:
    user = User(
        username=f"combo_repo_{uuid.uuid4().hex[:8]}",
        email=f"combo_repo_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="unused",
    )
    db_session.add(user)
    await db_session.flush()

    portfolio = Portfolio(
        user_id=user.id,
        name="Combo Repo",
        base_currency="USD",
        color_hex="#112233",
    )
    db_session.add(portfolio)
    await db_session.flush()

    account = Account(
        user_id=user.id,
        portfolio_id=portfolio.id,
        name="IBKR",
        type=AccountType.IBKR,
        currency="USD",
    )
    db_session.add(account)
    await db_session.flush()

    open_combo = Trade(
        user_id=user.id,
        account_id=account.id,
        symbol="QQQ",
        direction=Direction.LONG,
        asset_class=None,
        is_combo=True,
        quantity=None,
        entry_price=None,
        opened_at=datetime(2026, 7, 1, tzinfo=UTC),
        closed_at=None,
        commission=Decimal("1"),
        multiplier=1,
    )
    closed_combo = Trade(
        user_id=user.id,
        account_id=account.id,
        symbol="META",
        direction=Direction.LONG,
        asset_class=None,
        is_combo=True,
        quantity=None,
        entry_price=None,
        opened_at=datetime(2026, 7, 1, tzinfo=UTC),
        closed_at=datetime(2026, 7, 2, tzinfo=UTC),
        commission=Decimal("1"),
        multiplier=1,
    )
    normal_trade = Trade(
        user_id=user.id,
        account_id=account.id,
        symbol="AAPL",
        direction=Direction.LONG,
        asset_class=AssetClass.EQUITY,
        is_combo=False,
        quantity=Decimal("1"),
        entry_price=Decimal("100"),
        opened_at=datetime(2026, 7, 1, tzinfo=UTC),
        closed_at=None,
        commission=Decimal("1"),
        multiplier=1,
    )
    db_session.add_all([open_combo, closed_combo, normal_trade])
    await db_session.flush()

    opening_leg = LogicalExecution(
        user_id=user.id,
        account_id=account.id,
        trade_id=open_combo.id,
        symbol="QQQ",
        conid="878467678",
        asset_class=AssetClass.OPTION,
        direction=Direction.LONG,
        quantity=Decimal("1"),
        price=Decimal("19.63"),
        commission=Decimal("1"),
        executed_at=datetime(2026, 7, 1, 9, 0, tzinfo=UTC),
        origin=EXECUTION_ORIGIN_IMPORTED,
        deleted=False,
        user_modified=False,
        open_close="O",
        multiplier=100,
    )
    db_session.add(opening_leg)
    await db_session.flush()

    repo = TradeRepository(db_session)
    rows = await repo.list_open_combo_positions_by_user(
        user_id=user.id,
        portfolio_id=portfolio.id,
        account_id=account.id,
    )

    assert len(rows) == 1
    assert rows[0].id == open_combo.id
    assert rows[0].is_combo is True
