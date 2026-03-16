"""Unit tests for AuthService.google_oauth_login — no database access.

All :class:`~app.repositories.user_repository.UserRepository` method calls
are replaced with :class:`~unittest.mock.AsyncMock` instances injected
directly onto the ``service._repo`` attribute after construction, following
the same isolation pattern established in ``test_auth_service.py``.

Three scenarios are covered:
1. **Existing Google user** — ``get_by_provider_id`` returns a user;
   no linking or creation occurs.
2. **Email-link** — ``get_by_provider_id`` returns ``None`` but
   ``get_by_email`` returns a local user; ``link_oauth_account`` is called.
3. **New user creation** — both lookups return ``None``; the service
   derives a username and calls ``create_oauth_user``.

Additional edge cases: unverified email, inactive user, username collision
during derivation, and the shape of the returned three-tuple.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, call, patch

import pytest

from app.core.exceptions import InvalidCredentialsError
from app.models.user import User
from app.services.auth_service import AuthService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_google_user(
    *,
    id: uuid.UUID | None = None,
    username: str = "googleuser",
    email: str = "google@example.com",
    provider: str = "google",
    provider_id: str = "google-sub-123",
    hashed_password: str | None = None,
    is_active: bool = True,
    refresh_token_version: int = 0,
) -> User:
    """Build a detached :class:`User` ORM instance representing a Google account.

    Args:
        id: UUID primary key. Defaults to a new random UUID.
        username: Display name. Defaults to ``"googleuser"``.
        email: Email address. Defaults to ``"google@example.com"``.
        provider: Auth provider string. Defaults to ``"google"``.
        provider_id: Google ``sub`` claim. Defaults to ``"google-sub-123"``.
        hashed_password: Stored hash — ``None`` for OAuth-only accounts.
        is_active: Whether the account is active. Defaults to ``True``.
        refresh_token_version: Token version counter. Defaults to ``0``.

    Returns:
        A :class:`User` instance with all required fields populated.
    """
    user = User()
    user.id = id if id is not None else uuid.uuid4()  # type: ignore[assignment]
    user.username = username  # type: ignore[assignment]
    user.email = email  # type: ignore[assignment]
    user.hashed_password = hashed_password  # type: ignore[assignment]
    user.provider = provider  # type: ignore[assignment]
    user.provider_id = provider_id  # type: ignore[assignment]
    user.is_active = is_active  # type: ignore[assignment]
    user.refresh_token_version = refresh_token_version  # type: ignore[assignment]
    user.created_at = datetime.now(UTC)  # type: ignore[assignment]
    user.updated_at = datetime.now(UTC)  # type: ignore[assignment]
    return user


def _make_local_user(
    *,
    id: uuid.UUID | None = None,
    username: str = "localuser",
    email: str = "local@example.com",
    hashed_password: str = "$2b$04$SOMEHASHVALUE",
    is_active: bool = True,
    refresh_token_version: int = 0,
) -> User:
    """Build a detached :class:`User` ORM instance representing a local account.

    Args:
        id: UUID primary key. Defaults to a new random UUID.
        username: Display name. Defaults to ``"localuser"``.
        email: Email address. Defaults to ``"local@example.com"``.
        hashed_password: Pre-computed bcrypt hash. Defaults to a sentinel.
        is_active: Whether the account is active. Defaults to ``True``.
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


@pytest.fixture()
def mock_session() -> AsyncMock:
    """Return a mock :class:`AsyncSession`.

    Returns:
        A fresh :class:`AsyncMock` standing in for the SQLAlchemy session.
    """
    return AsyncMock()


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
# Scenario 1 — Existing Google user (lookup by provider_id succeeds)
# ---------------------------------------------------------------------------


