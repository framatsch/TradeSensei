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

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.auth import _get_service
from app.core.exceptions import InvalidCredentialsError, InvalidTokenError, UserAlreadyExistsError
from app.models.user import User

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_service():
    return AsyncMock()


@pytest.fixture
def override_dependency(mock_service):
    from app.main import app
    app.dependency_overrides[_get_service] = lambda: mock_service
    yield mock_service
    app.dependency_overrides.clear()


async def test_get_config(client: AsyncClient):
    resp = await client.get("/api/v1/auth/config")
    assert resp.status_code == 200
    assert "local_auth_enabled" in resp.json()


async def test_register_success(client: AsyncClient, override_dependency):
    user = User(
        id=uuid.uuid4(), 
        username="testuser", 
        email="test@test.com", 
        hashed_password="pw", 
        is_active=True, 
        created_at=datetime.now(UTC), 
        updated_at=datetime.now(UTC)
    )
    # mock model_validate if needed, or just let Pydantic read the ORM model
    override_dependency.register.return_value = user

    payload = {"username": "testuser", "email": "test@test.com", "password": "password123"}
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201


async def test_register_conflict(client: AsyncClient, override_dependency):
    override_dependency.register.side_effect = UserAlreadyExistsError()

    payload = {"username": "testuser", "email": "test@test.com", "password": "password123"}
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409


async def test_login_success(client: AsyncClient, override_dependency):
    override_dependency.login.return_value = ("access_tok", "refresh_tok")

    form_data = {"username": "testuser", "password": "password123"}
    resp = await client.post("/api/v1/auth/token", data=form_data)
    assert resp.status_code == 200
    assert resp.json()["access_token"] == "access_tok"
    assert "refresh_token" in resp.cookies


async def test_login_unauthorized(client: AsyncClient, override_dependency):
    override_dependency.login.side_effect = InvalidCredentialsError()

    form_data = {"username": "testuser", "password": "wrong"}
    resp = await client.post("/api/v1/auth/token", data=form_data)
    assert resp.status_code == 401


async def test_refresh_success(client: AsyncClient, override_dependency):
    override_dependency.refresh.return_value = ("new_access", "new_refresh")
    client.cookies.set("refresh_token", "old_refresh")
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 200
    assert resp.json()["access_token"] == "new_access"


async def test_refresh_missing_cookie(client: AsyncClient, override_dependency):
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401


async def test_refresh_invalid_cookie(client: AsyncClient, override_dependency):
    override_dependency.refresh.side_effect = InvalidCredentialsError()
    client.cookies.set("refresh_token", "bad_refresh")
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401


