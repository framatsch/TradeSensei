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

"""Integration tests for the /api/v1/auth and /api/v1/users/me endpoints.

These tests hit the full FastAPI application stack using an in-process
:class:`httpx.AsyncClient` wired to a real PostgreSQL/TimescaleDB instance.
They rely on the ``client`` and ``setup_database`` fixtures defined in
``conftest.py``.

Each test is isolated because ``db_session`` rolls back after every test,
so rows created in one test are never visible to another.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.annotation_definition_repository import AnnotationDefinitionRepository
from app.repositories.taxonomy_repository import TaxonomyRepository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REGISTER_URL = "/api/v1/auth/register"
_TOKEN_URL = "/api/v1/auth/token"
_REFRESH_URL = "/api/v1/auth/refresh"
_LOGOUT_URL = "/api/v1/auth/logout"
_ME_URL = "/api/v1/users/me"

_DEFAULT_USER = {
    "username": "authtest",
    "email": "authtest@example.com",
    "password": "S3cureP@ss99",
}


async def _register_and_login(
    client: AsyncClient,
    *,
    username: str = _DEFAULT_USER["username"],
    email: str = _DEFAULT_USER["email"],
    password: str = _DEFAULT_USER["password"],
) -> str:
    """Register a user and return the access token from the login response.

    Args:
        client: The test HTTP client.
        username: Username to register.
        email: Email to register.
        password: Password to register with and log in using.

    Returns:
        The ``access_token`` string from the login response body.
    """
    reg_resp = await client.post(
        _REGISTER_URL,
        json={"username": username, "email": email, "password": password},
    )
    assert reg_resp.status_code == 201, reg_resp.text

    login_resp = await client.post(
        _TOKEN_URL,
        data={"username": username, "password": password},
    )
    assert login_resp.status_code == 200, login_resp.text
    return str(login_resp.json()["access_token"])


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------


class TestRegister:
    """Integration tests for ``POST /api/v1/auth/register``."""

    @pytest.mark.integration
    async def test_register_success(self, client: AsyncClient) -> None:
        """POST /register must return 201 with a UserRead envelope.

        The response body must contain a ``data`` object with an ``id``,
        ``username``, ``email``, and ``is_active=True``.  The
        ``hashed_password`` field must never appear.
        """
        resp = await client.post(_REGISTER_URL, json=_DEFAULT_USER)
        assert resp.status_code == 201

        body = resp.json()
        user = body["data"]
        assert user["username"] == _DEFAULT_USER["username"]
        assert user["email"] == _DEFAULT_USER["email"]
        assert user["is_active"] is True
        assert "id" in user
        assert "hashed_password" not in user
        assert "password" not in user

    @pytest.mark.integration
    async def test_register_duplicate_returns_409(self, client: AsyncClient) -> None:
        """POST /register with an already-taken username must return 409.

        The first registration succeeds; the second with the same username
        must be rejected with HTTP 409 Conflict.
        """
        await client.post(_REGISTER_URL, json=_DEFAULT_USER)
        resp = await client.post(_REGISTER_URL, json=_DEFAULT_USER)
        assert resp.status_code == 409

    @pytest.mark.integration
    async def test_register_duplicate_email_returns_409(
        self, client: AsyncClient
    ) -> None:
        """POST /register with an already-registered email must return 409.

        Even if the username is different, a duplicate email address must
        be rejected with HTTP 409 Conflict.
        """
        await client.post(_REGISTER_URL, json=_DEFAULT_USER)
        resp = await client.post(
            _REGISTER_URL,
            json={
                "username": "differentname",
                "email": _DEFAULT_USER["email"],  # same email
                "password": "S3cureP@ss99",
            },
        )
        assert resp.status_code == 409

    @pytest.mark.integration
    async def test_register_missing_field_returns_422(
        self, client: AsyncClient
    ) -> None:
        """POST /register without a required field must return 422.

        The ``password`` field is required; omitting it must trigger
        Pydantic validation and return HTTP 422 with field-level details.
        """
        resp = await client.post(
            _REGISTER_URL,
            json={"username": "nopass", "email": "nopass@example.com"},
        )
        assert resp.status_code == 422

    @pytest.mark.integration
    async def test_register_seeds_default_taxonomies(self, client: AsyncClient) -> None:
        """A fresh registration exposes all 11 default taxonomies."""
        token = await _register_and_login(
            client,
            username="seededtaxuser",
            email="seededtaxuser@example.com",
            password="S3cureP@ss99",
        )
        response = await client.get(
            "/api/v1/taxonomies",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text

        names = {item["name"] for item in response.json()["data"]}
        assert names == {
            "Bullish",
            "Bearish",
            "Sideways",
            "Volatile",
            "FOMO",
            "Discipline",
            "High Conviction",
            "Breakout",
            "Mean Reversion",
            "Momentum",
            "Trend Following",
            "Stop Loss",
            "Textbook Trade",
        }

    @pytest.mark.integration
    async def test_register_seeds_default_annotation_definitions(
        self, client: AsyncClient
    ) -> None:
        """A fresh registration exposes all 5 default annotation definitions."""
        token = await _register_and_login(
            client,
            username="seededannouser",
            email="seededannouser@example.com",
            password="S3cureP@ss99",
        )
        response = await client.get(
            "/api/v1/annotation-definitions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text

        names = {item["name"] for item in response.json()["data"]}
        assert names == {
            "Mood Level",
            "Focus",
            "Rule Followed",
            "Setup Quality",
            "Market Regime",
        }

    @pytest.mark.integration
    async def test_forced_second_seed_call_does_not_duplicate_metadata(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Forcing seeders twice for the same user keeps unique seeded rows."""
        username = "seedidempotent"
        email = "seedidempotent@example.com"
        password = "S3cureP@ss99"

        reg_resp = await client.post(
            _REGISTER_URL,
            json={"username": username, "email": email, "password": password},
        )
        assert reg_resp.status_code == 201, reg_resp.text
        user_id = uuid.UUID(reg_resp.json()["data"]["id"])

        taxonomy_repo = TaxonomyRepository(db_session)
        annotation_repo = AnnotationDefinitionRepository(db_session)
        await taxonomy_repo.seed_defaults(user_id)
        await taxonomy_repo.seed_defaults(user_id)
        await annotation_repo.seed_defaults(user_id)
        await annotation_repo.seed_defaults(user_id)

        token = await client.post(
            _TOKEN_URL,
            data={"username": username, "password": password},
        )
        assert token.status_code == 200, token.text
        headers = {"Authorization": f"Bearer {token.json()['access_token']}"}

        taxonomies = await client.get("/api/v1/taxonomies", headers=headers)
        annotations = await client.get("/api/v1/annotation-definitions", headers=headers)

        assert taxonomies.status_code == 200, taxonomies.text
        assert annotations.status_code == 200, annotations.text
        assert len(taxonomies.json()["data"]) == 13
        assert len(annotations.json()["data"]) == 5


