import uuid
from typing import Any

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_settings_defaults(
    client: AsyncClient, primary_user: dict[str, Any]
) -> None:
    """Task 2.1: verify missing keys return defaults."""
    res = await client.get("/api/v1/users/me/settings", headers=primary_user["headers"])
    assert res.status_code == 200, res.text
    data = res.json()["data"]

    assert data["chart_candles_before"] == 20
    assert data["chart_candles_after"] == 10
    assert data["chart_show_post_exit"] is False
    assert data["default_portfolio_id"] is None
    assert data["home_route"] == "/dashboard"


@pytest.mark.asyncio
async def test_put_settings_all_fields(
    client: AsyncClient, primary_user: dict[str, Any]
) -> None:
    """Task 2.2: write all five fields; read back; verify values match."""
    port_id = str(uuid.uuid4())
    payload = {
        "chart_candles_before": 50,
        "chart_candles_after": 25,
        "chart_show_post_exit": True,
        "default_portfolio_id": port_id,
        "home_route": "/dashboard/trades",
    }

    res = await client.put(
        "/api/v1/users/me/settings", headers=primary_user["headers"], json=payload
    )
    assert res.status_code == 200, res.text
    data = res.json()["data"]

    assert data["chart_candles_before"] == 50
    assert data["chart_candles_after"] == 25
    assert data["chart_show_post_exit"] is True
    assert data["default_portfolio_id"] == port_id
    assert data["home_route"] == "/dashboard/trades"

    # Read back
    res2 = await client.get(
        "/api/v1/users/me/settings", headers=primary_user["headers"]
    )
    assert res2.status_code == 200, res2.text
    data2 = res2.json()["data"]

    assert data2["chart_candles_before"] == 50
    assert data2["chart_candles_after"] == 25
    assert data2["chart_show_post_exit"] is True
    assert data2["default_portfolio_id"] == port_id
    assert data2["home_route"] == "/dashboard/trades"


@pytest.mark.asyncio
async def test_put_settings_partial_update(
    client: AsyncClient, primary_user: dict[str, Any]
) -> None:
    """Task 2.3: Partial update (only chart_candles_before) does not clobber the other four keys."""
    # First set non-default values
    port_id = str(uuid.uuid4())
    initial = {
        "chart_candles_before": 50,
        "chart_candles_after": 25,
        "chart_show_post_exit": True,
        "default_portfolio_id": port_id,
        "home_route": "/dashboard/trades",
    }
    res = await client.put(
        "/api/v1/users/me/settings", headers=primary_user["headers"], json=initial
    )
    assert res.status_code == 200

    # Partial update
    res2 = await client.put(
        "/api/v1/users/me/settings",
        headers=primary_user["headers"],
        json={"chart_candles_before": 60},
    )
    assert res2.status_code == 200, res2.text
    data2 = res2.json()["data"]

    assert data2["chart_candles_before"] == 60
    assert data2["chart_candles_after"] == 25
    assert data2["chart_show_post_exit"] is True
    assert data2["default_portfolio_id"] == port_id
    assert data2["home_route"] == "/dashboard/trades"


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_val", [0, -1])
async def test_put_settings_invalid_candles(
    client: AsyncClient, primary_user: dict[str, Any], invalid_val: int
) -> None:
    """Task 2.4: chart_candles_before = 0 or negative rejected with HTTP 422."""
    res = await client.put(
        "/api/v1/users/me/settings",
        headers=primary_user["headers"],
        json={"chart_candles_before": invalid_val},
    )
    assert res.status_code == 422, res.text


@pytest.mark.asyncio
async def test_put_settings_default_portfolio_id(
    client: AsyncClient, primary_user: dict[str, Any]
) -> None:
    """Task 2.5: default_portfolio_id set to a valid UUID string; read back; verify stored correctly."""
    port_id = str(uuid.uuid4())
    res = await client.put(
        "/api/v1/users/me/settings",
        headers=primary_user["headers"],
        json={"default_portfolio_id": port_id},
    )
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["default_portfolio_id"] == port_id

    res2 = await client.get(
        "/api/v1/users/me/settings", headers=primary_user["headers"]
    )
    assert res2.status_code == 200
    data2 = res2.json()["data"]
    assert data2["default_portfolio_id"] == port_id


@pytest.mark.asyncio
async def test_put_settings_valid_home_route(
    client: AsyncClient, primary_user: dict[str, Any]
) -> None:
    """Task 2.6: home_route set to "/dashboard/trades"; read back correctly."""
    res = await client.put(
        "/api/v1/users/me/settings",
        headers=primary_user["headers"],
        json={"home_route": "/dashboard/trades"},
    )
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["home_route"] == "/dashboard/trades"

    res2 = await client.get(
        "/api/v1/users/me/settings", headers=primary_user["headers"]
    )
    assert res2.status_code == 200
    data2 = res2.json()["data"]
    assert data2["home_route"] == "/dashboard/trades"


@pytest.mark.asyncio
async def test_put_settings_invalid_home_route(
    client: AsyncClient, primary_user: dict[str, Any]
) -> None:
    """Task 2.7: home_route with an invalid value rejected with HTTP 422."""
    res = await client.put(
        "/api/v1/users/me/settings",
        headers=primary_user["headers"],
        json={"home_route": "/dashboard/invalid"},
    )
    assert res.status_code == 422, res.text
