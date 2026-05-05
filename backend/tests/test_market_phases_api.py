"""Integration tests for market phases API."""

import uuid

import pytest
from httpx import AsyncClient


async def _auth_headers(client: AsyncClient, *, prefix: str) -> dict[str, str]:
    suffix = uuid.uuid4().hex[:8]
    username = f"{prefix}_{suffix}"
    email = f"{prefix}_{suffix}@example.com"
    password = "PhaseP@ss99"

    register = await client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    assert register.status_code == 201, register.text

    login = await client.post(
        "/api/v1/auth/token",
        data={"username": username, "password": password},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.integration
async def test_market_phases_get_post_duplicate_label_409(client: AsyncClient) -> None:
    headers = await _auth_headers(client, prefix="phase")

    list_resp = await client.get("/api/v1/market-phases", headers=headers)
    assert list_resp.status_code == 200, list_resp.text

    created = await client.post(
        "/api/v1/market-phases",
        headers=headers,
        json={"name": "trend", "label": "Trend", "color_hex": "#22c55e"},
    )
    assert created.status_code == 201, created.text

    duplicate_label = await client.post(
        "/api/v1/market-phases",
        headers=headers,
        json={"name": "trend2", "label": "Trend", "color_hex": "#22c55e"},
    )
    assert duplicate_label.status_code == 409, duplicate_label.text
