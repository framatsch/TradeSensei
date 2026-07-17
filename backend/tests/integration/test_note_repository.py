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

"""Integration tests for NoteRepository."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account, AccountType
from app.models.portfolio import Portfolio
from app.models.trade import AssetClass, Direction, Trade
from app.models.user import User
from app.repositories.note_repository import NoteRepository
from app.schemas.note import TradeNoteCreate, TradeNoteUpdate

pytestmark = pytest.mark.asyncio


async def _make_user(session: AsyncSession) -> User:
    user = User(username=f"u_{uuid.uuid4().hex[:8]}", email=f"{uuid.uuid4().hex}@test.com", hashed_password="x")
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


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
        symbol="TSLA",
        direction=Direction.LONG,
        asset_class=AssetClass.EQUITY,
        quantity=Decimal("5"),
        entry_price=Decimal("200"),
        opened_at=datetime(2024, 3, 1, 9, 30, tzinfo=timezone.utc),
        currency="USD",
    )
    session.add(trade)
    await session.flush()
    await session.refresh(trade)
    return trade


@pytest.mark.integration
async def test_create_and_get_by_id(db_session: AsyncSession):
    user = await _make_user(db_session)
    trade = await _make_trade(db_session, user.id)
    repo = NoteRepository(db_session)

    note = await repo.create(
        data=TradeNoteCreate(content="First note"),
        trade_id=trade.id,
        user_id=user.id,
    )
    assert note.id is not None
    assert note.content == "First note"

    fetched = await repo.get_by_id(note_id=note.id, trade_id=trade.id, user_id=user.id)
    assert fetched is not None
    assert fetched.id == note.id


@pytest.mark.integration
async def test_get_by_id_not_found(db_session: AsyncSession):
    user = await _make_user(db_session)
    trade = await _make_trade(db_session, user.id)
    repo = NoteRepository(db_session)

    result = await repo.get_by_id(note_id=uuid.uuid4(), trade_id=trade.id, user_id=user.id)
    assert result is None


@pytest.mark.integration
async def test_get_by_id_wrong_user(db_session: AsyncSession):
    user = await _make_user(db_session)
    other = await _make_user(db_session)
    trade = await _make_trade(db_session, user.id)
    repo = NoteRepository(db_session)

    note = await repo.create(data=TradeNoteCreate(content="Secret"), trade_id=trade.id, user_id=user.id)
    result = await repo.get_by_id(note_id=note.id, trade_id=trade.id, user_id=other.id)
    assert result is None


@pytest.mark.integration
async def test_list_by_trade(db_session: AsyncSession):
    user = await _make_user(db_session)
    trade = await _make_trade(db_session, user.id)
    repo = NoteRepository(db_session)

    await repo.create(data=TradeNoteCreate(content="Note 1"), trade_id=trade.id, user_id=user.id)
    await repo.create(data=TradeNoteCreate(content="Note 2"), trade_id=trade.id, user_id=user.id)

    notes = await repo.list_by_trade(trade_id=trade.id, user_id=user.id)
    assert len(notes) == 2
    contents = [n.content for n in notes]
    assert "Note 1" in contents
    assert "Note 2" in contents


@pytest.mark.integration
async def test_list_by_trade_empty(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = NoteRepository(db_session)

    notes = await repo.list_by_trade(trade_id=uuid.uuid4(), user_id=user.id)
    assert notes == []


@pytest.mark.integration
async def test_update_note(db_session: AsyncSession):
    user = await _make_user(db_session)
    trade = await _make_trade(db_session, user.id)
    repo = NoteRepository(db_session)

    note = await repo.create(data=TradeNoteCreate(content="Original"), trade_id=trade.id, user_id=user.id)
    updated = await repo.update(note=note, data=TradeNoteUpdate(content="Updated"))
    assert updated.content == "Updated"


@pytest.mark.integration
async def test_delete_note(db_session: AsyncSession):
    user = await _make_user(db_session)
    trade = await _make_trade(db_session, user.id)
    repo = NoteRepository(db_session)

    note = await repo.create(data=TradeNoteCreate(content="To Delete"), trade_id=trade.id, user_id=user.id)
    note_id = note.id

    await repo.delete(note=note)
    result = await repo.get_by_id(note_id=note_id, trade_id=trade.id, user_id=user.id)
    assert result is None
