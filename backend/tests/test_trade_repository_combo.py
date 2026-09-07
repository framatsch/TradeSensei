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
from app.models.trade_note import TradeNote
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


@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_by_user_account_preserves_protected_trades(
    db_session: AsyncSession,
) -> None:
    user = User(
        username=f"delete_guard_{uuid.uuid4().hex[:8]}",
        email=f"delete_guard_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="unused",
    )
    db_session.add(user)
    await db_session.flush()

    portfolio = Portfolio(
        user_id=user.id,
        name="Delete Guard",
        base_currency="USD",
        color_hex="#223344",
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

    protected_trade = Trade(
        user_id=user.id,
        account_id=account.id,
        symbol="PROT_KEEP",
        direction=Direction.LONG,
        asset_class=AssetClass.EQUITY,
        is_manually_edited=True,
        quantity=Decimal("1"),
        entry_price=Decimal("100"),
        opened_at=datetime(2026, 8, 1, tzinfo=UTC),
        commission=Decimal("0"),
        multiplier=1,
    )
    user_modified_only_trade = Trade(
        user_id=user.id,
        account_id=account.id,
        symbol="USERMOD_KEEP",
        direction=Direction.LONG,
        asset_class=AssetClass.EQUITY,
        is_manually_edited=False,
        quantity=Decimal("1"),
        entry_price=Decimal("101"),
        opened_at=datetime(2026, 8, 2, tzinfo=UTC),
        commission=Decimal("0"),
        multiplier=1,
    )
    deletable_trade = Trade(
        user_id=user.id,
        account_id=account.id,
        symbol="DELETE_ME",
        direction=Direction.LONG,
        asset_class=AssetClass.EQUITY,
        is_manually_edited=False,
        quantity=Decimal("1"),
        entry_price=Decimal("102"),
        opened_at=datetime(2026, 8, 3, tzinfo=UTC),
        commission=Decimal("0"),
        multiplier=1,
    )
    db_session.add_all([protected_trade, user_modified_only_trade, deletable_trade])
    await db_session.flush()

    db_session.add_all(
        [
            LogicalExecution(
                user_id=user.id,
                account_id=account.id,
                trade_id=user_modified_only_trade.id,
                symbol="USERMOD_KEEP",
                conid="901001",
                asset_class=AssetClass.EQUITY,
                direction=Direction.LONG,
                quantity=Decimal("1"),
                price=Decimal("101"),
                commission=Decimal("0"),
                executed_at=datetime(2026, 8, 2, 9, 0, tzinfo=UTC),
                origin=EXECUTION_ORIGIN_IMPORTED,
                deleted=False,
                user_modified=True,
                multiplier=1,
            ),
            LogicalExecution(
                user_id=user.id,
                account_id=account.id,
                trade_id=deletable_trade.id,
                symbol="DELETE_ME",
                conid="901002",
                asset_class=AssetClass.EQUITY,
                direction=Direction.LONG,
                quantity=Decimal("1"),
                price=Decimal("102"),
                commission=Decimal("0"),
                executed_at=datetime(2026, 8, 3, 9, 0, tzinfo=UTC),
                origin=EXECUTION_ORIGIN_IMPORTED,
                deleted=False,
                user_modified=False,
                multiplier=1,
            ),
        ]
    )
    await db_session.flush()

    repo = TradeRepository(db_session)
    deleted = await repo.delete_by_user_account(
        user_id=user.id,
        account_id=account.id,
        include_manually_edited=False,
    )
    await db_session.flush()

    assert deleted == 1

    remaining = await repo.list_by_user_account(user.id, account.id)
    remaining_symbols = {trade.symbol for trade in remaining}
    assert "PROT_KEEP" in remaining_symbols
    assert "USERMOD_KEEP" in remaining_symbols
    assert "DELETE_ME" not in remaining_symbols


@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_by_user_account_preserves_trade_protected_by_note_only(
    db_session: AsyncSession,
) -> None:
    user = User(
        username=f"note_guard_{uuid.uuid4().hex[:8]}",
        email=f"note_guard_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="unused",
    )
    db_session.add(user)
    await db_session.flush()

    portfolio = Portfolio(
        user_id=user.id,
        name="Note Guard",
        base_currency="USD",
        color_hex="#556677",
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

    note_protected_trade = Trade(
        user_id=user.id,
        account_id=account.id,
        symbol="NOTE_KEEP",
        direction=Direction.LONG,
        asset_class=AssetClass.EQUITY,
        is_manually_edited=True,
        quantity=Decimal("1"),
        entry_price=Decimal("103"),
        opened_at=datetime(2026, 8, 4, tzinfo=UTC),
        commission=Decimal("0"),
        multiplier=1,
    )
    deletable_trade = Trade(
        user_id=user.id,
        account_id=account.id,
        symbol="DELETE_OTHER",
        direction=Direction.LONG,
        asset_class=AssetClass.EQUITY,
        is_manually_edited=False,
        quantity=Decimal("1"),
        entry_price=Decimal("104"),
        opened_at=datetime(2026, 8, 5, tzinfo=UTC),
        commission=Decimal("0"),
        multiplier=1,
    )
    db_session.add_all([note_protected_trade, deletable_trade])
    await db_session.flush()

    db_session.add(
        TradeNote(
            trade_id=note_protected_trade.id,
            user_id=user.id,
            content="metadata-only protection",
        )
    )
    db_session.add_all(
        [
            LogicalExecution(
                user_id=user.id,
                account_id=account.id,
                trade_id=note_protected_trade.id,
                symbol="NOTE_KEEP",
                conid="901010",
                asset_class=AssetClass.EQUITY,
                direction=Direction.LONG,
                quantity=Decimal("1"),
                price=Decimal("103"),
                commission=Decimal("0"),
                executed_at=datetime(2026, 8, 4, 9, 0, tzinfo=UTC),
                origin=EXECUTION_ORIGIN_IMPORTED,
                deleted=False,
                user_modified=False,
                multiplier=1,
            ),
            LogicalExecution(
                user_id=user.id,
                account_id=account.id,
                trade_id=deletable_trade.id,
                symbol="DELETE_OTHER",
                conid="901011",
                asset_class=AssetClass.EQUITY,
                direction=Direction.LONG,
                quantity=Decimal("1"),
                price=Decimal("104"),
                commission=Decimal("0"),
                executed_at=datetime(2026, 8, 5, 9, 0, tzinfo=UTC),
                origin=EXECUTION_ORIGIN_IMPORTED,
                deleted=False,
                user_modified=False,
                multiplier=1,
            ),
        ]
    )
    await db_session.flush()

    repo = TradeRepository(db_session)
    deleted = await repo.delete_by_user_account(
        user_id=user.id,
        account_id=account.id,
        include_manually_edited=False,
    )
    await db_session.flush()

    assert deleted == 1

    remaining = await repo.list_by_user_account(user.id, account.id)
    remaining_symbols = {trade.symbol for trade in remaining}
    assert "NOTE_KEEP" in remaining_symbols
    assert "DELETE_OTHER" not in remaining_symbols
