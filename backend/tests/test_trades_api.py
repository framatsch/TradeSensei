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

"""Integration tests for the /api/v1/trades endpoints.

These tests require a live database (TimescaleDB with migrations applied).
They use the ``client`` fixture from ``conftest.py`` which overrides the
``get_session`` dependency with a rolled-back transaction.
"""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

_REGISTER_URL = "/api/v1/auth/register"
_TOKEN_URL = "/api/v1/auth/token"


async def _get_auth_headers(client: AsyncClient, suffix: str = "") -> dict[str, str]:
    """Register a throwaway user and return Bearer auth headers.

    Args:
        client: The HTTPX test client.
        suffix: Optional suffix to make the username unique across test classes.

    Returns:
        A dict with the ``Authorization: Bearer …`` header.
    """
    uid = uuid.uuid4().hex[:8] + suffix
    reg = await client.post(
        _REGISTER_URL,
        json={
            "username": f"trd_{uid}",
            "email": f"trd_{uid}@example.com",
            "password": "TradeTest@99",
        },
    )
    assert reg.status_code == 201, f"Register failed: {reg.text}"
    login = await client.post(
        _TOKEN_URL,
        data={"username": f"trd_{uid}", "password": "TradeTest@99"},
    )
    assert login.status_code == 200, f"Login failed: {login.text}"
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _trade_payload(**kwargs: object) -> dict[str, object]:
    """Build a minimal valid trade creation payload dict.

    Args:
        **kwargs: Field overrides.

    Returns:
        A dict suitable for posting to ``POST /api/v1/trades``.
    """
    defaults: dict[str, object] = {
        "symbol": "AAPL",
        "direction": "LONG",
        "asset_class": "EQUITY",
        "quantity": "10.00000000",
        "entry_price": "150.00000000",
        "opened_at": datetime(2025, 1, 15, 10, 0, tzinfo=UTC).isoformat(),
    }
    defaults.update(kwargs)
    return defaults


async def _create_portfolio_and_account(
    client: AsyncClient,
    headers: dict[str, str],
    suffix: str,
) -> tuple[str, str]:
    """Create a portfolio and account for the authenticated test user.

    Args:
        client: The HTTPX test client.
        headers: Bearer auth headers.
        suffix: Unique suffix for test resource names.

    Returns:
        Tuple of ``(portfolio_id, account_id)``.
    """
    portfolio_resp = await client.post(
        "/api/v1/portfolios",
        json={"name": f"Trades Portfolio {suffix}", "base_currency": "USD"},
        headers=headers,
    )
    assert portfolio_resp.status_code == 201, portfolio_resp.text
    portfolio_id = str(portfolio_resp.json()["data"]["id"])

    account_resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        json={"name": f"Trades Account {suffix}", "type": "manual", "currency": "USD"},
        headers=headers,
    )
    assert account_resp.status_code == 201, account_resp.text
    account_id = str(account_resp.json()["data"]["id"])
    return portfolio_id, account_id


@pytest.mark.integration
class TestHealthEndpoint:
    """Tests for the ``GET /health`` endpoint."""

    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        """Health endpoint should return 200 with status ok wrapped in envelope."""
        response = await client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["status"] == "ok"