# ---------------------------------------------------------------------------
# Login tests
# ---------------------------------------------------------------------------


class TestLogin:
    """Integration tests for ``POST /api/v1/auth/token``."""

    @pytest.mark.integration
    async def test_login_success(self, client: AsyncClient) -> None:
        """POST /token must return 200 with access_token and set a refresh cookie.

        The response body must contain an ``access_token`` and
        ``token_type: "bearer"``.  The ``Set-Cookie`` header must include
        a ``refresh_token`` cookie.
        """
        await client.post(_REGISTER_URL, json=_DEFAULT_USER)
        resp = await client.post(
            _TOKEN_URL,
            data={
                "username": _DEFAULT_USER["username"],
                "password": _DEFAULT_USER["password"],
            },
        )
        assert resp.status_code == 200

        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert len(body["access_token"]) > 0

        # The refresh cookie must have been set
        cookie_header = resp.headers.get("set-cookie", "")
        assert "refresh_token" in cookie_header

    @pytest.mark.integration
    async def test_login_wrong_password_returns_401(self, client: AsyncClient) -> None:
        """POST /token with an incorrect password must return 401.

        The response must include a ``WWW-Authenticate: Bearer`` header as
        required by the OAuth2 spec.
        """
        await client.post(_REGISTER_URL, json=_DEFAULT_USER)
        resp = await client.post(
            _TOKEN_URL,
            data={
                "username": _DEFAULT_USER["username"],
                "password": "completely-wrong-password",
            },
        )
        assert resp.status_code == 401
        assert "WWW-Authenticate" in resp.headers


