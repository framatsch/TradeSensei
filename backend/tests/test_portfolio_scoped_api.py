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

"""Integration tests for portfolio-scoped isolation and imports."""

import uuid

import pytest
from httpx import AsyncClient

_REGISTER_URL = "/api/v1/auth/register"
_TOKEN_URL = "/api/v1/auth/token"
_PORTFOLIOS_URL = "/api/v1/portfolios"


async def _auth_headers(client: AsyncClient, prefix: str) -> dict[str, str]:
    suffix = uuid.uuid4().hex[:8]
    username = f"{prefix}_{suffix}"
    email = f"{prefix}_{suffix}@example.com"
    password = "PortfolioScopeP@ss99"

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


async def _create_portfolio(
    client: AsyncClient,
    headers: dict[str, str],
    name: str,
    base_currency: str = "USD",
) -> str:
    resp = await client.post(
        _PORTFOLIOS_URL,
        headers=headers,
        json={"name": name, "base_currency": base_currency},
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["data"]["id"])


async def _create_account(
    client: AsyncClient,
    headers: dict[str, str],
    portfolio_id: str,
    name: str,
    account_type: str = "manual",
    currency: str = "USD",
) -> str:
    resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        headers=headers,
        json={"name": name, "type": account_type, "currency": currency},
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["data"]["id"])


async def _create_closed_trade(
    client: AsyncClient,
    headers: dict[str, str],
    portfolio_id: str,
    account_id: str,
    symbol: str,
    pnl: str,
) -> str:
    payload = {
        "account_id": account_id,
        "symbol": symbol,
        "direction": "LONG",
        "asset_class": "EQUITY",
        "quantity": "1",
        "entry_price": "10",
        "exit_price": "12",
        "opened_at": "2024-01-01T10:00:00Z",
        "closed_at": "2024-01-02T10:00:00Z",
        "pnl": pnl,
        "commission": "0",
        "currency": "USD",
    }
    resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers=headers,
        json=payload,
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["data"]["id"])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_trade_endpoints_are_isolated_by_portfolio(client: AsyncClient) -> None:
    headers = await _auth_headers(client, "scope_trade")
    p1 = _create_portfolio(client, headers, "P1")
    p2 = _create_portfolio(client, headers, "P2")
    portfolio_1, portfolio_2 = await p1, await p2

    account_1 = await _create_account(client, headers, portfolio_1, "Acc1")
    account_2 = await _create_account(client, headers, portfolio_2, "Acc2")

    _ = account_1
    trade_id = await _create_closed_trade(
        client,
        headers,
        portfolio_2,
        account_2,
        "TSLA",
        "2",
    )

    wrong_scope = await client.get(
        f"/api/v1/portfolios/{portfolio_1}/trades/{trade_id}",
        headers=headers,
    )
    assert wrong_scope.status_code == 404, wrong_scope.text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_metrics_and_timeseries_do_not_leak_across_portfolios(
    client: AsyncClient,
) -> None:
    headers = await _auth_headers(client, "scope_metrics")
    portfolio_1 = await _create_portfolio(client, headers, "Stats A")
    portfolio_2 = await _create_portfolio(client, headers, "Stats B")

    account_1 = await _create_account(client, headers, portfolio_1, "Stats A acc")
    account_2 = await _create_account(client, headers, portfolio_2, "Stats B acc")

    await _create_closed_trade(client, headers, portfolio_1, account_1, "AAPL", "10")
    await _create_closed_trade(client, headers, portfolio_2, account_2, "MSFT", "20")

    summary_1 = await client.get(
        f"/api/v1/portfolios/{portfolio_1}/metrics/summary",
        headers=headers,
    )
    assert summary_1.status_code == 200, summary_1.text
    assert summary_1.json()["data"]["metrics"]["total_trades"] == 1
    assert summary_1.json()["data"]["metrics"]["total_pnl"] == "10.00000000"

    summary_2 = await client.get(
        f"/api/v1/portfolios/{portfolio_2}/metrics/summary",
        headers=headers,
    )
    assert summary_2.status_code == 200, summary_2.text
    assert summary_2.json()["data"]["metrics"]["total_trades"] == 1
    assert summary_2.json()["data"]["metrics"]["total_pnl"] == "20.00000000"

    daily_1 = await client.get(
        f"/api/v1/portfolios/{portfolio_1}/timeseries/daily-pnl",
        headers=headers,
    )
    assert daily_1.status_code == 200, daily_1.text
    assert len(daily_1.json()["data"]) == 1
    assert daily_1.json()["data"][0]["pnl"] == "10.00000000"

    account_scope_error = await client.get(
        f"/api/v1/portfolios/{portfolio_1}/metrics/summary",
        headers=headers,
        params={"account_id": account_2},
    )
    assert account_scope_error.status_code == 400, account_scope_error.text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_import_reports_currency_mismatch_warning(client: AsyncClient) -> None:
    headers = await _auth_headers(client, "scope_import")
    portfolio_id = await _create_portfolio(client, headers, "EUR Portfolio", "EUR")
    account_id = await _create_account(
        client,
        headers,
        portfolio_id,
        "Schwab EUR",
        account_type="schwab",
        currency="USD",
    )

    schwab_payload = {
        "fetchedAt": "2024-01-03T10:00:00.000Z",
        "dateRange": {
            "start": "2024-01-01T00:00:00.000Z",
            "end": "2024-01-03T00:00:00.000Z",
        },
        "accounts": [
            {
                "accountNumber": "12345678",
                "transactions": [
                    {
                        "activityId": "T1",
                        "type": "TRADE",
                        "status": "COMPLETED",
                        "time": "2024-01-01T10:00:00+0000",
                        "transferItems": [
                            {
                                "instrument": {"symbol": "AAPL", "assetType": "EQUITY"},
                                "instruction": "BUY",
                                "price": 100,
                                "amount": 1,
                            }
                        ],
                    },
                    {
                        "activityId": "T2",
                        "type": "TRADE",
                        "status": "COMPLETED",
                        "time": "2024-01-02T10:00:00+0000",
                        "transferItems": [
                            {
                                "instrument": {"symbol": "AAPL", "assetType": "EQUITY"},
                                "instruction": "SELL",
                                "price": 110,
                                "amount": 1,
                            }
                        ],
                    },
                ],
            }
        ],
    }

    resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/imports/schwab-json",
        headers=headers,
        params={"account_id": account_id},
        json=schwab_payload,
    )
    assert resp.status_code == 200, resp.text
    warnings = resp.json()["data"]["warnings"]
    assert any("currency_mismatch" in warning for warning in warnings)
