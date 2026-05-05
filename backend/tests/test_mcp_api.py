"""Integration tests for MCP transport endpoints."""

import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from tests.test_pat_api import _register_and_login


async def _create_pat(client: AsyncClient) -> str:
    headers = await _register_and_login(client)
    created = await client.post(
        "/api/v1/settings/tokens",
        json={"name": f"MCP-{uuid.uuid4().hex[:6]}"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    return str(created.json()["data"]["token"])


@pytest.mark.integration
async def test_mcp_sse_missing_auth_returns_401(client: AsyncClient) -> None:
    response = await client.get("/mcp/sse")
    assert response.status_code == 401


@pytest.mark.integration
async def test_mcp_sse_invalid_pat_returns_401(client: AsyncClient) -> None:
    response = await client.get(
        "/mcp/sse",
        headers={"Authorization": "Bearer not-a-valid-token"},
    )
    assert response.status_code == 401


@pytest.mark.integration
@patch("app.api.mcp._KEEPALIVE_INTERVAL", 0.05)
async def test_mcp_sse_valid_pat_returns_ready_event(client: AsyncClient) -> None:
    token = await _create_pat(client)

    async with client.stream(
        "GET",
        "/mcp/sse",
        headers={"Authorization": f"Bearer {token}", "x-test-no-sse-keepalive": "true"},
    ) as response:
        assert response.status_code == 200, await response.aread()
        assert response.headers["content-type"].startswith("text/event-stream")
        first_line = ""
        async for line in response.aiter_lines():
            if line.startswith("event:"):
                first_line = line
                break

    assert "event: ready" in first_line


@pytest.mark.integration
async def test_mcp_sse_invalid_session_id_returns_400(client: AsyncClient) -> None:
    token = await _create_pat(client)
    response = await client.get(
        "/mcp/sse?session_id=bad!*session",
        headers={"Authorization": f"Bearer {token}", "x-test-no-sse-keepalive": "true"},
    )
    assert response.status_code == 400


@pytest.mark.integration
@patch("app.api.mcp._KEEPALIVE_INTERVAL", 0.05)
async def test_mcp_sse_valid_session_id_echoed_in_ready_event(client: AsyncClient) -> None:
    token = await _create_pat(client)
    session_id = "session_123"

    async with client.stream(
        "GET",
        f"/mcp/sse?session_id={session_id}",
        headers={"Authorization": f"Bearer {token}", "x-test-no-sse-keepalive": "true"},
    ) as response:
        assert response.status_code == 200, await response.aread()
        first_line = ""
        session_data = ""
        async for line in response.aiter_lines():
            if line.startswith("event:"):
                first_line = line
            if line.startswith("data:"):
                session_data = line
                break

    assert "event: ready" in first_line
    assert "session_id" in session_data
    assert session_id in session_data


@pytest.mark.integration
async def test_mcp_messages_without_pat_returns_401(client: AsyncClient) -> None:
    response = await client.post(
        "/mcp/messages",
        json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
    )
    assert response.status_code == 401
