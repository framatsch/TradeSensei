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

"""Integration tests for SavedTradeFilterRepository."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.saved_trade_filter import FilterScope
from app.models.user import User
from app.repositories.saved_trade_filter_repository import SavedTradeFilterRepository

pytestmark = pytest.mark.asyncio


async def _make_user(session: AsyncSession) -> User:
    user = User(username=f"u_{uuid.uuid4().hex[:8]}", email=f"{uuid.uuid4().hex}@test.com", hashed_password="x")
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


@pytest.mark.integration
async def test_create_user_filter(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = SavedTradeFilterRepository(db_session)

    f = await repo.create(
        name="My Filter",
        definition={"direction": "LONG"},
        scope=FilterScope.USER,
        owner_id=user.id,
    )
    assert f.id is not None
    assert f.name == "My Filter"
    assert f.scope == FilterScope.USER


@pytest.mark.integration
async def test_create_system_filter(db_session: AsyncSession):
    repo = SavedTradeFilterRepository(db_session)

    f = await repo.create(
        name="Winners Only",
        definition={"pnl_gt": 0},
        scope=FilterScope.SYSTEM,
    )
    assert f.scope == FilterScope.SYSTEM
    assert f.owner_id is None


@pytest.mark.integration
async def test_get_by_id(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = SavedTradeFilterRepository(db_session)

    f = await repo.create(name="Fetchable", definition={}, scope=FilterScope.USER, owner_id=user.id)
    fetched = await repo.get_by_id(f.id)
    assert fetched is not None
    assert fetched.id == f.id


@pytest.mark.integration
async def test_get_by_id_not_found(db_session: AsyncSession):
    repo = SavedTradeFilterRepository(db_session)
    result = await repo.get_by_id(uuid.uuid4())
    assert result is None


@pytest.mark.integration
async def test_get_by_id_and_owner(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = SavedTradeFilterRepository(db_session)

    f = await repo.create(name="Owned", definition={}, scope=FilterScope.USER, owner_id=user.id)
    fetched = await repo.get_by_id_and_owner(f.id, user.id)
    assert fetched is not None


@pytest.mark.integration
async def test_get_by_id_and_owner_wrong_owner(db_session: AsyncSession):
    user = await _make_user(db_session)
    other = await _make_user(db_session)
    repo = SavedTradeFilterRepository(db_session)

    f = await repo.create(name="Owned2", definition={}, scope=FilterScope.USER, owner_id=user.id)
    result = await repo.get_by_id_and_owner(f.id, other.id)
    assert result is None


@pytest.mark.integration
async def test_list_for_user_includes_own_and_system(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = SavedTradeFilterRepository(db_session)

    sys_f = await repo.create(name="SysF", definition={}, scope=FilterScope.SYSTEM)
    user_f = await repo.create(name="UserF", definition={}, scope=FilterScope.USER, owner_id=user.id)

    results = await repo.list_for_user(user.id)
    ids = [r.id for r in results]
    assert sys_f.id in ids
    assert user_f.id in ids


@pytest.mark.integration
async def test_list_for_user_excludes_other_user_filters(db_session: AsyncSession):
    user = await _make_user(db_session)
    other = await _make_user(db_session)
    repo = SavedTradeFilterRepository(db_session)

    other_f = await repo.create(name="OtherUserFilter", definition={}, scope=FilterScope.USER, owner_id=other.id)

    results = await repo.list_for_user(user.id)
    ids = [r.id for r in results]
    assert other_f.id not in ids


@pytest.mark.integration
async def test_update_filter(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = SavedTradeFilterRepository(db_session)

    f = await repo.create(name="Before", definition={"a": 1}, scope=FilterScope.USER, owner_id=user.id)
    updated = await repo.update(f, name="After", definition={"b": 2})
    assert updated.name == "After"
    assert updated.definition == {"b": 2}


@pytest.mark.integration
async def test_update_needs_review(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = SavedTradeFilterRepository(db_session)

    f = await repo.create(name="Review Me", definition={}, scope=FilterScope.USER, owner_id=user.id)
    updated = await repo.update(f, needs_review=True)
    assert updated.needs_review is True


@pytest.mark.integration
async def test_delete_filter(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = SavedTradeFilterRepository(db_session)

    f = await repo.create(name="Delete Me", definition={}, scope=FilterScope.USER, owner_id=user.id)
    fid = f.id

    await repo.delete(fid)
    result = await repo.get_by_id(fid)
    assert result is None