class TestGoogleOAuthLoginExistingGoogleUser:
    """Tests for the returning-Google-user scenario.

    When ``get_by_provider_id`` returns an active user, the service should
    skip all linking/creation logic and go straight to token issuance.
    """

    @pytest.mark.unit
    async def test_returns_three_token_strings(self, service: AuthService) -> None:
        """google_oauth_login() returns a (access, refresh, ott) three-tuple.

        All three elements must be non-empty strings that can be used as
        JWT tokens or embedded in redirect URLs.
        """
        existing_google_user = _make_google_user()

        with patch.object(
            service._repo,
            "get_by_provider_id",
            new=AsyncMock(return_value=existing_google_user),
        ):
            (
                access_token,
                refresh_token,
                one_time_token,
            ) = await service.google_oauth_login(
                google_sub="google-sub-123",
                email="google@example.com",
                display_name="Google User",
                email_verified=True,
            )

        assert isinstance(access_token, str) and len(access_token) > 0
        assert isinstance(refresh_token, str) and len(refresh_token) > 0
        assert isinstance(one_time_token, str) and len(one_time_token) > 0

    @pytest.mark.unit
    async def test_does_not_call_get_by_email_when_provider_id_found(
        self, service: AuthService
    ) -> None:
        """When provider_id lookup succeeds, email lookup must not be called.

        Calling ``get_by_email`` unnecessarily would risk triggering the
        auto-link path on a user that already has a Google account.
        """
        existing_google_user = _make_google_user()
        mock_get_by_provider_id = AsyncMock(return_value=existing_google_user)
        mock_get_by_email = AsyncMock()

        with (
            patch.object(
                service._repo,
                "get_by_provider_id",
                new=mock_get_by_provider_id,
            ),
            patch.object(service._repo, "get_by_email", new=mock_get_by_email),
        ):
            await service.google_oauth_login(
                google_sub="google-sub-123",
                email="google@example.com",
                display_name="Google User",
                email_verified=True,
            )

        mock_get_by_email.assert_not_called()

    @pytest.mark.unit
    async def test_does_not_call_create_or_link_when_provider_id_found(
        self, service: AuthService
    ) -> None:
        """No creation or linking must happen when provider_id lookup returns a user.

        This verifies the early-return after step 1 of the lookup chain.
        """
        existing_google_user = _make_google_user()
        mock_link = AsyncMock()
        mock_create = AsyncMock()

        with (
            patch.object(
                service._repo,
                "get_by_provider_id",
                new=AsyncMock(return_value=existing_google_user),
            ),
            patch.object(service._repo, "link_oauth_account", new=mock_link),
            patch.object(service._repo, "create_oauth_user", new=mock_create),
        ):
            await service.google_oauth_login(
                google_sub="google-sub-123",
                email="google@example.com",
                display_name="Google User",
                email_verified=True,
            )

        mock_link.assert_not_called()
        mock_create.assert_not_called()

    @pytest.mark.unit
    async def test_provider_id_lookup_called_with_correct_args(
        self, service: AuthService
    ) -> None:
        """get_by_provider_id must be called with provider='google' and the sub claim.

        Verifies the lookup key composition so a change to hard-coded
        provider strings is caught immediately.
        """
        existing_google_user = _make_google_user()
        mock_get_by_provider_id = AsyncMock(return_value=existing_google_user)

        with patch.object(
            service._repo,
            "get_by_provider_id",
            new=mock_get_by_provider_id,
        ):
            await service.google_oauth_login(
                google_sub="abc-sub-987",
                email="google@example.com",
                display_name="Google User",
                email_verified=True,
            )

        mock_get_by_provider_id.assert_called_once_with("google", "abc-sub-987")

    @pytest.mark.unit
    async def test_inactive_google_user_raises_invalid_credentials_error(
        self, service: AuthService
    ) -> None:
        """An existing but inactive Google account must raise InvalidCredentialsError.

        Account suspension must block OAuth logins just as it blocks
        password logins.
        """
        inactive_user = _make_google_user(is_active=False)

        with (
            patch.object(
                service._repo,
                "get_by_provider_id",
                new=AsyncMock(return_value=inactive_user),
            ),
            pytest.raises(InvalidCredentialsError),
        ):
            await service.google_oauth_login(
                google_sub="google-sub-123",
                email="google@example.com",
                display_name="Google User",
                email_verified=True,
            )


# ---------------------------------------------------------------------------
# Scenario 2 — Email-link (provider_id miss, email hit)
# ---------------------------------------------------------------------------


