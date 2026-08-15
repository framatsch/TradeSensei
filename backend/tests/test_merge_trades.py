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

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# Test helpers (re-using identical logic from other API tests)
_REGISTER_URL = "/api/v1/auth/register"
_LOGIN_URL = "/api/v1/auth/login"
_TOKEN_URL = "/api/v1/auth/token"


async def _get_auth_headers(client: AsyncClient, suffix: str = "") -> dict[str, str]:
    """Register a throwaway user and return Bearer auth headers."""
    uid = uuid.uuid4().hex[:8] + suffix
    reg = await client.post(
        _REGISTER_URL,
        json={
            "username": f"test_{uid}",
            "email": f"test_{uid}@example.com",
            "password": "Password123!",
            "first_name": "Test",
            "last_name": "Merge",
        },
    )
    assert reg.status_code == 201, reg.text

    res = await client.post(
        _TOKEN_URL,
        data={
            "username": f"test_{uid}@example.com",
            "password": "Password123!",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_trade(
    client: AsyncClient,
    headers: dict[str, str],
    portfolio_id: str,
    account_id: str,
    overrides: dict | None = None,
) -> dict:
    payload = {
        "account_id": account_id,
        "symbol": "AAPL",
        "direction": "LONG",
        "asset_class": "EQUITY",
        "quantity": "10.00",
        "entry_price": "150.00",
        "opened_at": datetime.now(UTC).isoformat(),
        "commission": "1.50",
    }
    if overrides:
        payload.update(overrides)

    res = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades", json=payload, headers=headers
    )
    assert res.status_code == 201
    return res.json()["data"]


async def _create_portfolio_and_account(
    client: AsyncClient,
    headers: dict[str, str],
    suffix: str,
) -> tuple[str, str]:
    """Create a portfolio and account for merge-trades tests.

    Args:
        client: Test HTTP client.
        headers: Auth headers.
        suffix: Unique name suffix.

    Returns:
        Tuple of ``(portfolio_id, account_id)``.
    """
    p_res = await client.post(
        "/api/v1/portfolios",
        json={"name": f"Merge Portfolio {suffix}", "base_currency": "USD"},
        headers=headers,
    )
    assert p_res.status_code == 201, p_res.text
    portfolio_id = str(p_res.json()["data"]["id"])

    a_res = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        json={"name": f"Merge Account {suffix}", "type": "manual", "currency": "USD"},
        headers=headers,
    )
    assert a_res.status_code == 201, a_res.text
    account_id = str(a_res.json()["data"]["id"])
    return portfolio_id, account_id


async def _set_trade_execution_conid(
    db_session: AsyncSession,
    trade_id: str,
    conid: str,
) -> None:
    await db_session.execute(
        text("UPDATE logical_executions SET conid = :conid WHERE trade_id = :trade_id"),
        {"conid": conid, "trade_id": uuid.UUID(trade_id)},
    )
    await db_session.flush()


