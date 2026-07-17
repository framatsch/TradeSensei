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

"""Integration tests for AnnotationDefinitionRepository."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.annotation_definition_repository import AnnotationDefinitionRepository
from app.schemas.annotation_definition import AnnotationDefinitionCreate, AnnotationDefinitionUpdate

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
    repo = AnnotationDefinitionRepository(db_session)
    payload = AnnotationDefinitionCreate(name="Mood", type="int", scope="checkins")
    definition = await repo.create(user.id, payload)

    assert definition.id is not None
    assert definition.name == "Mood"

    fetched = await repo.get_by_id(user.id, definition.id)
    assert fetched is not None
    assert fetched.id == definition.id


@pytest.mark.integration
async def test_get_by_id_not_found(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = AnnotationDefinitionRepository(db_session)
    result = await repo.get_by_id(user.id, uuid.uuid4())
    assert result is None


@pytest.mark.integration
async def test_get_by_id_wrong_user(db_session: AsyncSession):
    user = await _make_user(db_session)
    other = await _make_user(db_session)
    repo = AnnotationDefinitionRepository(db_session)
    payload = AnnotationDefinitionCreate(name="Focus", type="int", scope="checkins")
    definition = await repo.create(user.id, payload)

    result = await repo.get_by_id(other.id, definition.id)
    assert result is None


@pytest.mark.integration
async def test_list_all_for_user(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = AnnotationDefinitionRepository(db_session)
    await repo.create(user.id, AnnotationDefinitionCreate(name="Ann A", type="bool", scope="trades"))
    await repo.create(user.id, AnnotationDefinitionCreate(name="Ann B", type="int", scope="checkins"))

    results = await repo.list(user.id)
    names = [r.name for r in results]
    assert "Ann A" in names
    assert "Ann B" in names


@pytest.mark.integration
async def test_list_with_scope_filter(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = AnnotationDefinitionRepository(db_session)
    await repo.create(user.id, AnnotationDefinitionCreate(name="Trade Ann", type="bool", scope="trades"))
    await repo.create(user.id, AnnotationDefinitionCreate(name="Checkin Ann", type="int", scope="checkins"))

    trade_results = await repo.list(user.id, scope="trades")
    names = [r.name for r in trade_results]
    assert "Trade Ann" in names
    assert "Checkin Ann" not in names


@pytest.mark.integration
async def test_list_returns_empty_for_other_user(db_session: AsyncSession):
    user = await _make_user(db_session)
    other = await _make_user(db_session)
    repo = AnnotationDefinitionRepository(db_session)
    await repo.create(user.id, AnnotationDefinitionCreate(name="OnlyMine", type="bool", scope="trades"))

    results = await repo.list(other.id)
    names = [r.name for r in results]
    assert "OnlyMine" not in names


@pytest.mark.integration
async def test_update_definition(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = AnnotationDefinitionRepository(db_session)
    definition = await repo.create(user.id, AnnotationDefinitionCreate(name="Old Name", type="int", scope="trades"))

    updated = await repo.update(definition, AnnotationDefinitionUpdate(name="New Name"))
    assert updated.name == "New Name"


@pytest.mark.integration
async def test_archive_and_unarchive(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = AnnotationDefinitionRepository(db_session)
    definition = await repo.create(user.id, AnnotationDefinitionCreate(name="Archivable", type="bool", scope="trades"))

    archived = await repo.archive(definition)
    assert archived.is_archived is True

    # Archived items should not appear in list()
    results = await repo.list(user.id)
    names = [r.name for r in results]
    assert "Archivable" not in names

    unarchived = await repo.unarchive(archived)
    assert unarchived.is_archived is False


@pytest.mark.integration
async def test_list_including_archived(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = AnnotationDefinitionRepository(db_session)
    definition = await repo.create(user.id, AnnotationDefinitionCreate(name="ToArchive", type="bool", scope="trades"))
    await repo.archive(definition)

    all_results = await repo.list_including_archived(user.id)
    names = [r.name for r in all_results]
    assert "ToArchive" in names


@pytest.mark.integration
async def test_list_including_archived_with_scope(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = AnnotationDefinitionRepository(db_session)
    await repo.create(user.id, AnnotationDefinitionCreate(name="Scoped Archive", type="bool", scope="trades"))

    results = await repo.list_including_archived(user.id, scope="trades")
    names = [r.name for r in results]
    assert "Scoped Archive" in names


@pytest.mark.integration
async def test_count_assignments_empty(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = AnnotationDefinitionRepository(db_session)
    definition = await repo.create(user.id, AnnotationDefinitionCreate(name="Count Test", type="int", scope="trades"))

    trade_count, checkin_count = await repo.count_assignments(definition.id)
    assert trade_count == 0
    assert checkin_count == 0


@pytest.mark.integration
async def test_delete_definition(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = AnnotationDefinitionRepository(db_session)
    definition = await repo.create(user.id, AnnotationDefinitionCreate(name="To Delete", type="bool", scope="trades"))
    def_id = definition.id

    await repo.delete(definition)

    result = await repo.get_by_id(user.id, def_id)
    assert result is None


@pytest.mark.integration
async def test_delete_assignments_no_op_on_empty(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = AnnotationDefinitionRepository(db_session)
    definition = await repo.create(user.id, AnnotationDefinitionCreate(name="Del Assign", type="int", scope="trades"))

    # Should not raise even with no assignments
    await repo.delete_assignments(definition.id)


@pytest.mark.integration
async def test_seed_defaults_creates_entries(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = AnnotationDefinitionRepository(db_session)
    await repo.seed_defaults(user.id)

    results = await repo.list_including_archived(user.id)
    assert len(results) >= 5  # 5 defaults defined in repository


@pytest.mark.integration
async def test_seed_defaults_idempotent(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = AnnotationDefinitionRepository(db_session)
    await repo.seed_defaults(user.id)
    await repo.seed_defaults(user.id)  # Second call should not duplicate

    results = await repo.list_including_archived(user.id)
    # Count 'Mood Level' entries — should only appear once
    mood_count = sum(1 for r in results if r.name == "Mood Level")
    assert mood_count == 1


@pytest.mark.integration
async def test_list_with_usage_counts_no_data(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = AnnotationDefinitionRepository(db_session)
    await repo.create(user.id, AnnotationDefinitionCreate(name="Usage Test", type="int", scope="trades"))

    results = await repo.list_with_usage_counts(user.id)
    assert len(results) >= 1
    # Verify tuple structure: (AnnotationDefinition, int)
    defn, count = results[0]
    assert isinstance(count, int)
    assert count == 0


@pytest.mark.integration
async def test_list_with_usage_counts_scoped(db_session: AsyncSession):
    user = await _make_user(db_session)
    repo = AnnotationDefinitionRepository(db_session)
    await repo.create(user.id, AnnotationDefinitionCreate(name="Scoped Usage", type="int", scope="checkins"))

    results = await repo.list_with_usage_counts(user.id, scope="checkins")
    names = [r[0].name for r in results]
    assert "Scoped Usage" in names
