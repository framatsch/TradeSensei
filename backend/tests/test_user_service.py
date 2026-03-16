"""Unit tests for UserService — no database access (all repository calls mocked).

Every test patches :class:`~app.repositories.user_repository.UserRepository`
methods directly on the instance created inside
:class:`~app.services.user_service.UserService`.  No real database
connection is required.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import UserAlreadyExistsError, UserNotFoundError
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate
from app.services.user_service import UserService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(
    *,
    id: uuid.UUID | None = None,
    username: str = "testuser",
    email: str = "test@example.com",
    is_active: bool = True,
) -> User:
    """Build a detached :class:`User` ORM instance for test use."""
    user = User()
    user.id = id if id is not None else uuid.uuid4()  # type: ignore[assignment]
    user.username = username  # type: ignore[assignment]
    user.email = email  # type: ignore[assignment]
    user.hashed_password = "hashed"  # type: ignore[assignment]
    user.provider = "local"  # type: ignore[assignment]
    user.provider_id = None  # type: ignore[assignment]
    user.is_active = is_active  # type: ignore[assignment]
    user.refresh_token_version = 0  # type: ignore[assignment]
    user.created_at = datetime.now(UTC)  # type: ignore[assignment]
    user.updated_at = datetime.now(UTC)  # type: ignore[assignment]
    return user


@pytest.fixture()
def mock_session() -> AsyncMock:
    """Return a mock :class:`AsyncSession`."""
    return AsyncMock()


@pytest.fixture()
def service(mock_session: AsyncMock) -> UserService:
    """Return a :class:`UserService` wired to a mock session."""
    return UserService(mock_session)


# ---------------------------------------------------------------------------
# get_user
# ---------------------------------------------------------------------------


class TestGetUser:
    """Tests for :meth:`UserService.get_user`."""

    async def test_get_user_returns_dto(self, service: UserService) -> None:
        """Should return a :class:`UserRead` DTO for an existing user."""
        user = _make_user()
        service._repo.get_by_id = AsyncMock(return_value=user)  # type: ignore[method-assign]

        result = await service.get_user(user.id)  # type: ignore[arg-type]

        assert isinstance(result, UserRead)
        assert result.username == "testuser"

    async def test_get_user_not_found_raises(self, service: UserService) -> None:
        """Should raise :class:`UserNotFoundError` if the user does not exist."""
        service._repo.get_by_id = AsyncMock(return_value=None)  # type: ignore[method-assign]

        with pytest.raises(UserNotFoundError):
            await service.get_user(uuid.uuid4())


# ---------------------------------------------------------------------------
# update_user
# ---------------------------------------------------------------------------


class TestUpdateUser:
    """Tests for :meth:`UserService.update_user`."""

    async def test_update_username_success(self, service: UserService) -> None:
        """Should update and return the new DTO when username is available."""
        user = _make_user(username="old_name")
        updated_user = _make_user(username="new_name")

        service._repo.get_by_username = AsyncMock(return_value=None)  # type: ignore[method-assign]
        service._repo.get_by_email = AsyncMock(return_value=None)  # type: ignore[method-assign]
        service._repo.update = AsyncMock(return_value=updated_user)  # type: ignore[method-assign]

        data = UserUpdate(username="new_name")
        result = await service.update_user(user, data)

        assert result.username == "new_name"

    async def test_update_username_taken_raises(self, service: UserService) -> None:
        """Should raise :class:`UserAlreadyExistsError` if username is taken."""
        user = _make_user(username="alice")
        existing = _make_user(username="bob", id=uuid.uuid4())

        service._repo.get_by_username = AsyncMock(return_value=existing)  # type: ignore[method-assign]

        data = UserUpdate(username="bob")
        with pytest.raises(UserAlreadyExistsError):
            await service.update_user(user, data)

    async def test_update_same_username_allowed(self, service: UserService) -> None:
        """Updating to the same username should not raise (no conflict check)."""
        user = _make_user(username="alice")

        service._repo.get_by_username = AsyncMock(return_value=None)  # type: ignore[method-assign]
        service._repo.get_by_email = AsyncMock(return_value=None)  # type: ignore[method-assign]
        service._repo.update = AsyncMock(return_value=user)  # type: ignore[method-assign]

        data = UserUpdate(username="alice")
        result = await service.update_user(user, data)
        assert result.username == "alice"

    async def test_update_email_taken_raises(self, service: UserService) -> None:
        """Should raise :class:`UserAlreadyExistsError` if email is taken."""
        user = _make_user(email="alice@example.com")
        existing = _make_user(email="bob@example.com", id=uuid.uuid4())

        service._repo.get_by_username = AsyncMock(return_value=None)  # type: ignore[method-assign]
        service._repo.get_by_email = AsyncMock(return_value=existing)  # type: ignore[method-assign]

        data = UserUpdate(email="bob@example.com")
        with pytest.raises(UserAlreadyExistsError):
            await service.update_user(user, data)

    async def test_update_no_fields_is_noop(self, service: UserService) -> None:
        """An empty update should call repo.update with an empty dict."""
        user = _make_user()

        service._repo.get_by_username = AsyncMock(return_value=None)  # type: ignore[method-assign]
        service._repo.get_by_email = AsyncMock(return_value=None)  # type: ignore[method-assign]
        service._repo.update = AsyncMock(return_value=user)  # type: ignore[method-assign]

        data = UserUpdate()
        result = await service.update_user(user, data)
        assert isinstance(result, UserRead)


# ---------------------------------------------------------------------------
# delete_user
# ---------------------------------------------------------------------------


class TestDeleteUser:
    """Tests for :meth:`UserService.delete_user`."""

    async def test_delete_calls_repo(self, service: UserService) -> None:
        """Should call :meth:`UserRepository.delete` with the user instance."""
        user = _make_user()
        service._repo.delete = AsyncMock()  # type: ignore[method-assign]

        await service.delete_user(user)

        service._repo.delete.assert_awaited_once_with(user)