class TestGoogleOAuthLoginEmailLink:
    """Tests for the account-linking scenario.

    When ``get_by_provider_id`` returns ``None`` but ``get_by_email`` finds
    an existing local user, the service should call ``link_oauth_account``
    and then issue tokens for the now-linked user.
    """

    @pytest.mark.unit
    async def test_links_existing_local_user_and_returns_tokens(
        self, service: AuthService
    ) -> None:
        """When a local account shares the Google email it must be linked.

        The service should call ``link_oauth_account`` with the correct
        provider / provider_id, and the returned three-tuple should all be
        non-empty strings.
        """
        local_user = _make_local_user(email="shared@example.com")
        # After linking the user will look like a Google account
        linked_user = _make_google_user(
            id=local_user.id,
            email="shared@example.com",
            provider="google",
            provider_id="new-google-sub-456",
        )

        mock_link = AsyncMock(return_value=linked_user)

        with (
            patch.object(
                service._repo,
                "get_by_provider_id",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service._repo,
                "get_by_email",
                new=AsyncMock(return_value=local_user),
            ),
            patch.object(service._repo, "link_oauth_account", new=mock_link),
        ):
            (
                access_token,
                refresh_token,
                one_time_token,
            ) = await service.google_oauth_login(
                google_sub="new-google-sub-456",
                email="shared@example.com",
                display_name="Shared User",
                email_verified=True,
            )

        assert isinstance(access_token, str) and len(access_token) > 0
        assert isinstance(refresh_token, str) and len(refresh_token) > 0
        assert isinstance(one_time_token, str) and len(one_time_token) > 0

    @pytest.mark.unit
    async def test_link_oauth_account_called_with_correct_args(
        self, service: AuthService
    ) -> None:
        """link_oauth_account must receive the existing user object, 'google', and sub.

        Validates that the linking call is wired up with the right parameters
        so a future rename of the provider string is caught.
        """
        local_user = _make_local_user(email="link@example.com")
        linked_user = _make_google_user(
            id=local_user.id,
            email="link@example.com",
            provider_id="sub-link-test",
        )
        mock_link = AsyncMock(return_value=linked_user)

        with (
            patch.object(
                service._repo,
                "get_by_provider_id",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service._repo,
                "get_by_email",
                new=AsyncMock(return_value=local_user),
            ),
            patch.object(service._repo, "link_oauth_account", new=mock_link),
        ):
            await service.google_oauth_login(
                google_sub="sub-link-test",
                email="link@example.com",
                display_name="Link Test",
                email_verified=True,
            )

        mock_link.assert_called_once_with(local_user, "google", "sub-link-test")

    @pytest.mark.unit
    async def test_create_oauth_user_not_called_in_email_link_scenario(
        self, service: AuthService
    ) -> None:
        """create_oauth_user must not be called when an email match is found.

        Creating a new record when one already exists would produce a
        duplicate-email violation.
        """
        local_user = _make_local_user()
        linked_user = _make_google_user(id=local_user.id)
        mock_create = AsyncMock()

        with (
            patch.object(
                service._repo,
                "get_by_provider_id",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service._repo,
                "get_by_email",
                new=AsyncMock(return_value=local_user),
            ),
            patch.object(
                service._repo,
                "link_oauth_account",
                new=AsyncMock(return_value=linked_user),
            ),
            patch.object(service._repo, "create_oauth_user", new=mock_create),
        ):
            await service.google_oauth_login(
                google_sub="sub-abc",
                email="local@example.com",
                display_name="Local User",
                email_verified=True,
            )

        mock_create.assert_not_called()

    @pytest.mark.unit
    async def test_inactive_local_user_after_link_raises_invalid_credentials_error(
        self, service: AuthService
    ) -> None:
        """A linked user who is inactive must still raise InvalidCredentialsError.

        The is_active check happens *after* linking, so a suspended local
        account cannot bypass the check by logging in via Google.
        """
        local_user = _make_local_user()
        # link_oauth_account returns the updated user — mark it inactive
        linked_inactive = _make_google_user(
            id=local_user.id,
            is_active=False,
        )

        with (
            patch.object(
                service._repo,
                "get_by_provider_id",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service._repo,
                "get_by_email",
                new=AsyncMock(return_value=local_user),
            ),
            patch.object(
                service._repo,
                "link_oauth_account",
                new=AsyncMock(return_value=linked_inactive),
            ),
            pytest.raises(InvalidCredentialsError),
        ):
            await service.google_oauth_login(
                google_sub="sub-inactive",
                email="local@example.com",
                display_name="Inactive User",
                email_verified=True,
            )


