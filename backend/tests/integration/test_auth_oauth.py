"""Integration tests for Google OAuth API endpoints.

Tests the following routes against a live database via the ``client``
fixture from ``conftest.py``:

- ``GET /api/v1/auth/google`` — service availability check
- ``POST /api/v1/auth/google/exchange`` — one-time token exchange
- ``POST /api/v1/auth/token`` — password login rejection for Google-only accounts

The Google OAuth callback (``GET /api/v1/auth/google/callback``) requires
a real Google authorization flow and is therefore **not** testable in a
standard integration suite.  The exchange endpoint is tested by minting
real OTTs via :func:`~app.core.security.create_one_time_token` and seeding
the required user directly into the test database.

All tests are isolated — the ``db_session`` fixture from ``conftest.py``
rolls back after each test so no data persists between runs.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import AsyncClient

from app.core.security import create_one_time_token

# ---------------------------------------------------------------------------
# URL constants
# ---------------------------------------------------------------------------

_GOOGLE_LOGIN_URL = "/api/v1/auth/google"
_GOOGLE_EXCHANGE_URL = "/api/v1/auth/google/exchange"
_TOKEN_URL = "/api/v1/auth/token"
_REGISTER_URL = "/api/v1/auth/register"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_user(
    client: AsyncClient,
    *,
    username: str,
    email: str,
    password: str,
) -> dict[str, Any]:
    """Register a local user and return the response body ``data`` dict.

    Args:
        client: The test HTTP client.
        username: Username to register.
        email: Email address to register.
        password: Plain-text password.

    Returns:
        The ``data`` key from the 201 registration response.
    """
    resp = await client.post(
        _REGISTER_URL,
        json={"username": username, "email": email, "password": password},
    )
    assert resp.status_code == 201, resp.text
    return dict(resp.json()["data"])


# ---------------------------------------------------------------------------
# GET /api/v1/auth/google
# ---------------------------------------------------------------------------


class TestGoogleLoginEndpoint:
    """Integration tests for ``GET /api/v1/auth/google``."""

    @pytest.mark.integration
    async def test_google_login_returns_503_when_client_id_not_configured(
        self, client: AsyncClient
    ) -> None:
        """GET /auth/google must return 503 when GOOGLE_CLIENT_ID is empty.

        The test environment does not have Google OAuth credentials, so the
        endpoint should refuse to redirect and return a 503 with a
        descriptive error message.
        """
        from unittest.mock import patch

        # Ensure GOOGLE_CLIENT_ID is None/empty in settings for this test
        from app.core.config import settings

        with patch.object(settings, "google_client_id", None):
            resp = await client.get(_GOOGLE_LOGIN_URL)

        assert resp.status_code == 503
        body = resp.json()
        assert "Google OAuth is not configured" in body.get("detail", "")

    @pytest.mark.integration
    async def test_google_login_returns_503_when_client_secret_not_configured(
        self, client: AsyncClient
    ) -> None:
        """GET /auth/google must return 503 when GOOGLE_CLIENT_SECRET is empty.

        Even if a client ID is present, a missing secret must prevent the
        redirect, as starting an OAuth flow without a secret is useless.
        """
        from unittest.mock import patch

        from app.core.config import settings

        with (
            patch.object(settings, "google_client_id", "some-client-id"),
            patch.object(settings, "google_client_secret", None),
        ):
            resp = await client.get(_GOOGLE_LOGIN_URL)

        assert resp.status_code == 503

    @pytest.mark.integration
    async def test_google_login_503_detail_is_informative(
        self, client: AsyncClient
    ) -> None:
        """The 503 error detail must name Google OAuth so it is debuggable.

        Operators need to know *which* integration is not configured when
        they hit this error in logs.
        """
        from unittest.mock import patch

        from app.core.config import settings

        with patch.object(settings, "google_client_id", None):
            resp = await client.get(_GOOGLE_LOGIN_URL)

        assert resp.status_code == 503
        assert "Google" in resp.json().get("detail", "")


# ---------------------------------------------------------------------------
# POST /api/v1/auth/google/exchange — valid one-time token
# ---------------------------------------------------------------------------


class TestGoogleExchangeValidToken:
    """Integration tests for ``POST /api/v1/auth/google/exchange`` — happy path."""

    @pytest.mark.integration
    async def test_exchange_valid_ott_returns_200_with_access_token(
        self, client: AsyncClient
    ) -> None:
        """A valid one-time token must be exchanged for a 200 with access_token.

        We register a local user first (to have a real user_id in the DB),
        mint an OTT for that user_id, then call the exchange endpoint.
        The response must be 200 with ``access_token`` and ``token_type``.
        """
        # Register a user so we have a real UUID in the database
        user_data = await _register_user(
            client,
            username="exchuser",
            email="exchuser@example.com",
            password="S3cureP@ss99",
        )
        user_id = uuid.UUID(user_data["id"])

        # Mint a fresh OTT for that user — no DB needed, it's a pure JWT
        ott = create_one_time_token(user_id)

        resp = await client.post(
            _GOOGLE_EXCHANGE_URL,
            json={"one_time_token": ott},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert len(body["access_token"]) > 0

    @pytest.mark.integration
    async def test_exchange_valid_ott_access_token_is_non_empty_jwt(
        self, client: AsyncClient
    ) -> None:
        """The returned access_token must be a non-empty string with JWT structure.

        A JWT has three dot-separated base64url segments.  We do not decode
        it here, but we validate the structure so a stray empty string or
        ``null`` does not slip through.
        """
        user_data = await _register_user(
            client,
            username="jwtcheckuser",
            email="jwtcheck@example.com",
            password="S3cureP@ss99",
        )
        user_id = uuid.UUID(user_data["id"])
        ott = create_one_time_token(user_id)

        resp = await client.post(
            _GOOGLE_EXCHANGE_URL,
            json={"one_time_token": ott},
        )

        assert resp.status_code == 200
        token = resp.json()["access_token"]
        parts = token.split(".")
        assert len(parts) == 3, f"Expected 3 JWT parts, got: {parts}"


# ---------------------------------------------------------------------------
# POST /api/v1/auth/google/exchange — invalid / expired / replayed token
# ---------------------------------------------------------------------------


class TestGoogleExchangeInvalidToken:
    """Integration tests for ``POST /api/v1/auth/google/exchange`` — error paths."""

    @pytest.mark.integration
    async def test_exchange_garbage_token_returns_401(
        self, client: AsyncClient
    ) -> None:
        """A completely invalid token string must return 401.

        The service cannot decode the JWT, so it must reject the exchange
        with HTTP 401 and a ``WWW-Authenticate: Bearer`` header.
        """
        resp = await client.post(
            _GOOGLE_EXCHANGE_URL,
            json={"one_time_token": "this.is.not.a.real.jwt"},
        )

        assert resp.status_code == 401
        assert "WWW-Authenticate" in resp.headers

    @pytest.mark.integration
    async def test_exchange_expired_ott_returns_401(self, client: AsyncClient) -> None:
        """An OTT whose ``exp`` claim is in the past must return 401.

        We craft the expired token manually rather than sleeping through
        the real expiry window.
        """
        from datetime import timedelta

        from jose import jwt

        from app.core.config import settings
        from app.core.constants import TOKEN_ALGORITHM

        user_id = uuid.uuid4()
        expired_payload: dict[str, Any] = {
            "sub": str(user_id),
            "jti": str(uuid.uuid4()),
            "ott": True,
            "iat": datetime.now(UTC) - timedelta(seconds=120),
            "exp": datetime.now(UTC) - timedelta(seconds=1),
        }
        expired_token = jwt.encode(
            expired_payload, settings.secret_key, algorithm=TOKEN_ALGORITHM
        )

        resp = await client.post(
            _GOOGLE_EXCHANGE_URL,
            json={"one_time_token": expired_token},
        )

        assert resp.status_code == 401

    @pytest.mark.integration
    async def test_exchange_replayed_ott_returns_401(self, client: AsyncClient) -> None:
        """A one-time token that has already been used must return 401 on second use.

        The first exchange must succeed (200); the second with the identical
        token must be rejected (401), demonstrating replay prevention.
        The DB-backed blocklist persists the JTI so replay is detected by
        IntegrityError on INSERT.
        """
        user_data = await _register_user(
            client,
            username="replayuser",
            email="replay@example.com",
            password="S3cureP@ss99",
        )
        user_id = uuid.UUID(user_data["id"])
        ott = create_one_time_token(user_id)

        # First use — must succeed
        first_resp = await client.post(
            _GOOGLE_EXCHANGE_URL,
            json={"one_time_token": ott},
        )
        assert first_resp.status_code == 200, first_resp.text

        # Second use — must be rejected
        second_resp = await client.post(
            _GOOGLE_EXCHANGE_URL,
            json={"one_time_token": ott},
        )
        assert second_resp.status_code == 401

    @pytest.mark.integration
    async def test_exchange_missing_body_returns_422(self, client: AsyncClient) -> None:
        """POST /exchange without a request body must return 422.

        The ``one_time_token`` field is required in :class:`OAuthExchangeRequest`;
        missing it triggers Pydantic validation before the service layer is reached.
        """
        resp = await client.post(_GOOGLE_EXCHANGE_URL, json={})
        assert resp.status_code == 422

    @pytest.mark.integration
    async def test_exchange_ott_for_nonexistent_user_returns_401(
        self, client: AsyncClient
    ) -> None:
        """An OTT for a user UUID that does not exist must return 401.

        The JWT is well-formed and not expired, but the user lookup inside
        :meth:`~app.services.auth_service.AuthService.exchange_one_time_token`
        returns ``None``, so the endpoint must return 401.
        """
        # Mint a valid OTT for a UUID that will never be in the DB
        ghost_user_id = uuid.uuid4()
        ott = create_one_time_token(ghost_user_id)

        resp = await client.post(
            _GOOGLE_EXCHANGE_URL,
            json={"one_time_token": ott},
        )

        assert resp.status_code == 401

    @pytest.mark.integration
    async def test_exchange_access_token_as_ott_returns_401(
        self, client: AsyncClient
    ) -> None:
        """A regular access token must not be accepted by the exchange endpoint.

        Access tokens do not carry the ``ott`` claim; attempting to use one
        for the exchange must be rejected with 401.
        """
        user_data = await _register_user(
            client,
            username="badottuser",
            email="badott@example.com",
            password="S3cureP@ss99",
        )
        user_id = uuid.UUID(user_data["id"])

        from app.core.security import create_access_token

        access_token = create_access_token(user_id)

        resp = await client.post(
            _GOOGLE_EXCHANGE_URL,
            json={"one_time_token": access_token},
        )

        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/v1/auth/token — password login blocked for Google-only accounts
# ---------------------------------------------------------------------------


class TestPasswordLoginBlockedForGoogleAccount:
    """Integration tests verifying that Google-only accounts cannot use /auth/token.

    A user whose ``provider`` is ``'google'`` has no local password.
    Attempting to authenticate them via the OAuth2 password form must
    return 401 rather than a server error.

    The ``db_session`` fixture (from ``conftest.py``) gives direct access to the
    same rolled-back transaction used by the ``client`` fixture, so a raw SQL
    ``UPDATE`` issued here is immediately visible to subsequent HTTP requests
    through the client without needing a separate commit.
    """

    @pytest.mark.integration
    async def test_google_only_user_password_login_returns_401(
        self, client: AsyncClient, db_session: object
    ) -> None:
        """POST /auth/token for a Google-only account must return 401.

        We register the user via the normal route (creates a local account),
        then simulate an OAuth migration by updating provider/hashed_password
        directly on the shared test session, and finally attempt a password login.

        Args:
            client: The test HTTP client.
            db_session: The per-test async session (same transaction as the client).
        """
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import AsyncSession

        assert isinstance(db_session, AsyncSession)

        # Step 1: Register a normal user so they exist in the DB
        await _register_user(
            client,
            username="googlonlyuser",
            email="googleonly@example.com",
            password="S3cureP@ss99",
        )

        # Step 2: Mutate the user row to become a Google-only account within the
        # same rolled-back transaction so the client picks up the change.
        await db_session.execute(
            text(
                "UPDATE users SET provider = 'google', hashed_password = NULL "
                "WHERE email = 'googleonly@example.com'"
            )
        )
        await db_session.flush()

        # Step 3: Attempt a password login — must be rejected
        resp = await client.post(
            _TOKEN_URL,
            data={"username": "googlonlyuser", "password": "S3cureP@ss99"},
        )

        assert resp.status_code == 401
        assert "WWW-Authenticate" in resp.headers

    @pytest.mark.integration
    async def test_local_user_password_login_still_succeeds(
        self, client: AsyncClient
    ) -> None:
        """A normal local-password user must still be able to log in after setup.

        Regression guard: creating Google-only users must not affect the
        password login flow for ordinary local accounts.
        """
        await _register_user(
            client,
            username="localpassuser",
            email="localpass@example.com",
            password="S3cureP@ss99",
        )

        resp = await client.post(
            _TOKEN_URL,
            data={"username": "localpassuser", "password": "S3cureP@ss99"},
        )

        assert resp.status_code == 200
        assert "access_token" in resp.json()

    @pytest.mark.integration
    async def test_google_only_user_email_login_also_returns_401(
        self, client: AsyncClient, db_session: object
    ) -> None:
        """POST /auth/token using the email of a Google-only account must return 401.

        The ``login()`` service method falls back to an email lookup when
        the username lookup fails; a Google account found by email must
        still be blocked.

        Args:
            client: The test HTTP client.
            db_session: The per-test async session (same transaction as the client).
        """
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import AsyncSession

        assert isinstance(db_session, AsyncSession)

        await _register_user(
            client,
            username="googlemailuser",
            email="googlemail@example.com",
            password="S3cureP@ss99",
        )

        await db_session.execute(
            text(
                "UPDATE users SET provider = 'google', hashed_password = NULL "
                "WHERE email = 'googlemail@example.com'"
            )
        )
        await db_session.flush()

        # Login attempt using the email address instead of username
        resp = await client.post(
            _TOKEN_URL,
            data={"username": "googlemail@example.com", "password": "S3cureP@ss99"},
        )

        assert resp.status_code == 401
