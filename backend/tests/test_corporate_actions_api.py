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

"""Integration tests for the /api/v1/corporate-actions endpoints.

Exercises the full HTTP → service → repository → DB round-trip using the
savepoint-backed ``client`` fixture from ``conftest.py``.  Each test class
registers its own throwaway user so that ownership isolation assertions are
unambiguous.

Requires a live TimescaleDB instance (migrations applied via ``conftest.py``).
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.ohlc_price import OhlcPrice

_REGISTER_URL = "/api/v1/auth/register"
_TOKEN_URL = "/api/v1/auth/token"
_BASE_URL = "/api/v1/corporate-actions"

# ── Auth helper ────────────────────────────────────────────────────────────────


async def _get_auth_headers(
    client: AsyncClient,
    suffix: str = "",
) -> dict[str, str]:
    """Register a throwaway user and return Bearer auth headers.

    Args:
        client: The HTTPX test client.
        suffix: Optional suffix to make the username unique across test classes.

    Returns:
        A dict containing the ``Authorization: Bearer <token>`` header.
    """
    uid = uuid.uuid4().hex[:8] + suffix
    reg = await client.post(
        _REGISTER_URL,
        json={
            "username": f"ca_{uid}",
            "email": f"ca_{uid}@example.com",
            "password": "CorpAct@99",
        },
    )
    assert reg.status_code == 201, f"Register failed: {reg.text}"
    login = await client.post(
        _TOKEN_URL,
        data={"username": f"ca_{uid}", "password": "CorpAct@99"},
    )
    assert login.status_code == 200, f"Login failed: {login.text}"
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Shared payload helpers ─────────────────────────────────────────────────────

_VALID_PAYLOAD: dict[str, object] = {
    "symbol": "OTLK",
    "date": "2023-05-01",
    "ratio": "0.05",
    "old_conid": "357194941",
    "new_conid": "690184975",
}

_UPDATE_PAYLOAD: dict[str, object] = {"ratio": "2.0"}


async def _create_portfolio_id(client: AsyncClient, headers: dict[str, str], suffix: str) -> str:
    response = await client.post(
        "/api/v1/portfolios",
        headers=headers,
        json={"name": f"CA Portfolio {suffix}", "base_currency": "USD"},
    )
    assert response.status_code == 201, response.text
    return str(response.json()["data"]["id"])


async def _create_account_id(client: AsyncClient, headers: dict[str, str], portfolio_id: str, suffix: str) -> str:
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        headers=headers,
        json={"name": f"CA Account {suffix}", "type": "manual", "currency": "USD"},
    )
    assert response.status_code == 201, response.text
    return str(response.json()["data"]["id"])


async def _create_closed_trade(
    client: AsyncClient,
    headers: dict[str, str],
    portfolio_id: str,
    account_id: str,
    *,
    symbol: str,
) -> str:
    trade_response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers=headers,
        json={
            "symbol": symbol,
            "direction": "LONG",
            "asset_class": "EQUITY",
            "quantity": "69",
            "entry_price": "1.44",
            "opened_at": datetime(2023, 5, 22, 14, 0, tzinfo=UTC).isoformat(),
            "commission": "1.00",
            "account_id": account_id,
        },
    )
    assert trade_response.status_code == 201, trade_response.text
    trade_id = str(trade_response.json()["data"]["id"])

    close_response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}/executions",
        headers=headers,
        json={
            "direction": "SHORT",
            "quantity": "69",
            "price": "1.50",
            "commission": "0.50",
            "executed_at": datetime(2023, 5, 24, 14, 0, tzinfo=UTC).isoformat(),
        },
    )
    assert close_response.status_code == 201, close_response.text
    return trade_id


# ── TestListCorporateActions ───────────────────────────────────────────────────


@pytest.mark.integration
class TestListCorporateActions:
    """Integration tests for GET /api/v1/corporate-actions."""

    async def test_returns_401_without_auth(self, client: AsyncClient) -> None:
        """A request without a token must be rejected with 401."""
        resp = await client.get(_BASE_URL)
        assert resp.status_code == 401, (
            f"Expected 401, got {resp.status_code}: {resp.text}"
        )

    async def test_returns_empty_list_for_new_user(self, client: AsyncClient) -> None:
        """A freshly registered user should see an empty corporate-actions list."""
        headers = await _get_auth_headers(client, "list_empty")
        resp = await client.get(_BASE_URL, headers=headers)
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}: {resp.text}"
        )
        assert resp.json()["data"] == []

    async def test_returns_created_items_in_list(self, client: AsyncClient) -> None:
        """Corporate actions created by the user must appear in the list response."""
        headers = await _get_auth_headers(client, "list_items")
        # Create two actions
        for symbol in ("OTLK", "AAPL"):
            payload = {**_VALID_PAYLOAD, "symbol": symbol}
            create_resp = await client.post(_BASE_URL, json=payload, headers=headers)
            assert create_resp.status_code == 201, (
                f"Create failed for {symbol}: {create_resp.text}"
            )

        resp = await client.get(_BASE_URL, headers=headers)
        assert resp.status_code == 200
        items = resp.json()["data"]
        assert len(items) == 2
        symbols = {item["symbol"] for item in items}
        assert symbols == {"OTLK", "AAPL"}


# ── TestCreateCorporateAction ──────────────────────────────────────────────────


@pytest.mark.integration
class TestCreateCorporateAction:
    """Integration tests for POST /api/v1/corporate-actions."""

    async def test_returns_401_without_auth(self, client: AsyncClient) -> None:
        """A create request without a token must be rejected with 401."""
        resp = await client.post(_BASE_URL, json=_VALID_PAYLOAD)
        assert resp.status_code == 401, (
            f"Expected 401, got {resp.status_code}: {resp.text}"
        )

    async def test_returns_201_with_valid_payload(self, client: AsyncClient) -> None:
        """A valid create request must return 201 Created."""
        headers = await _get_auth_headers(client, "create_201")
        resp = await client.post(_BASE_URL, json=_VALID_PAYLOAD, headers=headers)
        assert resp.status_code == 201, (
            f"Expected 201, got {resp.status_code}: {resp.text}"
        )

    async def test_response_fields_match_payload(self, client: AsyncClient) -> None:
        """The created record's fields in the response must match the
        submitted payload."""
        headers = await _get_auth_headers(client, "create_fields")
        resp = await client.post(_BASE_URL, json=_VALID_PAYLOAD, headers=headers)
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["symbol"] == "OTLK"
        assert data["date"] == "2023-05-01"
        assert data["old_conid"] == "357194941"
        assert data["new_conid"] == "690184975"
        # ratio is a Decimal; compare string representation via float
        assert float(data["ratio"]) == pytest.approx(0.05)

    async def test_response_contains_id_and_user_id(self, client: AsyncClient) -> None:
        """The created record must include database-generated ``id`` and
        ``user_id`` fields."""
        headers = await _get_auth_headers(client, "create_ids")
        resp = await client.post(_BASE_URL, json=_VALID_PAYLOAD, headers=headers)
        assert resp.status_code == 201
        data = resp.json()["data"]
        # Both fields must be parseable UUIDs
        uuid.UUID(data["id"])
        uuid.UUID(data["user_id"])

    async def test_returns_422_for_negative_ratio(self, client: AsyncClient) -> None:
        """A negative ratio must be rejected with a 422 validation error."""
        headers = await _get_auth_headers(client, "create_neg_ratio")
        bad_payload = {**_VALID_PAYLOAD, "ratio": "-0.05"}
        resp = await client.post(_BASE_URL, json=bad_payload, headers=headers)
        assert resp.status_code == 422, (
            f"Expected 422 for negative ratio, got {resp.status_code}: {resp.text}"
        )

    async def test_returns_422_for_missing_symbol(self, client: AsyncClient) -> None:
        """A payload without ``symbol`` must be rejected with 422."""
        headers = await _get_auth_headers(client, "create_no_sym")
        bad_payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "symbol"}
        resp = await client.post(_BASE_URL, json=bad_payload, headers=headers)
        assert resp.status_code == 422, (
            f"Expected 422 for missing symbol, got {resp.status_code}: {resp.text}"
        )

    async def test_optional_conid_fields_accept_null(self, client: AsyncClient) -> None:
        """Creating a corporate action without conid fields should succeed."""
        headers = await _get_auth_headers(client, "create_no_conid")
        payload = {"symbol": "AAPL", "date": "2024-01-15", "ratio": "2.0"}
        resp = await client.post(_BASE_URL, json=payload, headers=headers)
        assert resp.status_code == 201, (
            f"Expected 201, got {resp.status_code}: {resp.text}"
        )
        data = resp.json()["data"]
        assert data["old_conid"] is None
        assert data["new_conid"] is None

    async def test_duplicate_manual_create_returns_conflict(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client, "create_duplicate")
        first = await client.post(_BASE_URL, json=_VALID_PAYLOAD, headers=headers)
        assert first.status_code == 201

        second = await client.post(_BASE_URL, json=_VALID_PAYLOAD, headers=headers)
        assert second.status_code == 409
        detail = second.json().get("detail", {})
        assert isinstance(detail, dict)
        assert "existing_action_id" in detail


# ── TestUpdateCorporateAction ──────────────────────────────────────────────────


@pytest.mark.integration
class TestUpdateCorporateAction:
    """Integration tests for PUT /api/v1/corporate-actions/{id}."""

    async def _create_action(self, client: AsyncClient, headers: dict[str, str]) -> str:
        """Create a corporate action and return its UUID string.

        Args:
            client: The HTTPX test client.
            headers: Auth headers for the authenticated user.

        Returns:
            The UUID string of the created corporate action.
        """
        resp = await client.post(_BASE_URL, json=_VALID_PAYLOAD, headers=headers)
        assert resp.status_code == 201, f"Create failed: {resp.text}"
        return str(resp.json()["data"]["id"])

    async def test_returns_200_with_updated_fields(self, client: AsyncClient) -> None:
        """A valid PUT request must return 200 with the updated fields reflected."""
        headers = await _get_auth_headers(client, "update_ok")
        action_id = await self._create_action(client, headers)

        resp = await client.put(
            f"{_BASE_URL}/{action_id}",
            json=_UPDATE_PAYLOAD,
            headers=headers,
        )
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}: {resp.text}"
        )
        data = resp.json()["data"]
        assert float(data["ratio"]) == pytest.approx(2.0)

    async def test_returns_404_for_nonexistent_id(self, client: AsyncClient) -> None:
        """A PUT request for an unknown UUID must return 404."""
        headers = await _get_auth_headers(client, "update_404")
        nonexistent_id = str(uuid.uuid4())
        resp = await client.put(
            f"{_BASE_URL}/{nonexistent_id}",
            json=_UPDATE_PAYLOAD,
            headers=headers,
        )
        assert resp.status_code == 404, (
            f"Expected 404 for unknown id, got {resp.status_code}: {resp.text}"
        )

    async def test_user_cannot_update_another_users_record(
        self, client: AsyncClient
    ) -> None:
        """A user must not be able to update a corporate action owned by another user.

        The service scopes every DB look-up by ``user_id``, so the record simply
        will not be found for the second user — which is surfaced as a 404.
        """
        headers_a = await _get_auth_headers(client, "update_cross_a")
        headers_b = await _get_auth_headers(client, "update_cross_b")

        # User A creates a corporate action
        action_id = await self._create_action(client, headers_a)

        # User B attempts to update User A's record
        resp = await client.put(
            f"{_BASE_URL}/{action_id}",
            json=_UPDATE_PAYLOAD,
            headers=headers_b,
        )
        assert resp.status_code == 404, (
            f"Expected 404 when user B updates user A's record, "
            f"got {resp.status_code}: {resp.text}"
        )

    async def test_returns_401_without_auth(self, client: AsyncClient) -> None:
        """A PUT request without a token must be rejected with 401."""
        nonexistent_id = str(uuid.uuid4())
        resp = await client.put(
            f"{_BASE_URL}/{nonexistent_id}",
            json=_UPDATE_PAYLOAD,
        )
        assert resp.status_code == 401, (
            f"Expected 401, got {resp.status_code}: {resp.text}"
        )


# ── TestDeleteCorporateAction ──────────────────────────────────────────────────


@pytest.mark.integration
class TestDeleteCorporateAction:
    """Integration tests for DELETE /api/v1/corporate-actions/{id}."""

    async def _create_action(self, client: AsyncClient, headers: dict[str, str]) -> str:
        """Create a corporate action and return its UUID string.

        Args:
            client: The HTTPX test client.
            headers: Auth headers for the authenticated user.

        Returns:
            The UUID string of the created corporate action.
        """
        resp = await client.post(_BASE_URL, json=_VALID_PAYLOAD, headers=headers)
        assert resp.status_code == 201, f"Create failed: {resp.text}"
        return str(resp.json()["data"]["id"])

    async def test_returns_204_on_success(self, client: AsyncClient) -> None:
        """A valid DELETE request must return 204 No Content."""
        headers = await _get_auth_headers(client, "delete_ok")
        action_id = await self._create_action(client, headers)

        resp = await client.delete(f"{_BASE_URL}/{action_id}", headers=headers)
        assert resp.status_code == 204, (
            f"Expected 204, got {resp.status_code}: {resp.text}"
        )

    async def test_deleted_record_no_longer_appears_in_list(
        self, client: AsyncClient
    ) -> None:
        """After deletion, the record must no longer appear in the list response."""
        headers = await _get_auth_headers(client, "delete_gone")
        action_id = await self._create_action(client, headers)

        await client.delete(f"{_BASE_URL}/{action_id}", headers=headers)

        list_resp = await client.get(_BASE_URL, headers=headers)
        assert list_resp.status_code == 200
        ids = [item["id"] for item in list_resp.json()["data"]]
        assert action_id not in ids

    async def test_returns_404_for_nonexistent_id(self, client: AsyncClient) -> None:
        """A DELETE request for an unknown UUID must return 404."""
        headers = await _get_auth_headers(client, "delete_404")
        nonexistent_id = str(uuid.uuid4())
        resp = await client.delete(f"{_BASE_URL}/{nonexistent_id}", headers=headers)
        assert resp.status_code == 404, (
            f"Expected 404 for unknown id, got {resp.status_code}: {resp.text}"
        )

    async def test_returns_401_without_auth(self, client: AsyncClient) -> None:
        """A DELETE request without a token must be rejected with 401."""
        nonexistent_id = str(uuid.uuid4())
        resp = await client.delete(f"{_BASE_URL}/{nonexistent_id}")
        assert resp.status_code == 401, (
            f"Expected 401, got {resp.status_code}: {resp.text}"
        )


@pytest.mark.integration
class TestCorporateActionLifecycleEffects:
    async def test_create_update_delete_leave_pre_split_closed_trade_untouched(
        self,
        client: AsyncClient,
    ) -> None:
        headers = await _get_auth_headers(client, "lifecycle_closed_trade")
        portfolio_id = await _create_portfolio_id(client, headers, "lifecycle_closed_trade")
        account_id = await _create_account_id(client, headers, portfolio_id, "lifecycle_closed_trade")
        trade_id = await _create_closed_trade(
            client,
            headers,
            portfolio_id,
            account_id,
            symbol="OTLK",
        )

        before = await client.get(f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}", headers=headers)
        assert before.status_code == 200, before.text
        before_data = before.json()["data"]

        create_resp = await client.post(
            _BASE_URL,
            json={
                "symbol": "OTLK",
                "date": "2024-03-13",
                "ratio": "0.05",
                "old_conid": "357194941",
                "new_conid": "690184975",
            },
            headers=headers,
        )
        assert create_resp.status_code == 201, create_resp.text
        action_id = str(create_resp.json()["data"]["id"])

        update_resp = await client.put(
            f"{_BASE_URL}/{action_id}",
            json={"date": "2024-03-20", "ratio": "0.05"},
            headers=headers,
        )
        assert update_resp.status_code == 200, update_resp.text

        delete_resp = await client.delete(f"{_BASE_URL}/{action_id}", headers=headers)
        assert delete_resp.status_code == 204, delete_resp.text

        after = await client.get(f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}", headers=headers)
        assert after.status_code == 200, after.text
        after_data = after.json()["data"]

        assert Decimal(after_data["quantity"]) == Decimal(before_data["quantity"])
        assert Decimal(after_data["entry_price"]) == Decimal(before_data["entry_price"])
        assert Decimal(after_data["exit_price"]) == Decimal(before_data["exit_price"])
        assert Decimal(after_data["commission"]) == Decimal(before_data["commission"])
        assert Decimal(after_data["pnl"]) == Decimal(before_data["pnl"])
        assert Decimal(after_data["net_pnl"]) == Decimal(before_data["net_pnl"])

    async def test_corporate_action_crud_invalidates_symbol_cache_rows(
        self,
        client: AsyncClient,
        db_session,
    ) -> None:
        headers = await _get_auth_headers(client, "cache_invalidation")
        symbol = "CACHECA"

        async def _insert_cache_row(start_iso: str) -> None:
            db_session.add(
                OhlcPrice(
                    symbol=symbol,
                    interval="1d",
                    provider="lseg",
                    start=datetime.fromisoformat(start_iso),
                    open=Decimal("10"),
                    high=Decimal("11"),
                    low=Decimal("9"),
                    close=Decimal("10.5"),
                    volume=Decimal("1000"),
                )
            )
            await db_session.flush()

        async def _count_cache_rows() -> int:
            result = await db_session.execute(select(OhlcPrice).where(OhlcPrice.symbol == symbol))
            return len(result.scalars().all())

        await _insert_cache_row("2024-01-02T00:00:00+00:00")
        assert await _count_cache_rows() == 1

        create_resp = await client.post(
            _BASE_URL,
            json={"symbol": symbol, "date": "2024-03-13", "ratio": "0.5"},
            headers=headers,
        )
        assert create_resp.status_code == 201, create_resp.text
        action_id = str(create_resp.json()["data"]["id"])
        assert await _count_cache_rows() == 0

        await _insert_cache_row("2024-01-03T00:00:00+00:00")
        assert await _count_cache_rows() == 1

        update_resp = await client.put(
            f"{_BASE_URL}/{action_id}",
            json={"date": "2024-03-14"},
            headers=headers,
        )
        assert update_resp.status_code == 200, update_resp.text
        assert await _count_cache_rows() == 0

        await _insert_cache_row("2024-01-04T00:00:00+00:00")
        assert await _count_cache_rows() == 1

        delete_resp = await client.delete(f"{_BASE_URL}/{action_id}", headers=headers)
        assert delete_resp.status_code == 204, delete_resp.text
        assert await _count_cache_rows() == 0