# ---------------------------------------------------------------------------
# Scenario 3 — New user creation (both lookups return None)
# ---------------------------------------------------------------------------


class TestGoogleOAuthLoginNewUser:
    """Tests for the new-user-creation scenario.

    When both ``get_by_provider_id`` and ``get_by_email`` return ``None``,
    the service must derive a unique username and call ``create_oauth_user``.
    """

    @pytest.mark.unit
    async def test_creates_new_oauth_user_and_returns_tokens(
        self, service: AuthService
    ) -> None:
        """When no existing user matches, a new OAuth user must be created.

        The three returned values must all be non-empty JWT strings, and
        ``create_oauth_user`` must be called exactly once.
        """
        new_user = _make_google_user(username="johndoe")
        mock_create = AsyncMock(return_value=new_user)

        with (
            patch.object(
                service._repo,
                "get_by_provider_id",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service._repo,
                "get_by_email",
                new=AsyncMock(return_value=None),
            ),
            # username derivation: base "johndoe" is available on first check
            patch.object(
                service._repo,
                "get_by_username",
                new=AsyncMock(return_value=None),
            ),
            patch.object(service._repo, "create_oauth_user", new=mock_create),
        ):
            (
                access_token,
                refresh_token,
                one_time_token,
            ) = await service.google_oauth_login(
                google_sub="new-sub-789",
                email="newuser@example.com",
                display_name="John Doe",
                email_verified=True,
            )

        assert isinstance(access_token, str) and len(access_token) > 0
        assert isinstance(refresh_token, str) and len(refresh_token) > 0
        assert isinstance(one_time_token, str) and len(one_time_token) > 0
        mock_create.assert_called_once()

    @pytest.mark.unit
    async def test_create_oauth_user_called_with_correct_args(
        self, service: AuthService
    ) -> None:
        """create_oauth_user must receive the email, derived username, 'google', sub.

        Verifies the argument mapping so changes to the call signature are
        caught at test time rather than at runtime.
        """
        new_user = _make_google_user(username="johndoe", email="jd@example.com")
        mock_create = AsyncMock(return_value=new_user)

        with (
            patch.object(
                service._repo,
                "get_by_provider_id",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service._repo,
                "get_by_email",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service._repo,
                "get_by_username",
                new=AsyncMock(return_value=None),  # base name "johndoe" is free
            ),
            patch.object(service._repo, "create_oauth_user", new=mock_create),
        ):
            await service.google_oauth_login(
                google_sub="sub-jd-001",
                email="jd@example.com",
                display_name="John Doe",
                email_verified=True,
            )

        mock_create.assert_called_once_with(
            email="jd@example.com",
            username="johndoe",  # derived: strip non-alphanumeric, lowercase
            provider="google",
            provider_id="sub-jd-001",
        )

    @pytest.mark.unit
    async def test_link_oauth_account_not_called_in_new_user_scenario(
        self, service: AuthService
    ) -> None:
        """link_oauth_account must not be called when both lookups return None.

        There is nothing to link when neither a provider_id nor an email
        match exists.
        """
        new_user = _make_google_user()
        mock_link = AsyncMock()

        with (
            patch.object(
                service._repo,
                "get_by_provider_id",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service._repo,
                "get_by_email",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service._repo,
                "get_by_username",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service._repo,
                "create_oauth_user",
                new=AsyncMock(return_value=new_user),
            ),
            patch.object(service._repo, "link_oauth_account", new=mock_link),
        ):
            await service.google_oauth_login(
                google_sub="sub-xyz",
                email="brand@new.com",
                display_name="Brand New",
                email_verified=True,
            )

        mock_link.assert_not_called()

    @pytest.mark.unit
    async def test_username_derived_from_display_name(
        self, service: AuthService
    ) -> None:
        """The derived username must be lowercase-alphanum from the display name.

        ``_derive_unique_username`` strips non-alphanumeric characters and
        lowercases the result.  Spaces become empty strings; the display
        name ``"Jane O'Sullivan"`` should become ``"janeosullivan"``.
        """
        new_user = _make_google_user(username="janeosullivan")
        mock_create = AsyncMock(return_value=new_user)

        with (
            patch.object(
                service._repo,
                "get_by_provider_id",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service._repo,
                "get_by_email",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service._repo,
                "get_by_username",
                new=AsyncMock(return_value=None),
            ),
            patch.object(service._repo, "create_oauth_user", new=mock_create),
        ):
            await service.google_oauth_login(
                google_sub="sub-jane",
                email="jane@example.com",
                display_name="Jane O'Sullivan",
                email_verified=True,
            )

        _kwargs = mock_create.call_args.kwargs
        assert _kwargs["username"] == "janeosullivan"

    @pytest.mark.unit
    async def test_username_collision_appends_numeric_suffix(
        self, service: AuthService
    ) -> None:
        """When the base username is taken, a numeric suffix must be appended.

        ``get_by_username`` is called in a loop: first for the base name
        (returns an existing user), then for ``base2`` (returns ``None``).
        The created user should receive ``"johndoe2"`` as their username.
        """
        base_taken_user = _make_google_user(username="johndoe")
        new_user = _make_google_user(username="johndoe2")
        mock_create = AsyncMock(return_value=new_user)

        # First call returns an existing user (base name taken);
        # second call returns None (suffix-2 name is free).
        mock_get_by_username = AsyncMock(side_effect=[base_taken_user, None])

        with (
            patch.object(
                service._repo,
                "get_by_provider_id",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service._repo,
                "get_by_email",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service._repo,
                "get_by_username",
                new=mock_get_by_username,
            ),
            patch.object(service._repo, "create_oauth_user", new=mock_create),
        ):
            await service.google_oauth_login(
                google_sub="sub-collision",
                email="collision@example.com",
                display_name="John Doe",
                email_verified=True,
            )

        _kwargs = mock_create.call_args.kwargs
        assert _kwargs["username"] == "johndoe2"

    @pytest.mark.unit
    async def test_display_name_with_only_special_chars_falls_back_to_user(
        self, service: AuthService
    ) -> None:
        """A display name that strips to empty must fall back to ``'user'``.

        Handles edge cases where a user's Google display name contains
        only non-alphanumeric characters (e.g. ``"@!#"``).
        """
        new_user = _make_google_user(username="user")
        mock_create = AsyncMock(return_value=new_user)

        with (
            patch.object(
                service._repo,
                "get_by_provider_id",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service._repo,
                "get_by_email",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service._repo,
                "get_by_username",
                new=AsyncMock(return_value=None),
            ),
            patch.object(service._repo, "create_oauth_user", new=mock_create),
        ):
            await service.google_oauth_login(
                google_sub="sub-special",
                email="special@example.com",
                display_name="@!#$",
                email_verified=True,
            )

        _kwargs = mock_create.call_args.kwargs
        assert _kwargs["username"] == "user"


