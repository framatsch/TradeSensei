"""Integration tests for personal access token endpoints and PAT auth."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_pat
from app.models.pat import PersonalAccessToken

_REGISTER_URL = "/api/v1/auth/register"
_TOKEN_URL = "/api/v1/auth/token"
_TOKENS_URL = "/api/v1/settings/tokens"
_ME_URL = "/api/v1/users/me"
_MCP_MESSAGES_URL = "/mcp/messages"


async def _register_and_login(client: AsyncClient) -> dict[str, str]:
    suffix = str(uuid.uuid4())[:8]
    username = f"pat_user_{suffix}"
    email = f"pat_{suffix}@example.com"
    password = "S3cureP@ss99"

    register = await client.post(
        _REGISTER_URL,
        json={"username": username, "email": email, "password": password},
    )
    assert register.status_code == 201, register.text

    login = await client.post(
        _TOKEN_URL,
        data={"username": username, "password": password},
    )
    assert login.status_code == 200, login.text
    access_token = str(login.json()["access_token"])
    return {"Authorization": f"Bearer {access_token}"}


@pytest.mark.integration
async def test_pat_crud_endpoints(client: AsyncClient) -> None:
    headers = await _register_and_login(client)

    create = await client.post(
        _TOKENS_URL,
        json={"name": "Claude Desktop", "expires_at": "2030-01-01T00:00:00Z"},
        headers=headers,
    )
    assert create.status_code == 201, create.text
    created = create.json()["data"]
    assert created["name"] == "Claude Desktop"
    assert created["token"]
    assert "token_hash" not in created

    listed = await client.get(_TOKENS_URL, headers=headers)
    assert listed.status_code == 200, listed.text
    items = listed.json()["data"]
    assert len(items) == 1
    assert items[0]["id"] == created["id"]
    assert items[0]["is_revoked"] is False

    revoke = await client.delete(f"{_TOKENS_URL}/{created['id']}", headers=headers)
    assert revoke.status_code == 204, revoke.text

    listed_after = await client.get(_TOKENS_URL, headers=headers)
    assert listed_after.status_code == 200, listed_after.text
    assert listed_after.json()["data"][0]["is_revoked"] is True


@pytest.mark.integration
async def test_pat_auth_valid_token_updates_last_used(client: AsyncClient) -> None:
    headers = await _register_and_login(client)

    create = await client.post(
        _TOKENS_URL,
        json={"name": "MCP Client"},
        headers=headers,
    )
    assert create.status_code == 201, create.text
    plain_token = create.json()["data"]["token"]

    mcp = await client.post(
        _MCP_MESSAGES_URL,
        json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
        headers={"Authorization": f"Bearer {plain_token}"},
    )
    assert mcp.status_code == 200, mcp.text
    assert mcp.json()["result"]["pong"] is True

    listed = await client.get(_TOKENS_URL, headers=headers)
    assert listed.status_code == 200, listed.text
    assert listed.json()["data"][0]["last_used_at"] is not None


@pytest.mark.integration
async def test_pat_auth_rejects_expired_token(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await _register_and_login(client)
    me = await client.get(_ME_URL, headers=headers)
    assert me.status_code == 200, me.text
    user_id = uuid.UUID(str(me.json()["data"]["id"]))

    plain_token = f"expired-{uuid.uuid4()}"
    db_session.add(
        PersonalAccessToken(
            user_id=user_id,
            name="Expired token",
            token_hash=hash_pat(plain_token),
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
            is_revoked=False,
        )
    )
    await db_session.flush()

    mcp = await client.post(
        _MCP_MESSAGES_URL,
        json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
        headers={"Authorization": f"Bearer {plain_token}"},
    )
    assert mcp.status_code == 401, mcp.text


@pytest.mark.integration
async def test_pat_auth_rejects_revoked_token(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await _register_and_login(client)
    me = await client.get(_ME_URL, headers=headers)
    assert me.status_code == 200, me.text
    user_id = uuid.UUID(str(me.json()["data"]["id"]))

    plain_token = f"revoked-{uuid.uuid4()}"
    db_session.add(
        PersonalAccessToken(
            user_id=user_id,
            name="Revoked token",
            token_hash=hash_pat(plain_token),
            expires_at=datetime.now(UTC) + timedelta(days=30),
            is_revoked=True,
        )
    )
    await db_session.flush()

    mcp = await client.post(
        _MCP_MESSAGES_URL,
        json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
        headers={"Authorization": f"Bearer {plain_token}"},
    )
    assert mcp.status_code == 401, mcp.text


@pytest.mark.integration
async def test_pat_auth_rejects_missing_token(client: AsyncClient) -> None:
    mcp = await client.post(
        _MCP_MESSAGES_URL,
        json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
    )
    assert mcp.status_code == 401, mcp.text
