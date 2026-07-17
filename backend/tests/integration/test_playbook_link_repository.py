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

"""Integration tests for PlaybookLinkRepository."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.playbook import Playbook
from app.models.user import User
from app.repositories.playbook_link_repository import PlaybookLinkRepository

pytestmark = pytest.mark.asyncio


async def _make_user(session: AsyncSession) -> User:
    user = User(username=f"u_{uuid.uuid4().hex[:8]}", email=f"{uuid.uuid4().hex}@test.com", hashed_password="x")
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def _make_playbook(session: AsyncSession, user_id: uuid.UUID) -> Playbook:
    pb = Playbook(user_id=user_id, name="TestPlaybookLink")
    session.add(pb)
    await session.flush()
    await session.refresh(pb)
    return pb


@pytest.mark.integration
async def test_create_and_list_for_playbook(db_session: AsyncSession):
    user = await _make_user(db_session)
    playbook = await _make_playbook(db_session, user.id)
    repo = PlaybookLinkRepository(db_session)

    link = await repo.create(
        playbook_id=playbook.id,
        user_id=user.id,
        label="Reference Article",
        url="https://example.com/article",
    )
    assert link.id is not None
    assert link.label == "Reference Article"

    listed = await repo.list_for_playbook(playbook.id)
    assert len(listed) == 1
    assert listed[0].id == link.id


@pytest.mark.integration
async def test_list_for_playbook_empty(db_session: AsyncSession):
    repo = PlaybookLinkRepository(db_session)
    result = await repo.list_for_playbook(uuid.uuid4())
    assert result == []


@pytest.mark.integration
async def test_get_link(db_session: AsyncSession):
    user = await _make_user(db_session)
    playbook = await _make_playbook(db_session, user.id)
    repo = PlaybookLinkRepository(db_session)

    link = await repo.create(
        playbook_id=playbook.id,
        user_id=user.id,
        label="Wiki",
        url="https://wiki.example.com",
    )

    fetched = await repo.get(link_id=link.id, playbook_id=playbook.id)
    assert fetched is not None
    assert fetched.url == "https://wiki.example.com"


@pytest.mark.integration
async def test_get_link_not_found(db_session: AsyncSession):
    repo = PlaybookLinkRepository(db_session)
    result = await repo.get(link_id=uuid.uuid4(), playbook_id=uuid.uuid4())
    assert result is None


@pytest.mark.integration
async def test_delete_link(db_session: AsyncSession):
    user = await _make_user(db_session)
    playbook = await _make_playbook(db_session, user.id)
    repo = PlaybookLinkRepository(db_session)

    link = await repo.create(
        playbook_id=playbook.id,
        user_id=user.id,
        label="Delete Me",
        url="https://delete.example.com",
    )
    link_id = link.id

    await repo.delete(link)
    result = await repo.get(link_id=link_id, playbook_id=playbook.id)
    assert result is None