# ---------------------------------------------------------------------------
# Cross-cutting: unverified email guard
# ---------------------------------------------------------------------------


class TestGoogleOAuthLoginUnverifiedEmail:
    """Tests for the email-verification guard.

    ``google_oauth_login`` must refuse to proceed if Google has not
    verified the user's email address, regardless of the lookup results.
    """

    @pytest.mark.unit
    async def test_unverified_email_raises_invalid_credentials_error(
        self, service: AuthService
    ) -> None:
        """email_verified=False must cause an immediate InvalidCredentialsError.

        The service must bail out before performing any repository calls
        when the Google email is not verified, to prevent provisioning
        accounts on unverified identities.
        """
        mock_lookup = AsyncMock()

        with (
            patch.object(service._repo, "get_by_provider_id", new=mock_lookup),
            pytest.raises(InvalidCredentialsError, match="not verified"),
        ):
            await service.google_oauth_login(
                google_sub="sub-unverified",
                email="unverified@example.com",
                display_name="Unverified User",
                email_verified=False,
            )

        mock_lookup.assert_not_called()

    @pytest.mark.unit
    async def test_unverified_email_does_not_call_any_repo_method(
        self, service: AuthService
    ) -> None:
        """No repository method must be called when email_verified is False.

        Even a fast-path lookup is skipped — an unverified email must be
        rejected at the boundary, before any database work.
        """
        mock_get_by_provider_id = AsyncMock()
        mock_get_by_email = AsyncMock()
        mock_create = AsyncMock()
        mock_link = AsyncMock()

        with (
            patch.object(
                service._repo, "get_by_provider_id", new=mock_get_by_provider_id
            ),
            patch.object(service._repo, "get_by_email", new=mock_get_by_email),
            patch.object(service._repo, "create_oauth_user", new=mock_create),
            patch.object(service._repo, "link_oauth_account", new=mock_link),
            pytest.raises(InvalidCredentialsError),
        ):
            await service.google_oauth_login(
                google_sub="sub-x",
                email="x@example.com",
                display_name="X",
                email_verified=False,
            )

        mock_get_by_provider_id.assert_not_called()
        mock_get_by_email.assert_not_called()
        mock_create.assert_not_called()
        mock_link.assert_not_called()


