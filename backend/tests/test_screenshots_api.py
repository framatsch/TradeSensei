"""Integration tests for trade screenshots API."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from app.core.constants import SCREENSHOT_MAX_FILE_SIZE_MB
from tests.test_trades_api import _create_portfolio_and_account, _get_auth_headers


async def _create_trade(
    client: AsyncClient,
    headers: dict[str, str],
    portfolio_id: str,
    account_id: str,
) -> str:
    payload = {
        "account_id": account_id,
        "symbol": "AAPL",
        "direction": "LONG",
        "asset_class": "EQUITY",
        "quantity": "1",
        "entry_price": "100",
        "opened_at": datetime(2026, 1, 1, 10, 0, tzinfo=UTC).isoformat(),
    }
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return str(response.json()["data"]["id"])


@pytest.mark.integration
async def test_screenshots_upload_and_delete_happy_path(client: AsyncClient) -> None:
    headers = await _get_auth_headers(client, "shots")
    portfolio_id, account_id = await _create_portfolio_and_account(client, headers, "shots")
    trade_id = await _create_trade(client, headers, portfolio_id, account_id)

    upload = await client.post(
        f"/api/v1/trades/{trade_id}/screenshots",
        files={"file": ("chart.png", b"fake-png", "image/png")},
        headers=headers,
    )
    assert upload.status_code == 201, upload.text
    image_urls = upload.json()["data"]["image_urls"]
    assert image_urls
    uploaded_url = str(image_urls[-1])

    filename = uploaded_url.rsplit("/", 1)[-1]
    deleted = await client.delete(
        f"/api/v1/trades/{trade_id}/screenshots/{filename}",
        headers=headers,
    )
    assert deleted.status_code == 200, deleted.text
    assert uploaded_url not in deleted.json()["data"]["image_urls"]


@pytest.mark.integration
async def test_screenshots_upload_oversized_returns_413(client: AsyncClient) -> None:
    headers = await _get_auth_headers(client, "shots413")
    portfolio_id, account_id = await _create_portfolio_and_account(
        client, headers, "shots413"
    )
    trade_id = await _create_trade(client, headers, portfolio_id, account_id)

    big = b"a" * ((SCREENSHOT_MAX_FILE_SIZE_MB * 1024 * 1024) + 1)
    response = await client.post(
        f"/api/v1/trades/{trade_id}/screenshots",
        files={"file": ("big.png", big, "image/png")},
        headers=headers,
    )
    assert response.status_code == 413, response.text


@pytest.mark.integration
async def test_screenshots_upload_disallowed_content_type_returns_415(
    client: AsyncClient,
) -> None:
    headers = await _get_auth_headers(client, "shots415")
    portfolio_id, account_id = await _create_portfolio_and_account(
        client, headers, "shots415"
    )
    trade_id = await _create_trade(client, headers, portfolio_id, account_id)

    response = await client.post(
        f"/api/v1/trades/{trade_id}/screenshots",
        files={"file": ("doc.pdf", b"pdf", "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 415, response.text


@pytest.mark.integration
async def test_screenshots_upload_non_owner_returns_404(client: AsyncClient) -> None:
    owner_headers = await _get_auth_headers(client, "shotsowner")
    other_headers = await _get_auth_headers(client, "shotsother")
    portfolio_id, account_id = await _create_portfolio_and_account(
        client, owner_headers, "shotsowner"
    )
    trade_id = await _create_trade(client, owner_headers, portfolio_id, account_id)

    response = await client.post(
        f"/api/v1/trades/{trade_id}/screenshots",
        files={"file": ("chart.png", b"fake-png", "image/png")},
        headers=other_headers,
    )
    assert response.status_code == 404, response.text