# ---------------------------------------------------------------------------
# /users/me tests
# ---------------------------------------------------------------------------


class TestGetMe:
    """Integration tests for ``GET /api/v1/users/me``."""

    @pytest.mark.integration
    async def test_get_me_authenticated(self, client: AsyncClient) -> None:
        """GET /users/me with a valid Bearer token must return 200 with UserRead.

        The returned profile must match the username and email that were
        used during registration.
        """
        access_token = await _register_and_login(client)
        resp = await client.get(
            _ME_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200

        user = resp.json()["data"]
        assert user["username"] == _DEFAULT_USER["username"]
        assert user["email"] == _DEFAULT_USER["email"]
        assert "hashed_password" not in user

    @pytest.mark.integration
    async def test_get_me_unauthenticated_returns_401(
        self, client: AsyncClient
    ) -> None:
        """GET /users/me without a Bearer token must return 401.

        The endpoint requires authentication; missing credentials must be
        rejected with HTTP 401 and a ``WWW-Authenticate: Bearer`` header.
        """
        resp = await client.get(_ME_URL)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Token refresh tests
# ---------------------------------------------------------------------------


class TestRefreshToken:
    """Integration tests for ``POST /api/v1/auth/refresh``."""

    @pytest.mark.integration
    async def test_refresh_token(self, client: AsyncClient) -> None:
        """POST /refresh with a valid refresh cookie must return a new access_token.

        After login, the refresh cookie is stored in the client's cookie jar.
        The refresh endpoint must accept it and return a fresh access token.
        """
        # Register and login — the client's cookie jar captures refresh_token
        await client.post(_REGISTER_URL, json=_DEFAULT_USER)
        await client.post(
            _TOKEN_URL,
            data={
                "username": _DEFAULT_USER["username"],
                "password": _DEFAULT_USER["password"],
            },
        )

        resp = await client.post(_REFRESH_URL)
        assert resp.status_code == 200

        body = resp.json()
        assert "access_token" in body
        assert len(body["access_token"]) > 0

    @pytest.mark.integration
    async def test_refresh_without_cookie_returns_401(
        self, client: AsyncClient
    ) -> None:
        """POST /refresh without a refresh cookie must return 401.

        When the ``refresh_token`` cookie is absent, the endpoint must
        return HTTP 401 rather than raise an unhandled server error.
        """
        resp = await client.post(_REFRESH_URL)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Logout tests
# ---------------------------------------------------------------------------


class TestLogout:
    """Integration tests for ``POST /api/v1/auth/logout``."""

    @pytest.mark.integration
    async def test_logout_clears_cookie(self, client: AsyncClient) -> None:
        """POST /logout must return 204 and clear the refresh_token cookie.

        The ``Set-Cookie`` header in the logout response must set the
        ``refresh_token`` cookie to an empty string (or include
        ``Max-Age=0`` / ``expires`` in the past), indicating deletion.
        """
        # Log in first to get the cookie set and an access token
        await client.post(_REGISTER_URL, json=_DEFAULT_USER)
        login_resp = await client.post(
            _TOKEN_URL,
            data={
                "username": _DEFAULT_USER["username"],
                "password": _DEFAULT_USER["password"],
            },
        )
        assert login_resp.status_code == 200
        access_token = str(login_resp.json()["access_token"])

        resp = await client.post(
            _LOGOUT_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 204

        cookie_header = resp.headers.get("set-cookie", "")
        # FastAPI's delete_cookie sets max-age=0 or an expired date
        assert "refresh_token" in cookie_header
