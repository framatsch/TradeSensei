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

"""Integration tests for closing/partial closing a trade via Executions."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient

from tests.test_trades_api import _get_auth_headers, _trade_payload


async def _create_portfolio_and_account(
    client: AsyncClient,
    headers: dict[str, str],
    suffix: str,
) -> tuple[str, str]:
    """Create a portfolio and account for execution close tests.

    Args:
        client: The HTTPX test client.
        headers: Auth headers.
        suffix: Unique suffix for names.

    Returns:
        Tuple of ``(portfolio_id, account_id)``.
    """
    p_resp = await client.post(
        "/api/v1/portfolios",
        json={"name": f"Execution Close {suffix}", "base_currency": "USD"},
        headers=headers,
    )
    assert p_resp.status_code == 201, p_resp.text
    portfolio_id = str(p_resp.json()["data"]["id"])

    a_resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        json={"name": f"Execution Close {suffix}", "type": "manual", "currency": "USD"},
        headers=headers,
    )
    assert a_resp.status_code == 201, a_resp.text
    account_id = str(a_resp.json()["data"]["id"])
    return portfolio_id, account_id


@pytest.mark.integration
class TestExecutionCloseTrade:
    """Integration tests for closing a trade via ``POST /api/v1/trades/{trade_id}/executions``."""

    async def test_adding_sell_execution_to_long_trade(
        self, client: AsyncClient
    ) -> None:
        """Adding a SELL execution to an open LONG trade correctly aggregates values but keeps it open if partial."""
        headers = await _get_auth_headers(client, "pcsplit")
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "pcsplit"
        )

        # 1. Create an open LONG trade (10 shares)
        payload = _trade_payload(
            quantity="10",
            commission="10.00",
            direction="LONG",
            account_id=account_id,
        )
        create_resp = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades", json=payload, headers=headers
        )
        trade_id = create_resp.json()["data"]["id"]

        # 2. Add a SELL execution for 4 shares
        execution_payload = {
            "direction": "SHORT",
            "quantity": "4",
            "price": "160.00",
            "commission": "2.50",
            "executed_at": datetime(2025, 1, 15, 15, 0, tzinfo=UTC).isoformat(),
        }
        exec_resp = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}/executions",
            json=execution_payload,
            headers=headers,
        )
        assert exec_resp.status_code == 201

        # 3. Verify original trade was re-aggregated
        trade_resp = await client.get(
            f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}", headers=headers
        )
        trade = trade_resp.json()["data"]

        # Qty remains 10 (entry sum). Commission is 10.00 (entry) + 2.50 (exit) = 12.50
        assert Decimal(trade["quantity"]) == Decimal("10")
        assert Decimal(trade["commission"]) == Decimal("12.50")
        assert trade["closed_at"] is None  # Still open
        assert Decimal(trade["exit_price"]) == Decimal("160.00")

    async def test_adding_full_quantity_sell_closes_trade(
        self, client: AsyncClient
    ) -> None:
        """If exit quantity matches entry quantity, the trade should be fully closed."""
        headers = await _get_auth_headers(client, "pcfull")
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "pcfull"
        )

        # 1. Create an open LONG trade (10 shares)
        payload = _trade_payload(
            quantity="10",
            commission="5.00",
            direction="LONG",
            account_id=account_id,
        )
        create_resp = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades", json=payload, headers=headers
        )
        trade_id = create_resp.json()["data"]["id"]

        # 2. Add a SELL execution for 10 shares
        execution_payload = {
            "direction": "SHORT",
            "quantity": "10",
            "price": "170.00",
            "commission": "1.00",
            "executed_at": datetime(2025, 1, 15, 16, 0, tzinfo=UTC).isoformat(),
        }
        exec_resp = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}/executions",
            json=execution_payload,
            headers=headers,
        )
        assert exec_resp.status_code == 201

        # 3. Verify trade is closed
        trade_resp = await client.get(
            f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}", headers=headers
        )
        trade = trade_resp.json()["data"]

        assert Decimal(trade["quantity"]) == Decimal("10")
        assert Decimal(trade["commission"]) == Decimal("6.00")  # 5 + 1
        assert trade["closed_at"] is not None
        assert Decimal(trade["exit_price"]) == Decimal("170.00")

    async def test_invalid_execution_quantity_returns_422(
        self, client: AsyncClient
    ) -> None:
        """Should return 422 if execution payload is invalid (e.g. qty=0)."""
        headers = await _get_auth_headers(client, "pcinv")
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "pcinv"
        )

        # 1. Create an open LONG trade (5 shares)
        payload = _trade_payload(quantity="5", direction="LONG", account_id=account_id)
        create_resp = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades", json=payload, headers=headers
        )
        trade_id = create_resp.json()["data"]["id"]

        # 2. Attempt to add invalid execution
        execution_payload = {
            "direction": "SHORT",
            "quantity": "0",  # Invalid
            "price": "100.00",
            "commission": "0",
            "executed_at": datetime.now(UTC).isoformat(),
        }
        exec_resp = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}/executions",
            json=execution_payload,
            headers=headers,
        )
        assert exec_resp.status_code == 422
