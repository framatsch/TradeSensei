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

"""Integration tests for UserRepository."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate

pytestmark = pytest.mark.asyncio


def _unique_username() -> str:
    return f"user_{uuid.uuid4().hex[:10]}"


def _unique_email() -> str:
    return f"{uuid.uuid4().hex[:10]}@test.example.com"


@pytest.mark.integration
async def test_create_and_get_by_id(db_session: AsyncSession):
    repo = UserRepository(db_session)
    data = UserCreate(username=_unique_username(), email=_unique_email(), password="Pass!1234")
    user = await repo.create(data=data, hashed_password="$2b$12$fakehash")

    assert user.id is not None
    assert user.username == data.username

    fetched = await repo.get_by_id(user.id)
    assert fetched is not None
    assert fetched.id == user.id


@pytest.mark.integration
async def test_get_by_id_not_found(db_session: AsyncSession):
    repo = UserRepository(db_session)
    result = await repo.get_by_id(uuid.uuid4())
    assert result is None


@pytest.mark.integration
async def test_get_by_username(db_session: AsyncSession):
    repo = UserRepository(db_session)
    username = _unique_username()
    data = UserCreate(username=username, email=_unique_email(), password="Pass!1234")
    await repo.create(data=data, hashed_password="$2b$12$fakehash")

    fetched = await repo.get_by_username(username)
    assert fetched is not None
    assert fetched.username == username


@pytest.mark.integration
async def test_get_by_username_not_found(db_session: AsyncSession):
    repo = UserRepository(db_session)
    result = await repo.get_by_username("no_such_user_xyz")
    assert result is None


@pytest.mark.integration
async def test_get_by_email(db_session: AsyncSession):
    repo = UserRepository(db_session)
    email = _unique_email()
    data = UserCreate(username=_unique_username(), email=email, password="Pass!1234")
    await repo.create(data=data, hashed_password="$2b$12$fakehash")

    fetched = await repo.get_by_email(email)
    assert fetched is not None
    assert fetched.email == email


@pytest.mark.integration
async def test_get_by_email_not_found(db_session: AsyncSession):
    repo = UserRepository(db_session)
    result = await repo.get_by_email("nonexistent@nope.com")
    assert result is None


@pytest.mark.integration
async def test_get_by_provider_id(db_session: AsyncSession):
    repo = UserRepository(db_session)
    provider_id = f"google_{uuid.uuid4().hex[:10]}"
    user = await repo.create_oauth_user(
        email=_unique_email(),
        username=_unique_username(),
        provider="google",
        provider_id=provider_id,
    )
    assert user.id is not None

    fetched = await repo.get_by_provider_id(provider="google", provider_id=provider_id)
    assert fetched is not None
    assert fetched.id == user.id


@pytest.mark.integration
async def test_get_by_provider_id_not_found(db_session: AsyncSession):
    repo = UserRepository(db_session)
    result = await repo.get_by_provider_id(provider="google", provider_id="no-such-id")
    assert result is None


@pytest.mark.integration
async def test_create_oauth_user(db_session: AsyncSession):
    repo = UserRepository(db_session)
    user = await repo.create_oauth_user(
        email=_unique_email(),
        username=_unique_username(),
        provider="github",
        provider_id="gh_123",
    )
    assert user.id is not None
    assert user.hashed_password is None
    assert user.provider == "github"


@pytest.mark.integration
async def test_link_oauth_account(db_session: AsyncSession):
    repo = UserRepository(db_session)
    data = UserCreate(username=_unique_username(), email=_unique_email(), password="Pass!1234")
    user = await repo.create(data=data, hashed_password="$2b$12$fakehash")

    updated = await repo.link_oauth_account(user=user, provider="google", provider_id="oauth_xyz")
    assert updated.provider == "google"
    assert updated.provider_id == "oauth_xyz"


@pytest.mark.integration
async def test_update_user(db_session: AsyncSession):
    repo = UserRepository(db_session)
    data = UserCreate(username=_unique_username(), email=_unique_email(), password="Pass!1234")
    user = await repo.create(data=data, hashed_password="$2b$12$fakehash")

    new_email = _unique_email()
    updated = await repo.update(user=user, data={"email": new_email})
    assert updated.email == new_email


@pytest.mark.integration
async def test_delete_user(db_session: AsyncSession):
    repo = UserRepository(db_session)
    data = UserCreate(username=_unique_username(), email=_unique_email(), password="Pass!1234")
    user = await repo.create(data=data, hashed_password="$2b$12$fakehash")
    uid = user.id

    await repo.delete(user=user)
    result = await repo.get_by_id(uid)
    assert result is None


@pytest.mark.integration
async def test_increment_token_version(db_session: AsyncSession):
    repo = UserRepository(db_session)
    data = UserCreate(username=_unique_username(), email=_unique_email(), password="Pass!1234")
    user = await repo.create(data=data, hashed_password="$2b$12$fakehash")
    original_version = user.refresh_token_version

    await repo.increment_token_version(user=user)
    assert user.refresh_token_version == original_version + 1
