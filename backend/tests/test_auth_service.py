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

"""Unit tests for AuthService — no database access (all repository calls mocked).

Every test patches :class:`~app.repositories.user_repository.UserRepository`
methods on the instance created inside :class:`~app.services.auth_service.AuthService`,
so no real database connection is required.

Isolation strategy: ``AuthService.__init__`` creates a ``UserRepository``
from the injected session. We patch individual repository methods directly
on the instance via ``unittest.mock.AsyncMock`` assigned as attributes after
construction, giving us precise control over each scenario.

Note on bcrypt: ``passlib 1.7.4`` is incompatible with ``bcrypt 5+`` under
Python 3.14 (bcrypt removed the ``__about__`` attribute and tightened its
72-byte limit enforcement). All fixtures therefore store **pre-computed**
bcrypt hashes rather than calling ``hash_password()`` at fixture-build time,
and the ``hash_password`` / ``verify_password`` functions inside
``app.core.security`` are patched in tests that need to exercise that logic.
The pre-computed hashes below were generated with ``bcrypt.hashpw`` directly
(rounds=4 for test speed) and can be verified independently.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import InvalidCredentialsError, UserAlreadyExistsError
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin
from app.services.auth_service import AuthService

# ---------------------------------------------------------------------------
# Pre-computed bcrypt hashes (rounds=4) for test fixture passwords.
# Generated via:  bcrypt.hashpw(b"<password>", bcrypt.gensalt(rounds=4))
# ---------------------------------------------------------------------------
_HASH_P_AT_SSWORD_123 = "$2b$04$CjEA.qj8papCg/iPS.on8.25WkGEgECsrnDEJbk/kn.RlVzYeTlAy"
_HASH_CORRECT_PASSWORD = "$2b$04$6j8nrZc7ByC4ID90vPC.R.rS8XvZ3m.XxoVyYxBEy9X9YXdL9Y4qO"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(
    *,
    id: uuid.UUID | None = None,
    username: str = "testuser",
    email: str = "test@example.com",
    hashed_password: str = _HASH_P_AT_SSWORD_123,
    is_active: bool = True,
    refresh_token_version: int = 0,
) -> User:
    """Build a detached :class:`User` ORM instance for test use.

    Uses a pre-computed bcrypt hash to avoid calling ``hash_password()``
    (which triggers the broken passlib/bcrypt 5+ backend initialisation under
    Python 3.14).

    Args:
        id: UUID primary key. Defaults to a new random UUID.
        username: Display name. Defaults to ``"testuser"``.
        email: Email address. Defaults to ``"test@example.com"``.
        hashed_password: Pre-computed bcrypt hash to store directly. Defaults
            to the hash for ``"P@ssword123"``.
        is_active: Whether the user account is active. Defaults to ``True``.
        refresh_token_version: Token version counter. Defaults to ``0``.

    Returns:
        A :class:`User` instance with all required fields populated.
    """
    user = User()
    user.id = id if id is not None else uuid.uuid4()  # type: ignore[assignment]
    user.username = username  # type: ignore[assignment]
    user.email = email  # type: ignore[assignment]
    user.hashed_password = hashed_password  # type: ignore[assignment]
    user.provider = "local"  # type: ignore[assignment]
    user.provider_id = None  # type: ignore[assignment]
    user.is_active = is_active  # type: ignore[assignment]
    user.refresh_token_version = refresh_token_version  # type: ignore[assignment]
    user.created_at = datetime.now(UTC)  # type: ignore[assignment]
    user.updated_at = datetime.now(UTC)  # type: ignore[assignment]
    return user


def _make_register_payload(
    *,
    username: str = "newuser",
    email: str = "new@example.com",
    password: str = "P@ssword123",
) -> UserCreate:
    """Build a valid :class:`UserCreate` payload.

    Args:
        username: Desired username. Defaults to ``"newuser"``.
        email: Desired email. Defaults to ``"new@example.com"``.
        password: Plain-text password. Defaults to ``"P@ssword123"``.

    Returns:
        A validated :class:`UserCreate` instance.
    """
    return UserCreate(username=username, email=email, password=password)


def _make_login_payload(
    *,
    username: str = "testuser",
    password: str = "P@ssword123",
) -> UserLogin:
    """Build a valid :class:`UserLogin` payload.

    Args:
        username: Username or email. Defaults to ``"testuser"``.
        password: Plain-text password. Defaults to ``"P@ssword123"``.

    Returns:
        A validated :class:`UserLogin` instance.
    """
    return UserLogin(username=username, password=password)


@pytest.fixture()
def service(mock_session: AsyncMock) -> AuthService:
    """Return an :class:`AuthService` wired to a mock session.

    Args:
        mock_session: The mocked SQLAlchemy session.

    Returns:
        An :class:`AuthService` instance ready for testing.
    """
    return AuthService(mock_session)


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------


class TestRegister:
    """Unit tests for :meth:`AuthService.register`."""

    @pytest.mark.unit
    async def test_register_success(
        self, service: AuthService, mock_session: AsyncMock
    ) -> None:
        """register() must persist a user whose hashed_password differs from plain.

        The service must call ``hash_password`` internally and never store
        the raw password.  We verify this by patching ``hash_password`` to
        return a recognisable sentinel value and confirming the repo is
        called with that sentinel (not the plain-text password).
        """
        payload = _make_register_payload()
        expected_user = _make_user(username=payload.username, email=payload.email)
        sentinel_hash = "$2b$04$SENTINEL_HASH_FOR_TESTING_ONLY_____"

        with (
            patch.object(
                service._repo,
                "get_by_username",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service._repo,
                "get_by_email",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service._repo,
                "create",
                new=AsyncMock(return_value=expected_user),
            ) as mock_create,
            # Patch hash_password so it returns a predictable value without
            # triggering the broken passlib/bcrypt backend initialisation.
            patch(
                "app.services.auth_service.hash_password",
                return_value=sentinel_hash,
            ),
        ):
            result = await service.register(payload)

        # The returned object must be the user the repo returned.
        assert result is expected_user

        # The repo's create() must have received the sentinel hash, not plain text.
        _call_args = mock_create.call_args
        stored_hash: str = _call_args[0][1]  # second positional arg is hashed_password
        assert stored_hash == sentinel_hash
        assert stored_hash != payload.password

    @pytest.mark.unit
    async def test_register_duplicate_username_raises(
        self, service: AuthService
    ) -> None:
        """register() must raise UserAlreadyExistsError when the username exists.

        When ``get_by_username`` returns an existing user, the service must
        not proceed to the email check or the create call.
        """
        existing = _make_user()

        with (
            patch.object(
                service._repo,
                "get_by_username",
                new=AsyncMock(return_value=existing),
            ),
            patch.object(
                service._repo,
                "get_by_email",
                new=AsyncMock(return_value=None),
            ),
            pytest.raises(UserAlreadyExistsError),
        ):
            await service.register(_make_register_payload())

    @pytest.mark.unit
    async def test_register_duplicate_email_raises(self, service: AuthService) -> None:
        """register() must raise UserAlreadyExistsError when the email exists.

        Even if the username is free, a taken email address must block
        registration.
        """
        existing = _make_user()

        with (
            patch.object(
                service._repo,
                "get_by_username",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service._repo,
                "get_by_email",
                new=AsyncMock(return_value=existing),
            ),
            pytest.raises(UserAlreadyExistsError),
        ):
            await service.register(_make_register_payload())

    @pytest.mark.unit
    async def test_register_seeding_failure_is_non_blocking_and_logged(
        self, service: AuthService
    ) -> None:
        payload = _make_register_payload()
        expected_user = _make_user(username=payload.username, email=payload.email)

        with (
            patch.object(
                service._repo,
                "get_by_username",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service._repo,
                "get_by_email",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service._repo,
                "create",
                new=AsyncMock(return_value=expected_user),
            ),
            patch.object(
                service._market_index_repo,
                "seed_defaults",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service._taxonomy_repo,
                "seed_defaults",
                new=AsyncMock(side_effect=RuntimeError("boom")),
            ),
            patch.object(
                service._annotation_repo,
                "seed_defaults",
                new=AsyncMock(return_value=None),
            ),
            patch("app.services.auth_service.hash_password", return_value="hashed"),
            patch("app.services.auth_service.logger.error") as mock_logger_error,
            patch.object(service._audit, "create_audit_event") as mock_audit_event,
        ):
            result = await service.register(payload)

        assert result is expected_user
        mock_logger_error.assert_called_once()
        mock_audit_event.assert_called_once()
        assert mock_audit_event.call_args.kwargs["action"] == "metadata.seeding.failed"
        assert mock_audit_event.call_args.kwargs["metadata"] == {
            "user_id": str(expected_user.id)
        }


# ---------------------------------------------------------------------------
# Login tests
# ---------------------------------------------------------------------------


class TestLogin:
    """Unit tests for :meth:`AuthService.login`."""

    @pytest.mark.unit
    async def test_login_success(self, service: AuthService) -> None:
        """login() must return a tuple of (access_token, refresh_token) strings.

        Both tokens must be non-empty strings for a valid user with the
        correct password.  ``verify_password`` is patched to return ``True``
        so the test is not sensitive to the bcrypt backend.
        """
        # user.hashed_password doesn't matter because verify_password is mocked
        user = _make_user()

        with (
            patch.object(
                service._repo,
                "get_by_username",
                new=AsyncMock(return_value=user),
            ),
            # Patch verify_password to bypass broken passlib/bcrypt backend
            patch("app.services.auth_service.verify_password", return_value=True),
        ):
            access_token, refresh_token = await service.login(
                _make_login_payload(password="P@ssword123")
            )

        assert isinstance(access_token, str) and len(access_token) > 0
        assert isinstance(refresh_token, str) and len(refresh_token) > 0

    @pytest.mark.unit
    async def test_login_wrong_password_raises(self, service: AuthService) -> None:
        """login() must raise InvalidCredentialsError for a wrong password.

        The error must be raised even when the username resolves correctly,
        ensuring the password check is always enforced.  ``verify_password``
        is patched to return ``False`` to simulate a bad password.
        """
        user = _make_user()

        with (
            patch.object(
                service._repo,
                "get_by_username",
                new=AsyncMock(return_value=user),
            ),
            # Simulate password mismatch without touching bcrypt
            patch("app.services.auth_service.verify_password", return_value=False),
            pytest.raises(InvalidCredentialsError),
        ):
            await service.login(_make_login_payload(password="wrong-password-456"))

    @pytest.mark.unit
    async def test_login_inactive_user_raises(self, service: AuthService) -> None:
        """login() must raise InvalidCredentialsError for an inactive user.

        A correct password must still be rejected if the user account has
        been deactivated (``is_active=False``).  ``verify_password`` is
        patched to return ``True`` so the inactive check is the only blocker.
        """
        inactive_user = _make_user(is_active=False)

        with (
            patch.object(
                service._repo,
                "get_by_username",
                new=AsyncMock(return_value=inactive_user),
            ),
            patch("app.services.auth_service.verify_password", return_value=True),
            pytest.raises(InvalidCredentialsError),
        ):
            await service.login(_make_login_payload(password="P@ssword123"))

    @pytest.mark.unit
    async def test_login_unknown_user_raises(self, service: AuthService) -> None:
        """login() must raise InvalidCredentialsError when no user is found.

        When both the username and email lookups return ``None``, the
        service must raise :class:`~app.core.exceptions.InvalidCredentialsError`
        rather than leaking information about which lookup failed.
        """
        with (
            patch.object(
                service._repo,
                "get_by_username",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service._repo,
                "get_by_email",
                new=AsyncMock(return_value=None),
            ),
            pytest.raises(InvalidCredentialsError),
        ):
            await service.login(_make_login_payload())

    @pytest.mark.unit
    async def test_login_falls_back_to_email_lookup(self, service: AuthService) -> None:
        """login() must accept either username or email as the identifier.

        When the username lookup returns ``None``, the service tries the
        same string as an email address.  This test verifies the fallback
        path is exercised.
        """
        user = _make_user(email="alice@example.com")

        with (
            patch.object(
                service._repo,
                "get_by_username",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service._repo,
                "get_by_email",
                new=AsyncMock(return_value=user),
            ),
            # Bypass bcrypt backend by patching verify_password
            patch("app.services.auth_service.verify_password", return_value=True),
        ):
            access_token, refresh_token = await service.login(
                _make_login_payload(
                    username="alice@example.com", password="P@ssword123"
                )
            )

        assert isinstance(access_token, str) and len(access_token) > 0
        assert isinstance(refresh_token, str) and len(refresh_token) > 0


# ---------------------------------------------------------------------------
# Token refresh tests
# ---------------------------------------------------------------------------


class TestRefresh:
    """Unit tests for :meth:`AuthService.refresh`."""

    @pytest.mark.unit
    async def test_refresh_valid_token_returns_new_access_token(
        self, service: AuthService
    ) -> None:
        """refresh() returns a (access_token, refresh_token) tuple for a valid token.

        When the refresh token is valid and the user still exists and is
        active, :meth:`AuthService.refresh` must return a two-tuple of
        non-empty strings.
        """
        from app.core.security import create_refresh_token

        user = _make_user(refresh_token_version=0)
        refresh_token = create_refresh_token(user.id, token_version=0)  # type: ignore[arg-type]

        with (
            patch.object(
                service._repo,
                "get_by_id",
                new=AsyncMock(return_value=user),
            ),
            patch.object(
                service._repo,
                "increment_token_version",
                new=AsyncMock(),
            ),
        ):
            new_access_token, new_refresh_token = await service.refresh(refresh_token)

        assert isinstance(new_access_token, str) and len(new_access_token) > 0
        assert isinstance(new_refresh_token, str) and len(new_refresh_token) > 0

    @pytest.mark.unit
    async def test_refresh_invalid_token_raises(self, service: AuthService) -> None:
        """refresh() must raise InvalidCredentialsError for a completely invalid token.

        A garbage string (not a valid JWT) should cause the underlying
        ``decode_refresh_token`` call to raise ``InvalidTokenError``, which
        the service catches and re-raises as ``InvalidCredentialsError``.
        """
        with pytest.raises(InvalidCredentialsError):
            await service.refresh("not.a.valid.jwt.token")

    @pytest.mark.unit
    async def test_refresh_valid_token_inactive_user_raises(
        self, service: AuthService
    ) -> None:
        """refresh() must raise InvalidCredentialsError when the user is inactive.

        A valid refresh token for a user that has been deactivated since
        the token was issued must still be rejected.
        """
        from app.core.security import create_refresh_token

        inactive_user = _make_user(is_active=False, refresh_token_version=0)
        refresh_token = create_refresh_token(inactive_user.id, token_version=0)  # type: ignore[arg-type]

        with (
            patch.object(
                service._repo,
                "get_by_id",
                new=AsyncMock(return_value=inactive_user),
            ),
            pytest.raises(InvalidCredentialsError),
        ):
            await service.refresh(refresh_token)

    @pytest.mark.unit
    async def test_refresh_valid_token_deleted_user_raises(
        self, service: AuthService
    ) -> None:
        """refresh() must raise InvalidCredentialsError when the user no longer exists.

        A valid refresh token for a user that has been deleted from the
        database since the token was issued must be rejected.
        """
        from app.core.security import create_refresh_token

        ghost_user_id = uuid.uuid4()
        refresh_token = create_refresh_token(ghost_user_id, token_version=0)

        with (
            patch.object(
                service._repo,
                "get_by_id",
                new=AsyncMock(return_value=None),
            ),
            pytest.raises(InvalidCredentialsError),
        ):
            await service.refresh(refresh_token)

    @pytest.mark.unit
    async def test_refresh_revoked_token_raises(self, service: AuthService) -> None:
        """refresh() must raise InvalidCredentialsError when token version mismatches.

        If the user's ``refresh_token_version`` has been incremented (e.g. after
        a logout), any previously issued refresh token must be rejected.
        """
        from app.core.security import create_refresh_token

        # Token was issued with version 0, but user is now at version 1
        user = _make_user(refresh_token_version=1)
        refresh_token = create_refresh_token(user.id, token_version=0)  # type: ignore[arg-type]

        with (
            patch.object(
                service._repo,
                "get_by_id",
                new=AsyncMock(return_value=user),
            ),
            pytest.raises(InvalidCredentialsError),
        ):
            await service.refresh(refresh_token)
