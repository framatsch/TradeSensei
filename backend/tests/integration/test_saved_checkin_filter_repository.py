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

"""Integration tests for SavedCheckinFilterRepository."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.saved_checkin_filter_repository import SavedCheckinFilterRepository

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
    repo = SavedCheckinFilterRepository(db_session)

    f = await repo.create(user_id=user.id, name="My Filter", filter_config={"status": "all"}, is_default=False)
    assert f.id is not None
    assert f.name == "My Filter"

    fetched = await repo.get_by_id(f.id)
    assert fetched is not None
    assert fetched.id == f.id


@pytest.mark.integration
async def test_get_by_id_not_found(db_session: AsyncSession):
    repo = SavedCheckinFilterRepository(db_session)
    result = await repo.get_by_id(uuid.uuid4())
    assert result is None


@pytest.mark.integration
async def test_list_by_user(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = SavedCheckinFilterRepository(db_session)

    await repo.create(user_id=user.id, name="Filter A", filter_config={}, is_default=False)
    await repo.create(user_id=user.id, name="Filter B", filter_config={}, is_default=False)

    results = await repo.list_by_user(user.id)
    names = [r.name for r in results]
    assert "Filter A" in names
    assert "Filter B" in names


@pytest.mark.integration
async def test_list_by_user_empty(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = SavedCheckinFilterRepository(db_session)

    results = await repo.list_by_user(user.id)
    assert list(results) == []


@pytest.mark.integration
async def test_update_filter(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = SavedCheckinFilterRepository(db_session)

    f = await repo.create(user_id=user.id, name="Before", filter_config={}, is_default=False)
    updated = await repo.update(filter_id=f.id, name="After")
    assert updated is not None
    assert updated.name == "After"


@pytest.mark.integration
async def test_update_nonexistent_returns_none(db_session: AsyncSession):
    repo = SavedCheckinFilterRepository(db_session)
    result = await repo.update(filter_id=uuid.uuid4(), name="New Name")
    assert result is None


@pytest.mark.integration
async def test_delete_filter(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = SavedCheckinFilterRepository(db_session)

    f = await repo.create(user_id=user.id, name="To Delete", filter_config={}, is_default=False)
    fid = f.id

    removed = await repo.delete(fid)
    assert removed is True

    result = await repo.get_by_id(fid)
    assert result is None


@pytest.mark.integration
async def test_delete_nonexistent_returns_false(db_session: AsyncSession):
    repo = SavedCheckinFilterRepository(db_session)
    result = await repo.delete(uuid.uuid4())
    assert result is False


@pytest.mark.integration
async def test_unset_default(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = SavedCheckinFilterRepository(db_session)

    f = await repo.create(user_id=user.id, name="Default Filter", filter_config={}, is_default=True)
    # Unset all defaults
    await repo.unset_default(user_id=user.id)

    refreshed = await repo.get_by_id(f.id)
    assert refreshed is not None
    assert refreshed.is_default is False


@pytest.mark.integration
async def test_unset_default_with_exclude_id(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = SavedCheckinFilterRepository(db_session)

    f1 = await repo.create(user_id=user.id, name="Default Filter", filter_config={}, is_default=True)
    # Unset excluding f1's id — f1 should remain default
    await repo.unset_default(user_id=user.id, exclude_id=f1.id)

    refreshed = await repo.get_by_id(f1.id)
    assert refreshed is not None
    assert refreshed.is_default is True
