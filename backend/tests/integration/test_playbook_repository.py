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

"""Integration tests for PlaybookRepository."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.playbook_repository import PlaybookRepository
from app.schemas.playbook import PlaybookCreate, PlaybookUpdate

pytestmark = pytest.mark.asyncio


async def _make_user(session: AsyncSession) -> User:
    user = User(username=f"u_{uuid.uuid4().hex[:8]}", email=f"{uuid.uuid4().hex}@test.com", hashed_password="x")
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


@pytest.mark.integration
async def test_create_and_get_by_id(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = PlaybookRepository(db_session)

    playbook = await repo.create(PlaybookCreate(name="Breakout Long"), user_id=user.id)
    assert playbook.id is not None
    assert playbook.name == "Breakout Long"

    fetched = await repo.get_by_id(playbook_id=playbook.id, user_id=user.id)
    assert fetched is not None
    assert fetched.id == playbook.id


@pytest.mark.integration
async def test_get_by_id_not_found(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = PlaybookRepository(db_session)

    result = await repo.get_by_id(playbook_id=uuid.uuid4(), user_id=user.id)
    assert result is None


@pytest.mark.integration
async def test_get_by_id_wrong_user(db_session: AsyncSession):
    user = await _make_user(db_session)
    other = await _make_user(db_session)
    repo = PlaybookRepository(db_session)

    playbook = await repo.create(PlaybookCreate(name="My Strategy"), user_id=user.id)
    result = await repo.get_by_id(playbook_id=playbook.id, user_id=other.id)
    assert result is None


@pytest.mark.integration
async def test_get_by_name(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = PlaybookRepository(db_session)

    await repo.create(PlaybookCreate(name="VWAP Fade"), user_id=user.id)
    result = await repo.get_by_name("VWAP Fade", user_id=user.id)
    assert result is not None
    assert result.name == "VWAP Fade"


@pytest.mark.integration
async def test_get_by_name_not_found(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = PlaybookRepository(db_session)

    result = await repo.get_by_name("Nonexistent", user_id=user.id)
    assert result is None


@pytest.mark.integration
async def test_list_by_user(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = PlaybookRepository(db_session)

    await repo.create(PlaybookCreate(name="Strategy A"), user_id=user.id)
    await repo.create(PlaybookCreate(name="Strategy B"), user_id=user.id)

    playbooks = await repo.list_by_user(user.id)
    names = [p.name for p in playbooks]
    assert "Strategy A" in names
    assert "Strategy B" in names


@pytest.mark.integration
async def test_list_by_user_empty(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = PlaybookRepository(db_session)

    playbooks = await repo.list_by_user(user.id)
    assert playbooks == []


@pytest.mark.integration
async def test_update_playbook(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = PlaybookRepository(db_session)

    playbook = await repo.create(PlaybookCreate(name="Old Name"), user_id=user.id)
    updated = await repo.update(playbook=playbook, data=PlaybookUpdate(name="New Name"))
    assert updated.name == "New Name"


@pytest.mark.integration
async def test_update_playbook_description(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = PlaybookRepository(db_session)

    playbook = await repo.create(PlaybookCreate(name="Described"), user_id=user.id)
    updated = await repo.update(playbook=playbook, data=PlaybookUpdate(description="New desc"))
    assert updated.description == "New desc"


@pytest.mark.integration
async def test_delete_playbook(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = PlaybookRepository(db_session)

    playbook = await repo.create(PlaybookCreate(name="Delete Me"), user_id=user.id)
    pid = playbook.id

    await repo.delete(playbook)
    result = await repo.get_by_id(playbook_id=pid, user_id=user.id)
    assert result is None
