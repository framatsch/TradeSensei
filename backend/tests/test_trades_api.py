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
_TRADES_URL = "/api/v1/trades"


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
        response = await client.post(
            "/api/v1/trades", json=_trade_payload(), headers=headers
        )
        assert response.status_code == 201

    async def test_create_response_envelope(self, client: AsyncClient) -> None:
        """Response should be wrapped in the standard envelope."""
        headers = await _get_auth_headers(client, "createenv")
        response = await client.post(
            "/api/v1/trades", json=_trade_payload(), headers=headers
        )
        body = response.json()
        assert "data" in body
        assert body["data"]["symbol"] == "AAPL"
        assert body["data"]["direction"] == "LONG"

    async def test_create_missing_required_field(self, client: AsyncClient) -> None:
        """Missing a required field should return HTTP 422."""
        headers = await _get_auth_headers(client, "createmissing")
        payload = _trade_payload()
        del payload["symbol"]  # type: ignore[attr-defined]
        response = await client.post("/api/v1/trades", json=payload, headers=headers)
        assert response.status_code == 422

    async def test_create_naive_datetime_rejected(self, client: AsyncClient) -> None:
        """A naive (no timezone) opened_at should return HTTP 422."""
        headers = await _get_auth_headers(client, "createnaive")
        payload = _trade_payload(opened_at="2025-01-15T10:00:00")  # no tz
        response = await client.post("/api/v1/trades", json=payload, headers=headers)
        assert response.status_code == 422

    async def test_create_combo_trade_sets_null_vwap_fields(
        self, client: AsyncClient
    ) -> None:
        """Creating a COMBO trade should keep asset_class/quantity/prices null."""
        headers = await _get_auth_headers(client, "createcombo")
        payload = {
            "symbol": "AAPL",
            "direction": "LONG",
            "is_combo": True,
            "opened_at": datetime(2025, 1, 15, 10, 0, tzinfo=UTC).isoformat(),
        }
        response = await client.post("/api/v1/trades", json=payload, headers=headers)
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
        create_resp = await client.post(
            "/api/v1/trades", json=_trade_payload(), headers=headers
        )
        trade_id = create_resp.json()["data"]["id"]

        response = await client.get(f"/api/v1/trades/{trade_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["data"]["id"] == trade_id

    async def test_get_nonexistent_trade_returns_404(self, client: AsyncClient) -> None:
        """Should return 404 for an unknown trade ID."""
        headers = await _get_auth_headers(client, "get404")
        response = await client.get(f"/api/v1/trades/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404


@pytest.mark.integration
class TestListTrades:
    """Integration tests for ``GET /api/v1/trades``."""

    async def test_list_returns_envelope(self, client: AsyncClient) -> None:
        """Should return a CursorPage wrapped in a ResponseEnvelope."""
        headers = await _get_auth_headers(client, "listenv")
        response = await client.get("/api/v1/trades", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "items" in body["data"]
        assert "next_cursor" in body["data"]

    async def test_list_invalid_cursor_returns_400(self, client: AsyncClient) -> None:
        """An invalid cursor token should return HTTP 400."""
        headers = await _get_auth_headers(client, "listcursor")
        response = await client.get(
            "/api/v1/trades?cursor=INVALID_CURSOR!!!", headers=headers
        )
        assert response.status_code == 400

    async def test_limit_out_of_range_returns_422(self, client: AsyncClient) -> None:
        """A limit > 100 should return HTTP 422."""
        headers = await _get_auth_headers(client, "listlimit")
        response = await client.get("/api/v1/trades?limit=999", headers=headers)
        assert response.status_code == 422


@pytest.mark.integration
class TestUpdateTrade:
    """Integration tests for ``PATCH /api/v1/trades/{trade_id}``."""

    async def test_patch_updates_field(self, client: AsyncClient) -> None:
        """PATCH should update only the supplied field."""
        headers = await _get_auth_headers(client, "patchupd")
        create_resp = await client.post(
            "/api/v1/trades", json=_trade_payload(), headers=headers
        )
        trade_id = create_resp.json()["data"]["id"]

        response = await client.patch(
            f"/api/v1/trades/{trade_id}",
            json={"notes": "Updated note"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["data"]["notes"] == "Updated note"

    async def test_patch_nonexistent_returns_404(self, client: AsyncClient) -> None:
        """PATCH on a non-existent trade should return 404."""
        headers = await _get_auth_headers(client, "patch404")
        response = await client.patch(
            f"/api/v1/trades/{uuid.uuid4()}", json={"notes": "x"}, headers=headers
        )
        assert response.status_code == 404

    async def test_patch_is_combo_is_ignored(self, client: AsyncClient) -> None:
        """PATCH must not toggle is_combo once trade is created."""
        headers = await _get_auth_headers(client, "patchcombo")
        create_resp = await client.post(
            "/api/v1/trades",
            json={
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
            f"/api/v1/trades/{trade_id}",
            json={"is_combo": False, "notes": "still combo"},
            headers=headers,
        )
        assert patch_resp.status_code == 200, patch_resp.text
        assert patch_resp.json()["data"]["is_combo"] is True


@pytest.mark.integration
class TestDeleteTrade:
    """Integration tests for ``DELETE /api/v1/trades/{trade_id}``."""

    async def test_delete_returns_204(self, client: AsyncClient) -> None:
        """DELETE should return 204 No Content."""
        headers = await _get_auth_headers(client, "del204")
        create_resp = await client.post(
            "/api/v1/trades", json=_trade_payload(), headers=headers
        )
        trade_id = create_resp.json()["data"]["id"]

        response = await client.delete(f"/api/v1/trades/{trade_id}", headers=headers)
        assert response.status_code == 204

    async def test_delete_then_get_returns_404(self, client: AsyncClient) -> None:
        """After deletion, GET should return 404."""
        headers = await _get_auth_headers(client, "delget")
        create_resp = await client.post(
            "/api/v1/trades", json=_trade_payload(), headers=headers
        )
        trade_id = create_resp.json()["data"]["id"]

        await client.delete(f"/api/v1/trades/{trade_id}", headers=headers)
        response = await client.get(f"/api/v1/trades/{trade_id}", headers=headers)
        assert response.status_code == 404

    async def test_delete_nonexistent_returns_404(self, client: AsyncClient) -> None:
        """DELETE on a non-existent trade should return 404."""
        headers = await _get_auth_headers(client, "del404")
        response = await client.delete(
            f"/api/v1/trades/{uuid.uuid4()}", headers=headers
        )
        assert response.status_code == 404


# TestHasConflictFilter removed: has_conflict field was removed in the
# simplified-execution-model spec (task 5.5). The ?has_conflict filter
# query parameter no longer exists on the trades list endpoint.
