"""Integration tests for the /api/v1/trades endpoints.

These tests require a live database (TimescaleDB with migrations applied).
They use the ``client`` fixture from ``conftest.py`` which overrides the
``get_session`` dependency with a rolled-back transaction.
"""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient


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
        """Health endpoint should return 200 with status ok."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.integration
class TestCreateTrade:
    """Integration tests for ``POST /api/v1/trades``."""

    async def test_create_returns_201(self, client: AsyncClient) -> None:
        """Creating a valid trade should return HTTP 201."""
        response = await client.post("/api/v1/trades", json=_trade_payload())
        assert response.status_code == 201

    async def test_create_response_envelope(self, client: AsyncClient) -> None:
        """Response should be wrapped in the standard envelope."""
        response = await client.post("/api/v1/trades", json=_trade_payload())
        body = response.json()
        assert "data" in body
        assert body["data"]["symbol"] == "AAPL"
        assert body["data"]["direction"] == "LONG"

    async def test_create_missing_required_field(self, client: AsyncClient) -> None:
        """Missing a required field should return HTTP 422."""
        payload = _trade_payload()
        del payload["symbol"]  # type: ignore[attr-defined]
        response = await client.post("/api/v1/trades", json=payload)
        assert response.status_code == 422

    async def test_create_naive_datetime_rejected(self, client: AsyncClient) -> None:
        """A naive (no timezone) opened_at should return HTTP 422."""
        payload = _trade_payload(opened_at="2025-01-15T10:00:00")  # no tz
        response = await client.post("/api/v1/trades", json=payload)
        assert response.status_code == 422


@pytest.mark.integration
class TestGetTrade:
    """Integration tests for ``GET /api/v1/trades/{trade_id}``."""

    async def test_get_existing_trade(self, client: AsyncClient) -> None:
        """Should return the trade when it exists."""
        create_resp = await client.post("/api/v1/trades", json=_trade_payload())
        trade_id = create_resp.json()["data"]["id"]

        response = await client.get(f"/api/v1/trades/{trade_id}")
        assert response.status_code == 200
        assert response.json()["data"]["id"] == trade_id

    async def test_get_nonexistent_trade_returns_404(self, client: AsyncClient) -> None:
        """Should return 404 for an unknown trade ID."""
        import uuid

        response = await client.get(f"/api/v1/trades/{uuid.uuid4()}")
        assert response.status_code == 404


@pytest.mark.integration
class TestListTrades:
    """Integration tests for ``GET /api/v1/trades``."""

    async def test_list_returns_envelope(self, client: AsyncClient) -> None:
        """Should return a CursorPage wrapped in a ResponseEnvelope."""
        response = await client.get("/api/v1/trades")
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "items" in body["data"]
        assert "next_cursor" in body["data"]

    async def test_list_invalid_cursor_returns_400(self, client: AsyncClient) -> None:
        """An invalid cursor token should return HTTP 400."""
        response = await client.get("/api/v1/trades?cursor=INVALID_CURSOR!!!")
        assert response.status_code == 400

    async def test_limit_out_of_range_returns_422(self, client: AsyncClient) -> None:
        """A limit > 100 should return HTTP 422."""
        response = await client.get("/api/v1/trades?limit=999")
        assert response.status_code == 422


@pytest.mark.integration
class TestUpdateTrade:
    """Integration tests for ``PATCH /api/v1/trades/{trade_id}``."""

    async def test_patch_updates_field(self, client: AsyncClient) -> None:
        """PATCH should update only the supplied field."""
        create_resp = await client.post("/api/v1/trades", json=_trade_payload())
        trade_id = create_resp.json()["data"]["id"]

        response = await client.patch(
            f"/api/v1/trades/{trade_id}", json={"notes": "Updated note"}
        )
        assert response.status_code == 200
        assert response.json()["data"]["notes"] == "Updated note"

    async def test_patch_nonexistent_returns_404(self, client: AsyncClient) -> None:
        """PATCH on a non-existent trade should return 404."""
        import uuid

        response = await client.patch(
            f"/api/v1/trades/{uuid.uuid4()}", json={"notes": "x"}
        )
        assert response.status_code == 404


@pytest.mark.integration
class TestDeleteTrade:
    """Integration tests for ``DELETE /api/v1/trades/{trade_id}``."""

    async def test_delete_returns_204(self, client: AsyncClient) -> None:
        """DELETE should return 204 No Content."""
        create_resp = await client.post("/api/v1/trades", json=_trade_payload())
        trade_id = create_resp.json()["data"]["id"]

        response = await client.delete(f"/api/v1/trades/{trade_id}")
        assert response.status_code == 204

    async def test_delete_then_get_returns_404(self, client: AsyncClient) -> None:
        """After deletion, GET should return 404."""
        create_resp = await client.post("/api/v1/trades", json=_trade_payload())
        trade_id = create_resp.json()["data"]["id"]

        await client.delete(f"/api/v1/trades/{trade_id}")
        response = await client.get(f"/api/v1/trades/{trade_id}")
        assert response.status_code == 404

    async def test_delete_nonexistent_returns_404(self, client: AsyncClient) -> None:
        """DELETE on a non-existent trade should return 404."""
        import uuid

        response = await client.delete(f"/api/v1/trades/{uuid.uuid4()}")
        assert response.status_code == 404