@pytest.mark.integration
class TestCreateTrade:
    """Integration tests for ``POST /api/v1/trades``."""

    async def test_create_returns_201(self, client: AsyncClient) -> None:
        """Creating a valid trade should return HTTP 201."""
        headers = await _get_auth_headers(client, "create201")
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "create201"
        )
        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json=_trade_payload(account_id=account_id),
            headers=headers,
        )
        assert response.status_code == 201

    async def test_create_response_envelope(self, client: AsyncClient) -> None:
        """Response should be wrapped in the standard envelope."""
        headers = await _get_auth_headers(client, "createenv")
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "createenv"
        )
        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json=_trade_payload(account_id=account_id),
            headers=headers,
        )
        body = response.json()
        assert "data" in body
        assert body["data"]["symbol"] == "AAPL"
        assert body["data"]["direction"] == "LONG"

    async def test_create_missing_required_field(self, client: AsyncClient) -> None:
        """Missing a required field should return HTTP 422."""
        headers = await _get_auth_headers(client, "createmissing")
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "createmissing"
        )
        payload = _trade_payload()
        payload["account_id"] = account_id
        del payload["symbol"]  # type: ignore[attr-defined]
        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json=payload,
            headers=headers,
        )
        assert response.status_code == 422

    async def test_create_naive_datetime_rejected(self, client: AsyncClient) -> None:
        """A naive (no timezone) opened_at should return HTTP 422."""
        headers = await _get_auth_headers(client, "createnaive")
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "createnaive"
        )
        payload = _trade_payload(
            opened_at="2025-01-15T10:00:00", account_id=account_id
        )  # no tz
        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json=payload,
            headers=headers,
        )
        assert response.status_code == 422

    async def test_create_combo_trade_sets_null_vwap_fields(
        self, client: AsyncClient
    ) -> None:
        """Creating a COMBO trade should keep asset_class/quantity/prices null."""
        headers = await _get_auth_headers(client, "createcombo")
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "createcombo"
        )
        payload = {
            "account_id": account_id,
            "symbol": "AAPL",
            "direction": "LONG",
            "is_combo": True,
            "opened_at": datetime(2025, 1, 15, 10, 0, tzinfo=UTC).isoformat(),
        }
        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json=payload,
            headers=headers,
        )
        assert response.status_code == 201, response.text
        data = response.json()["data"]
        assert data["is_combo"] is True
        assert data["asset_class"] is None
        assert data["entry_price"] is None
        assert data["exit_price"] is None
        assert data["quantity"] is None


@pytest.mark.integration
class TestGetTrade:
    """Integration tests for ``GET /api/v1/trades/{trade_id}``."""

    async def test_get_existing_trade(self, client: AsyncClient) -> None:
        """Should return the trade when it exists."""
        headers = await _get_auth_headers(client, "getexist")
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "getexist"
        )
        create_resp = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json=_trade_payload(account_id=account_id),
            headers=headers,
        )
        trade_id = create_resp.json()["data"]["id"]

        response = await client.get(
            f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}", headers=headers
        )
        assert response.status_code == 200
        assert response.json()["data"]["id"] == trade_id

    async def test_get_nonexistent_trade_returns_404(self, client: AsyncClient) -> None:
        """Should return 404 for an unknown trade ID."""
        headers = await _get_auth_headers(client, "get404")
        portfolio_id, _ = await _create_portfolio_and_account(client, headers, "get404")
        response = await client.get(
            f"/api/v1/portfolios/{portfolio_id}/trades/{uuid.uuid4()}",
            headers=headers,
        )
        assert response.status_code == 404


@pytest.mark.integration
class TestListTrades:
    """Integration tests for ``GET /api/v1/trades``."""

    async def test_list_returns_envelope(self, client: AsyncClient) -> None:
        """Should return a CursorPage wrapped in a ResponseEnvelope."""
        headers = await _get_auth_headers(client, "listenv")
        portfolio_id, _ = await _create_portfolio_and_account(client, headers, "listenv")
        response = await client.get(
            f"/api/v1/portfolios/{portfolio_id}/trades", headers=headers
        )
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "items" in body["data"]
        assert "next_cursor" in body["data"]

    async def test_list_invalid_cursor_returns_400(self, client: AsyncClient) -> None:
        """An invalid cursor token should return HTTP 400."""
        headers = await _get_auth_headers(client, "listcursor")
        portfolio_id, _ = await _create_portfolio_and_account(
            client, headers, "listcursor"
        )
        response = await client.get(
            f"/api/v1/portfolios/{portfolio_id}/trades?cursor=INVALID_CURSOR!!!",
            headers=headers,
        )
        assert response.status_code == 400

    async def test_limit_out_of_range_returns_422(self, client: AsyncClient) -> None:
        """A limit > 100 should return HTTP 422."""
        headers = await _get_auth_headers(client, "listlimit")
        portfolio_id, _ = await _create_portfolio_and_account(
            client, headers, "listlimit"
        )
        response = await client.get(
            f"/api/v1/portfolios/{portfolio_id}/trades?limit=999", headers=headers
        )
        assert response.status_code == 422


