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

"""Integration tests for CheckinTaxonomyRepository."""

import datetime
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_checkin import DailyCheckin
from app.models.taxonomy import Taxonomy
from app.models.user import User
from app.repositories.checkin_taxonomy_repository import CheckinTaxonomyRepository

pytestmark = pytest.mark.asyncio


async def _make_user(session: AsyncSession) -> User:
    user = User(username=f"u_{uuid.uuid4().hex[:8]}", email=f"{uuid.uuid4().hex}@test.com", hashed_password="x")
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def _make_taxonomy(session: AsyncSession, user_id: uuid.UUID, name: str = "Tag") -> Taxonomy:
    tax = Taxonomy(user_id=user_id, name=name, scope="checkins", color_hex="#000000")
    session.add(tax)
    await session.flush()
    await session.refresh(tax)
    return tax


async def _make_checkin(session: AsyncSession, user_id: uuid.UUID) -> DailyCheckin:
    checkin = DailyCheckin(user_id=user_id, date=datetime.date.today())
    session.add(checkin)
    await session.flush()
    await session.refresh(checkin)
    return checkin


@pytest.mark.integration
async def test_assign_and_list_for_checkin(db_session: AsyncSession):
    user = await _make_user(db_session)
    tax = await _make_taxonomy(db_session, user.id, name="Bullish")
    checkin = await _make_checkin(db_session, user.id)
    repo = CheckinTaxonomyRepository(db_session)

    assignment = await repo.assign(checkin_id=checkin.id, taxonomy_id=tax.id)
    assert assignment.checkin_id == checkin.id
    assert assignment.taxonomy_id == tax.id

    listed = await repo.list_for_checkin(checkin.id)
    assert len(listed) == 1


@pytest.mark.integration
async def test_list_for_checkin_empty(db_session: AsyncSession):
    repo = CheckinTaxonomyRepository(db_session)
    result = await repo.list_for_checkin(uuid.uuid4())
    assert result == []


@pytest.mark.integration
async def test_remove_existing(db_session: AsyncSession):
    user = await _make_user(db_session)
    tax = await _make_taxonomy(db_session, user.id, name="Bearish")
    checkin = await _make_checkin(db_session, user.id)
    repo = CheckinTaxonomyRepository(db_session)

    await repo.assign(checkin_id=checkin.id, taxonomy_id=tax.id)
    removed = await repo.remove(checkin_id=checkin.id, taxonomy_id=tax.id)
    assert removed is True

    listed = await repo.list_for_checkin(checkin.id)
    assert listed == []


@pytest.mark.integration
async def test_remove_nonexistent_returns_false(db_session: AsyncSession):
    repo = CheckinTaxonomyRepository(db_session)
    result = await repo.remove(uuid.uuid4(), uuid.uuid4())
    assert result is False
