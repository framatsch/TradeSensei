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

"""Integration tests for CheckinAnnotationRepository."""

import datetime
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.annotation_definition import AnnotationDefinition
from app.models.daily_checkin import DailyCheckin
from app.models.user import User
from app.repositories.checkin_annotation_repository import CheckinAnnotationRepository

pytestmark = pytest.mark.asyncio


async def _make_user(session: AsyncSession) -> User:
    user = User(username=f"u_{uuid.uuid4().hex[:8]}", email=f"{uuid.uuid4().hex}@test.com", hashed_password="x")
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def _make_definition(session: AsyncSession, user_id: uuid.UUID, name: str = "TestDef", ann_type: str = "int") -> AnnotationDefinition:
    defn = AnnotationDefinition(
        user_id=user_id,
        name=name,
        type=ann_type,
        scope="checkins",
        is_archived=False,
        scale_labels={},
    )
    session.add(defn)
    await session.flush()
    await session.refresh(defn)
    return defn


async def _make_checkin(session: AsyncSession, user_id: uuid.UUID) -> DailyCheckin:
    checkin = DailyCheckin(user_id=user_id, date=datetime.date.today())
    session.add(checkin)
    await session.flush()
    await session.refresh(checkin)
    return checkin


@pytest.mark.integration
async def test_assign_and_list_for_checkin(db_session: AsyncSession):
    user = await _make_user(db_session)
    defn = await _make_definition(db_session, user.id, name="Mood")
    checkin = await _make_checkin(db_session, user.id)
    repo = CheckinAnnotationRepository(db_session)

    assignment = await repo.assign(
        checkin_id=checkin.id,
        annotation_definition_id=defn.id,
        typed_values={"value_int": 7, "value_float": None, "value_bool": None, "value_string": None},
    )

    assert assignment.id is not None
    assert assignment.value_int == 7

    listed = await repo.list_for_checkin(checkin.id)
    assert len(listed) == 1
    assert listed[0].id == assignment.id


@pytest.mark.integration
async def test_list_for_checkin_empty(db_session: AsyncSession):
    repo = CheckinAnnotationRepository(db_session)
    result = await repo.list_for_checkin(uuid.uuid4())
    assert result == []


@pytest.mark.integration
async def test_update_existing_annotation(db_session: AsyncSession):
    user = await _make_user(db_session)
    defn = await _make_definition(db_session, user.id, name="Focus")
    checkin = await _make_checkin(db_session, user.id)
    repo = CheckinAnnotationRepository(db_session)

    await repo.assign(
        checkin_id=checkin.id,
        annotation_definition_id=defn.id,
        typed_values={"value_int": 3, "value_float": None, "value_bool": None, "value_string": None},
    )

    updated = await repo.update(
        checkin_id=checkin.id,
        annotation_definition_id=defn.id,
        typed_values={"value_int": 9, "value_float": None, "value_bool": None, "value_string": None},
    )

    assert updated is not None
    assert updated.value_int == 9


@pytest.mark.integration
async def test_update_nonexistent_returns_none(db_session: AsyncSession):
    repo = CheckinAnnotationRepository(db_session)
    result = await repo.update(
        checkin_id=uuid.uuid4(),
        annotation_definition_id=uuid.uuid4(),
        typed_values={"value_int": 5, "value_float": None, "value_bool": None, "value_string": None},
    )
    assert result is None


@pytest.mark.integration
async def test_remove_existing_annotation(db_session: AsyncSession):
    user = await _make_user(db_session)
    defn = await _make_definition(db_session, user.id, name="Remove Me")
    checkin = await _make_checkin(db_session, user.id)
    repo = CheckinAnnotationRepository(db_session)

    await repo.assign(
        checkin_id=checkin.id,
        annotation_definition_id=defn.id,
        typed_values={"value_int": None, "value_float": None, "value_bool": True, "value_string": None},
    )

    removed = await repo.remove(checkin_id=checkin.id, annotation_definition_id=defn.id)
    assert removed is True

    listed = await repo.list_for_checkin(checkin.id)
    assert listed == []


@pytest.mark.integration
async def test_remove_nonexistent_returns_false(db_session: AsyncSession):
    repo = CheckinAnnotationRepository(db_session)
    result = await repo.remove(uuid.uuid4(), uuid.uuid4())
    assert result is False
