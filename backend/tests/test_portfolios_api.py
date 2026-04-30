"""Integration tests for portfolio CRUD endpoints."""

import uuid

import pytest
from httpx import AsyncClient

_REGISTER_URL = "/api/v1/auth/register"
_TOKEN_URL = "/api/v1/auth/token"
_PORTFOLIOS_URL = "/api/v1/portfolios"


async def _register_and_login(client: AsyncClient, prefix: str) -> dict[str, str]:
    suffix = uuid.uuid4().hex[:8]
    username = f"{prefix}_{suffix}"
    email = f"{prefix}_{suffix}@example.com"
    password = "PortfolioP@ss99"

    reg = await client.post(
        _REGISTER_URL,
        json={"username": username, "email": email, "password": password},
    )
    assert reg.status_code == 201, reg.text

    login = await client.post(
        _TOKEN_URL,
        data={"username": username, "password": password},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_portfolio_crud_happy_path(client: AsyncClient) -> None:
    headers = await _register_and_login(client, "portfolio_owner")

    create = await client.post(
        _PORTFOLIOS_URL,
        headers=headers,
        json={"name": "Main", "base_currency": "USD", "color_hex": "#123456"},
    )
    assert create.status_code == 201, create.text
    portfolio_id = create.json()["data"]["id"]

    listed = await client.get(_PORTFOLIOS_URL, headers=headers)
    assert listed.status_code == 200, listed.text
    assert len(listed.json()["data"]) == 1
    assert listed.json()["data"][0]["id"] == portfolio_id

    fetched = await client.get(f"{_PORTFOLIOS_URL}/{portfolio_id}", headers=headers)
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["data"]["name"] == "Main"

    patched = await client.patch(
        f"{_PORTFOLIOS_URL}/{portfolio_id}",
        headers=headers,
        json={"name": "Main Renamed", "color_hex": "#654321"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["name"] == "Main Renamed"

    deleted = await client.delete(f"{_PORTFOLIOS_URL}/{portfolio_id}", headers=headers)
    assert deleted.status_code == 204, deleted.text

    after_delete = await client.get(
        f"{_PORTFOLIOS_URL}/{portfolio_id}", headers=headers
    )
    assert after_delete.status_code == 404, after_delete.text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_portfolio_foreign_and_missing_access_returns_404(
    client: AsyncClient,
) -> None:
    owner_headers = await _register_and_login(client, "portfolio_owner2")
    other_headers = await _register_and_login(client, "portfolio_other")

    created = await client.post(
        _PORTFOLIOS_URL,
        headers=owner_headers,
        json={"name": "Owner Portfolio", "base_currency": "USD"},
    )
    assert created.status_code == 201, created.text
    portfolio_id = created.json()["data"]["id"]

    foreign_get = await client.get(
        f"{_PORTFOLIOS_URL}/{portfolio_id}", headers=other_headers
    )
    assert foreign_get.status_code == 404, foreign_get.text

    foreign_patch = await client.patch(
        f"{_PORTFOLIOS_URL}/{portfolio_id}",
        headers=other_headers,
        json={"name": "Nope"},
    )
    assert foreign_patch.status_code == 404, foreign_patch.text

    foreign_delete = await client.delete(
        f"{_PORTFOLIOS_URL}/{portfolio_id}", headers=other_headers
    )
    assert foreign_delete.status_code == 404, foreign_delete.text

    missing_get = await client.get(
        f"{_PORTFOLIOS_URL}/{uuid.uuid4()}", headers=owner_headers
    )
    assert missing_get.status_code == 404, missing_get.text