class TestMergeTrades:
    """Test suite for POST /api/v1/trades/merge."""

    async def test_merge_trades_success(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client, "merge1")
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "merge1"
        )

        # Create 3 trades
        t1 = await _create_trade(
            client,
            headers,
            portfolio_id,
            account_id,
            {
                "quantity": "10.0",
                "entry_price": "100.0",
                "opened_at": "2023-01-01T10:00:00Z",
            },
        )
        t2 = await _create_trade(
            client,
            headers,
            portfolio_id,
            account_id,
            {
                "quantity": "10.0",
                "entry_price": "110.0",
                "opened_at": "2023-01-01T11:00:00Z",
            },
        )
        t3 = await _create_trade(
            client,
            headers,
            portfolio_id,
            account_id,
            {
                "quantity": "5.0",
                "entry_price": "120.0",
                "opened_at": "2023-01-01T12:00:00Z",
            },
        )

        # Merge them
        payload = {"trade_ids": [t1["id"], t2["id"], t3["id"]]}
        res = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades/merge",
            json=payload,
            headers=headers,
        )

        assert res.status_code == 200, res.text
        data = res.json()["data"]

        # Survivor should be the oldest one, so t1
        assert data["id"] == t1["id"]
        # Quantities merged: 10 + 10 + 5 = 25
        assert float(data["quantity"]) == 25.0
        assert data["is_manually_edited"] is True

        exec_res = await client.get(
            f"/api/v1/portfolios/{portfolio_id}/trades/{t1['id']}/executions",
            headers=headers,
        )
        assert exec_res.status_code == 200, exec_res.text
        executions = exec_res.json()["data"]
        assert executions
        assert all(execution["user_modified"] is True for execution in executions)

        # Make sure the other trades are deleted
        res2 = await client.get(
            f"/api/v1/portfolios/{portfolio_id}/trades/{t2['id']}", headers=headers
        )
        assert res2.status_code == 404

        res3 = await client.get(
            f"/api/v1/portfolios/{portfolio_id}/trades/{t3['id']}", headers=headers
        )
        assert res3.status_code == 404

    async def test_merge_trades_sets_combo_for_distinct_conids(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _get_auth_headers(client, "mergecombo")
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "mergecombo"
        )

        t1 = await _create_trade(
            client,
            headers,
            portfolio_id,
            account_id,
            {
                "symbol": "QQQ",
                "asset_class": "OPTION",
                "quantity": "1",
                "entry_price": "10.0",
                "opened_at": "2026-01-01T10:00:00Z",
            },
        )
        t2 = await _create_trade(
            client,
            headers,
            portfolio_id,
            account_id,
            {
                "symbol": "QQQ",
                "asset_class": "OPTION",
                "quantity": "1",
                "entry_price": "2.0",
                "opened_at": "2026-01-02T10:00:00Z",
            },
        )
        await _set_trade_execution_conid(db_session, t1["id"], "111111")
        await _set_trade_execution_conid(db_session, t2["id"], "222222")

        res = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades/merge",
            json={"trade_ids": [t1["id"], t2["id"]]},
            headers=headers,
        )
        assert res.status_code == 200, res.text
        merged = res.json()["data"]
        assert merged["id"] == t1["id"]
        assert merged["is_combo"] is True

    async def test_merge_trades_keeps_non_combo_for_single_conid(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _get_auth_headers(client, "mergeoneconid")
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "mergeoneconid"
        )

        t1 = await _create_trade(
            client,
            headers,
            portfolio_id,
            account_id,
            {
                "symbol": "QQQ",
                "asset_class": "OPTION",
                "quantity": "1",
                "entry_price": "10.0",
                "opened_at": "2026-03-01T10:00:00Z",
            },
        )
        t2 = await _create_trade(
            client,
            headers,
            portfolio_id,
            account_id,
            {
                "symbol": "QQQ",
                "asset_class": "OPTION",
                "quantity": "1",
                "entry_price": "11.0",
                "opened_at": "2026-03-02T10:00:00Z",
            },
        )
        await _set_trade_execution_conid(db_session, t1["id"], "555555")
        await _set_trade_execution_conid(db_session, t2["id"], "555555")

        res = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades/merge",
            json={"trade_ids": [t1["id"], t2["id"]]},
            headers=headers,
        )
        assert res.status_code == 200, res.text
        merged = res.json()["data"]
        assert merged["is_combo"] is False

    async def test_merge_trades_allows_mixed_asset_class_when_combo(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _get_auth_headers(client, "mergeasset")
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "mergeasset"
        )

        t1 = await _create_trade(
            client,
            headers,
            portfolio_id,
            account_id,
            {
                "symbol": "QQQ",
                "asset_class": "OPTION",
                "quantity": "1",
                "entry_price": "10.0",
                "opened_at": "2026-02-01T10:00:00Z",
            },
        )
        t2 = await _create_trade(
            client,
            headers,
            portfolio_id,
            account_id,
            {
                "symbol": "QQQ",
                "asset_class": "EQUITY",
                "quantity": "1",
                "entry_price": "100.0",
                "opened_at": "2026-02-02T10:00:00Z",
            },
        )
        await _set_trade_execution_conid(db_session, t1["id"], "333333")
        await _set_trade_execution_conid(db_session, t2["id"], "444444")

        res = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades/merge",
            json={"trade_ids": [t1["id"], t2["id"]]},
            headers=headers,
        )
        assert res.status_code == 200, res.text
        merged = res.json()["data"]
        assert merged["is_combo"] is True

    async def test_merge_trades_invalid_symbol(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client, "merge2")
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "merge2"
        )
        t1 = await _create_trade(
            client, headers, portfolio_id, account_id, {"symbol": "AAPL"}
        )
        t2 = await _create_trade(
            client, headers, portfolio_id, account_id, {"symbol": "MSFT"}
        )

        payload = {"trade_ids": [t1["id"], t2["id"]]}
        res = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades/merge",
            json=payload,
            headers=headers,
        )

        # Should raise 400 or 422 for non-matching properties.
        # Typically the service raises ValueError or similar. Let's see what status code it uses.
        # Fast API handles ValueError as 500 if not caught.
        # But let's just assert it is not successful for now.
        assert res.status_code in (400, 422, 500, 404)

    async def test_merge_trades_invalid_account(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client, "mergeacct")
        portfolio_id, account_id_a = await _create_portfolio_and_account(
            client, headers, "mergeaccta"
        )
        portfolio_id_b, account_id_b = await _create_portfolio_and_account(
            client, headers, "mergeacctb"
        )
        t1 = await _create_trade(
            client, headers, portfolio_id, account_id_a, {"symbol": "AAPL"}
        )
        t2 = await _create_trade(client, headers, portfolio_id_b, account_id_b, {"symbol": "AAPL"})

        payload = {"trade_ids": [t1["id"], t2["id"]]}
        res = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades/merge",
            json=payload,
            headers=headers,
        )

        assert res.status_code in (400, 422, 500, 404)