# ---------------------------------------------------------------------------
# Password login guard: Google-only accounts cannot use /auth/token
# ---------------------------------------------------------------------------


class TestLoginBlockedForGoogleOnlyAccount:
    """Tests for the OAuth-only account login guard in :meth:`AuthService.login`.

    Users provisioned via Google OAuth have ``provider='google'`` and
    ``hashed_password=None``.  Attempting a password login for such
    accounts must raise :class:`InvalidCredentialsError` rather than
    proceeding to the (absent) bcrypt check.
    """

    @pytest.mark.unit
    async def test_login_google_only_user_raises_invalid_credentials_error(
        self, service: AuthService
    ) -> None:
        """login() must raise InvalidCredentialsError for a Google-only account.

        The service checks ``user.provider != 'local'`` before attempting
        password verification.  A Google-only user must never be allowed
        to log in with a password.
        """
        from app.schemas.user import UserLogin

        google_user = _make_google_user(hashed_password=None)

        with (
            patch.object(
                service._repo,
                "get_by_username",
                new=AsyncMock(return_value=google_user),
            ),
            pytest.raises(InvalidCredentialsError),
        ):
            await service.login(
                UserLogin(username="googleuser", password="any-password")
            )

    @pytest.mark.unit
    async def test_login_google_only_user_does_not_call_verify_password(
        self, service: AuthService
    ) -> None:
        """verify_password must never be called for a Google-only account.

        The service must short-circuit before reaching the bcrypt check
        because calling it with ``hashed=None`` would raise a ``TypeError``.
        """
        from app.schemas.user import UserLogin

        google_user = _make_google_user(hashed_password=None)
        mock_verify = AsyncMock()

        with (
            patch.object(
                service._repo,
                "get_by_username",
                new=AsyncMock(return_value=google_user),
            ),
            patch("app.services.auth_service.verify_password", new=mock_verify),
            pytest.raises(InvalidCredentialsError),
        ):
            await service.login(
                UserLogin(username="googleuser", password="any-password")
            )

        mock_verify.assert_not_called()

    @pytest.mark.unit
    async def test_login_google_only_user_with_non_null_hash_also_raises(
        self, service: AuthService
    ) -> None:
        """A Google user with a non-null hashed_password is still blocked.

        The guard is ``provider != 'local'``, not ``hashed_password is None``.
        An edge-case user whose provider is ``'google'`` but who somehow has
        a stored hash must still be rejected at the provider check.
        """
        from app.schemas.user import UserLogin

        # Simulate a Google user that also has a legacy password hash stored
        google_user_with_hash = _make_google_user(
            hashed_password="$2b$04$SOMEHASH", provider="google"
        )

        with (
            patch.object(
                service._repo,
                "get_by_username",
                new=AsyncMock(return_value=google_user_with_hash),
            ),
            pytest.raises(InvalidCredentialsError),
        ):
            await service.login(
                UserLogin(username="googleuser", password="any-password")
            )
