"""Integration tests for the Trade Partial Close endpoint."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient

from tests.test_trades_api import _get_auth_headers, _trade_payload

_TRADES_URL = "/api/v1/trades"


@pytest.mark.integration
class TestPartialCloseTrade:
    """Integration tests for ``POST /api/v1/trades/{trade_id}/partial-close``."""

    async def test_partial_close_splits_trade(self, client: AsyncClient) -> None:
        """Partial close should reduce original quantity and create a new closed trade."""
        headers = await _get_auth_headers(client, "pcsplit")

        # 1. Create an open trade (10 shares, 10.00 commission)
        payload = _trade_payload(quantity="10", commission="10.00")
        create_resp = await client.post(_TRADES_URL, json=payload, headers=headers)
        trade_id = create_resp.json()["data"]["id"]

        # 2. Add a tag and a trade note to the original
        tag_resp = await client.post(
            "/api/v1/tags", json={"name": "Setup A"}, headers=headers
        )
        tag_id = tag_resp.json()["data"]["id"]
        await client.patch(
            f"{_TRADES_URL}/{trade_id}", json={"tag_ids": [tag_id]}, headers=headers
        )
        await client.post(
            f"{_TRADES_URL}/{trade_id}/notes",
            json={"content": "Note 1", "emotion": "fearful"},
            headers=headers,
        )

        # 3. Partially close 4 shares at 160.00
        close_payload = {
            "quantity": "4",
            "exit_price": "160.00",
            "closed_at": datetime(2025, 1, 15, 15, 0, tzinfo=UTC).isoformat(),
            "exit_commission": "2.50",
        }
        response = await client.post(
            f"{_TRADES_URL}/{trade_id}/partial-close",
            json=close_payload,
            headers=headers,
        )

        assert response.status_code == 200
        new_trade = response.json()["data"]

        # Verify new trade details
        assert Decimal(new_trade["quantity"]) == Decimal("4")
        assert Decimal(new_trade["exit_price"]) == Decimal("160.00")
        # Prop entry commission: (10 * 4) / 10 = 4.00. Total: 4.00 + 2.50 = 6.50
        assert Decimal(new_trade["commission"]) == Decimal("6.50")
        assert new_trade["closed_at"] is not None

        # Verify metadata duplication
        assert len(new_trade["tags"]) == 1
        assert new_trade["tags"][0]["name"] == "Setup A"
        assert len(new_trade["trade_notes"]) == 1
        assert new_trade["trade_notes"][0]["content"] == "Note 1"

        # 4. Verify original trade was updated
        orig_resp = await client.get(f"{_TRADES_URL}/{trade_id}", headers=headers)
        orig_trade = orig_resp.json()["data"]
        assert Decimal(orig_trade["quantity"]) == Decimal("6")
        assert Decimal(orig_trade["commission"]) == Decimal("6.00")
        assert orig_trade["closed_at"] is None

    async def test_partial_close_full_quantity_closes_inplace(
        self, client: AsyncClient
    ) -> None:
        """If quantity matches total, it should just perform a standard close."""
        headers = await _get_auth_headers(client, "pcfull")

        payload = _trade_payload(quantity="10", commission="5.00")
        create_resp = await client.post(_TRADES_URL, json=payload, headers=headers)
        trade_id = create_resp.json()["data"]["id"]

        close_payload = {
            "quantity": "10",
            "exit_price": "170.00",
            "closed_at": datetime(2025, 1, 15, 16, 0, tzinfo=UTC).isoformat(),
            "exit_commission": "1.00",
        }
        response = await client.post(
            f"{_TRADES_URL}/{trade_id}/partial-close",
            json=close_payload,
            headers=headers,
        )

        assert response.status_code == 200
        closed_trade = response.json()["data"]
        assert closed_trade["id"] == trade_id
        assert closed_trade["quantity"] == "10.00000000"
        assert Decimal(closed_trade["commission"]) == Decimal("6.00")  # 5 + 1
        assert closed_trade["closed_at"] is not None

    async def test_partial_close_invalid_quantity_returns_400(
        self, client: AsyncClient
    ) -> None:
        """Should return 400 if quantity exceeds available."""
        headers = await _get_auth_headers(client, "pcinv")

        payload = _trade_payload(quantity="5")
        create_resp = await client.post(_TRADES_URL, json=payload, headers=headers)
        trade_id = create_resp.json()["data"]["id"]

        close_payload = {
            "quantity": "6",  # More than 5
            "exit_price": "100.00",
            "closed_at": datetime.now(UTC).isoformat(),
        }
        response = await client.post(
            f"{_TRADES_URL}/{trade_id}/partial-close",
            json=close_payload,
            headers=headers,
        )
        assert response.status_code == 400
        assert "exceeds available quantity" in response.json()["detail"]

    async def test_partial_close_already_closed_returns_400(
        self, client: AsyncClient
    ) -> None:
        """Should return 400 if trade is already closed."""
        headers = await _get_auth_headers(client, "pcclosed")

        payload = _trade_payload(
            quantity="5", exit_price="110", closed_at=datetime.now(UTC).isoformat()
        )
        create_resp = await client.post(_TRADES_URL, json=payload, headers=headers)
        trade_id = create_resp.json()["data"]["id"]

        close_payload = {
            "quantity": "1",
            "exit_price": "120.00",
            "closed_at": datetime.now(UTC).isoformat(),
        }
        response = await client.post(
            f"{_TRADES_URL}/{trade_id}/partial-close",
            json=close_payload,
            headers=headers,
        )
        assert response.status_code == 400
        assert "already closed" in response.json()["detail"]