async def test_logout_success(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    client.cookies.set("refresh_token", "some_refresh")
    resp = await client.post("/api/v1/auth/logout", headers=primary_user["headers"])
    assert resp.status_code == 204


async def test_google_login(client: AsyncClient):
    resp = await client.get("/api/v1/auth/google", follow_redirects=False)
    assert resp.status_code in [302, 503]


async def test_google_exchange_success(client: AsyncClient, override_dependency):
    override_dependency.exchange_one_time_token.return_value = ("access_tok", "refresh_tok")
    resp = await client.post("/api/v1/auth/google/exchange", json={"one_time_token": "token"})
    assert resp.status_code == 200
    assert resp.json()["access_token"] == "access_tok"


async def test_google_exchange_unauthorized(client: AsyncClient, override_dependency):
    override_dependency.exchange_one_time_token.side_effect = InvalidCredentialsError()
    resp = await client.post("/api/v1/auth/google/exchange", json={"one_time_token": "bad_token"})
    assert resp.status_code == 401


@patch("app.api.v1.auth.send_password_reset_email", new_callable=AsyncMock)
async def test_forgot_password(mock_send, client: AsyncClient, override_dependency):
    user = User(id=uuid.uuid4(), username="testuser", email="test@test.com", hashed_password="pw")
    override_dependency.get_user_by_email.return_value = user
    resp = await client.post("/api/v1/auth/forgot-password", json={"email": "test@test.com"})
    assert resp.status_code in [200, 503]


@patch("app.api.v1.auth.consume_password_reset_token", new_callable=AsyncMock)
async def test_reset_password_success(mock_consume, client: AsyncClient, override_dependency):
    mock_consume.return_value = uuid.uuid4()
    resp = await client.post("/api/v1/auth/reset-password", json={"token": "reset_tok", "new_password": "new_password123"})
    assert resp.status_code == 200


@patch("app.api.v1.auth.consume_password_reset_token", new_callable=AsyncMock)
async def test_reset_password_unauthorized(mock_consume, client: AsyncClient, override_dependency):
    mock_consume.side_effect = InvalidTokenError()
    resp = await client.post("/api/v1/auth/reset-password", json={"token": "bad_tok", "new_password": "new_password123"})
    assert resp.status_code == 401


async def test_oidc_exchange_success(client: AsyncClient, override_dependency):
    override_dependency.exchange_one_time_token.return_value = ("access_tok", "refresh_tok")
    resp = await client.post("/api/v1/auth/oidc/exchange", json={"one_time_token": "token"})
    assert resp.status_code == 200


async def test_oidc_exchange_unauthorized(client: AsyncClient, override_dependency):
    override_dependency.exchange_one_time_token.side_effect = InvalidCredentialsError()
    resp = await client.post("/api/v1/auth/oidc/exchange", json={"one_time_token": "bad_token"})
    assert resp.status_code == 401

@patch("app.api.v1.auth._oauth")
async def test_google_callback_success(mock_oauth, client: AsyncClient, override_dependency):
    mock_oauth.google.authorize_access_token = AsyncMock(return_value={"userinfo": {"sub": "123", "email": "test@google.com", "name": "Google User"}})
    override_dependency.external_oauth_login.return_value = ("access_tok", "refresh_tok", "one_time_tok")
    
    resp = await client.get("/api/v1/auth/google/callback", follow_redirects=False)
    assert resp.status_code == 302
    assert "token=one_time_tok" in resp.headers["location"]

@patch("app.api.v1.auth._oauth")
async def test_google_callback_unauthorized(mock_oauth, client: AsyncClient, override_dependency):
    mock_oauth.google.authorize_access_token = AsyncMock(return_value={"userinfo": {"sub": "123", "email": "test@google.com", "name": "Google User"}})
    override_dependency.external_oauth_login.side_effect = InvalidCredentialsError()
    
    resp = await client.get("/api/v1/auth/google/callback", follow_redirects=False)
    assert resp.status_code == 302
    assert "error=oauth_failed" in resp.headers["location"]

@patch("app.api.v1.auth._oauth")
async def test_oidc_callback_success(mock_oauth, client: AsyncClient, override_dependency):
    mock_oauth.oidc.authorize_access_token = AsyncMock(return_value={"userinfo": {"sub": "123", "email": "test@oidc.com", "preferred_username": "OIDC User"}})
    override_dependency.external_oauth_login.return_value = ("access_tok", "refresh_tok", "one_time_tok")
    
    resp = await client.get("/api/v1/auth/oidc/callback", follow_redirects=False)
    assert resp.status_code == 302
    assert "token=one_time_tok" in resp.headers["location"]

@patch("app.api.v1.auth._oauth")
async def test_oidc_callback_unauthorized(mock_oauth, client: AsyncClient, override_dependency):
    mock_oauth.oidc.authorize_access_token = AsyncMock(return_value={"userinfo": {"sub": "123", "email": "test@oidc.com"}})
    override_dependency.external_oauth_login.side_effect = InvalidCredentialsError()
    
    resp = await client.get("/api/v1/auth/oidc/callback", follow_redirects=False)
    assert resp.status_code == 302
    assert "error=oauth_failed" in resp.headers["location"]

@patch("app.api.v1.auth._oauth")
async def test_google_callback_oauth_error(mock_oauth, client: AsyncClient):
    from authlib.integrations.starlette_client import OAuthError
    mock_oauth.google.authorize_access_token = AsyncMock(side_effect=OAuthError())
    resp = await client.get("/api/v1/auth/google/callback", follow_redirects=False)
    assert resp.status_code == 302
    assert "error=oauth_cancelled" in resp.headers["location"]

@patch("app.api.v1.auth._oauth")
async def test_oidc_callback_oauth_error(mock_oauth, client: AsyncClient):
    from authlib.integrations.starlette_client import OAuthError
    mock_oauth.oidc.authorize_access_token = AsyncMock(side_effect=OAuthError())
    resp = await client.get("/api/v1/auth/oidc/callback", follow_redirects=False)
    assert resp.status_code == 302
    assert "error=oauth_cancelled" in resp.headers["location"]