@pytest.mark.integration
class TestUpdateTrade:
    """Integration tests for ``PATCH /api/v1/trades/{trade_id}``."""

    async def test_patch_updates_field(self, client: AsyncClient) -> None:
        """PATCH should update only the supplied field."""
        headers = await _get_auth_headers(client, "patchupd")
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "patchupd"
        )
        create_resp = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json=_trade_payload(account_id=account_id),
            headers=headers,
        )
        trade_id = create_resp.json()["data"]["id"]

        response = await client.patch(
            f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}",
            json={"journal": "Updated note"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["data"]["journal"] == "Updated note"

    async def test_patch_nonexistent_returns_404(self, client: AsyncClient) -> None:
        """PATCH on a non-existent trade should return 404."""
        headers = await _get_auth_headers(client, "patch404")
        portfolio_id, _ = await _create_portfolio_and_account(client, headers, "patch404")
        response = await client.patch(
            f"/api/v1/portfolios/{portfolio_id}/trades/{uuid.uuid4()}",
            json={"journal": "x"},
            headers=headers,
        )
        assert response.status_code == 404

    async def test_patch_is_combo_is_ignored(self, client: AsyncClient) -> None:
        """PATCH must not toggle is_combo once trade is created."""
        headers = await _get_auth_headers(client, "patchcombo")
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "patchcombo"
        )
        create_resp = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json={
                "account_id": account_id,
                "symbol": "AAPL",
                "direction": "LONG",
                "is_combo": True,
                "opened_at": datetime(2025, 1, 15, 10, 0, tzinfo=UTC).isoformat(),
            },
            headers=headers,
        )
        assert create_resp.status_code == 201, create_resp.text
        trade_id = create_resp.json()["data"]["id"]

        patch_resp = await client.patch(
            f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}",
            json={"is_combo": False, "journal": "still combo"},
            headers=headers,
        )
        assert patch_resp.status_code == 200, patch_resp.text
        assert patch_resp.json()["data"]["is_combo"] is True

    async def test_patch_user_rating_field(self, client: AsyncClient) -> None:
        """PATCH should accept user_rating updates."""
        headers = await _get_auth_headers(client, "patchrating")
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "patchrating"
        )
        create_resp = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json=_trade_payload(account_id=account_id),
            headers=headers,
        )
        trade_id = create_resp.json()["data"]["id"]

        response = await client.patch(
            f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}",
            json={"user_rating": 5},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["data"]["user_rating"] == 5


@pytest.mark.integration
class TestDeleteTrade:
    """Integration tests for ``DELETE /api/v1/trades/{trade_id}``."""

    async def test_delete_returns_204(self, client: AsyncClient) -> None:
        """DELETE should return 204 No Content."""
        headers = await _get_auth_headers(client, "del204")
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "del204"
        )
        create_resp = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json=_trade_payload(account_id=account_id),
            headers=headers,
        )
        trade_id = create_resp.json()["data"]["id"]

        response = await client.delete(
            f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}", headers=headers
        )
        assert response.status_code == 204

    async def test_delete_then_get_returns_404(self, client: AsyncClient) -> None:
        """After deletion, GET should return 404."""
        headers = await _get_auth_headers(client, "delget")
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "delget"
        )
        create_resp = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json=_trade_payload(account_id=account_id),
            headers=headers,
        )
        trade_id = create_resp.json()["data"]["id"]

        await client.delete(
            f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}", headers=headers
        )
        response = await client.get(
            f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}", headers=headers
        )
        assert response.status_code == 404

    async def test_delete_nonexistent_returns_404(self, client: AsyncClient) -> None:
        """DELETE on a non-existent trade should return 404."""
        headers = await _get_auth_headers(client, "del404")
        portfolio_id, _ = await _create_portfolio_and_account(client, headers, "del404")
        response = await client.delete(
            f"/api/v1/portfolios/{portfolio_id}/trades/{uuid.uuid4()}",
            headers=headers,
        )
        assert response.status_code == 404


# TestHasConflictFilter removed: has_conflict field was removed in the
# simplified-execution-model spec (task 5.5). The ?has_conflict filter
# query parameter no longer exists on the trades list endpoint.
