"""Integration tests for execution endpoints.

Runs against a real PostgreSQL instance via the test client and session fixtures.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from httpx import AsyncClient

_REGISTER_URL = "/api/v1/auth/register"
_LOGIN_URL = "/api/v1/auth/login"
_TOKEN_URL = "/api/v1/auth/token"


async def _get_auth_headers(client: AsyncClient, suffix: str = "") -> dict[str, str]:
    """Register a throwaway user and return Bearer auth headers."""
    uid = uuid.uuid4().hex[:8] + suffix
    reg = await client.post(
        _REGISTER_URL,
        json={
            "username": f"exec_{uid}",
            "email": f"exec_{uid}@example.com",
            "password": "ExecTest@99",
        },
    )
    assert reg.status_code == 201, f"Register failed: {reg.text}"
    login = await client.post(
        _TOKEN_URL,
        data={"username": f"exec_{uid}@example.com", "password": "ExecTest@99"},
    )
    assert login.status_code == 200, f"Login failed: {login.text}"
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_trade(
    client: AsyncClient, headers: dict[str, str], overrides: dict | None = None
) -> dict:
    """Create a default trade using the API to ensure all DB invariants and triggers fire."""
    payload = {
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

    res = await client.post("/api/v1/trades", json=payload, headers=headers)
    assert res.status_code == 201
    return res.json()["data"]


class TestExecutionAPI:
    """Test suite for /api/v1/executions and /api/v1/trades/{id}/executions."""

    async def test_create_execution(self, client: AsyncClient) -> None:
        """POST /trades/{trade_id}/executions should return 201 and create execution."""
        headers = await _get_auth_headers(client, "cre_exec")
        trade = await _create_trade(client, headers)
        trade_id = trade["id"]

        payload = {
            "direction": "SHORT",
            "quantity": "5.00",
            "price": "160.00",
            "commission": "1.00",
            "executed_at": datetime.now(UTC).isoformat(),
        }

        res = await client.post(
            f"/api/v1/trades/{trade_id}/executions", json=payload, headers=headers
        )
        assert res.status_code == 201, res.text
        data = res.json()
        assert data["trade_id"] == trade_id
        assert data["direction"] == "SHORT"
        assert Decimal(data["quantity"]) == Decimal("5")

        # Verify trade was re-aggregated
        trade_res = await client.get(f"/api/v1/trades/{trade_id}", headers=headers)
        assert trade_res.status_code == 200
        trade_data = trade_res.json()["data"]
        # Trade should now have exit_price computed
        assert trade_data["exit_price"] is not None

    async def test_create_execution_validation(self, client: AsyncClient) -> None:
        """POST /trades/{trade_id}/executions with invalid data should return 422."""
        headers = await _get_auth_headers(client, "cre_exec_val")
        trade = await _create_trade(client, headers)

        payload = {
            "direction": "INVALID",
            "quantity": "-5.00",
            "price": "160.00",
            "executed_at": datetime.now(UTC).isoformat(),
        }

        res = await client.post(
            f"/api/v1/trades/{trade['id']}/executions", json=payload, headers=headers
        )
        assert res.status_code == 422

    async def test_list_executions(self, client: AsyncClient) -> None:
        """GET /trades/{trade_id}/executions should return all executions."""
        headers = await _get_auth_headers(client, "list_exec")
        trade = await _create_trade(client, headers)
        trade_id = trade["id"]

        res = await client.get(f"/api/v1/trades/{trade_id}/executions", headers=headers)
        assert res.status_code == 200
        data = res.json()
        # Should have the auto-created initial execution from the trade
        assert len(data) >= 1

    async def test_update_execution(self, client: AsyncClient) -> None:
        """PATCH /executions/{execution_id} should update and return execution."""
        headers = await _get_auth_headers(client, "upd_exec")
        trade = await _create_trade(client, headers)
        trade_id = trade["id"]

        # Fetch executions to get the auto-created one
        list_res = await client.get(
            f"/api/v1/trades/{trade_id}/executions", headers=headers
        )
        ex_id = list_res.json()[0]["id"]

        patch_res = await client.patch(
            f"/api/v1/executions/{ex_id}", json={"price": "155.00"}, headers=headers
        )
        assert patch_res.status_code == 200, patch_res.text
        assert Decimal(patch_res.json()["price"]) == Decimal("155.00")

    async def test_delete_execution_cascade(self, client: AsyncClient) -> None:
        """DELETE /executions/{execution_id} should delete execution, deleting trade if empty."""
        headers = await _get_auth_headers(client, "del_exec")
        trade = await _create_trade(client, headers)
        trade_id = trade["id"]

        list_res = await client.get(
            f"/api/v1/trades/{trade_id}/executions", headers=headers
        )
        ex_id = list_res.json()[0]["id"]

        del_res = await client.delete(f"/api/v1/executions/{ex_id}", headers=headers)
        assert del_res.status_code == 204

        # Trade should also be deleted
        get_res = await client.get(f"/api/v1/trades/{trade_id}", headers=headers)
        assert get_res.status_code == 404

    async def test_reassign_execution(self, client: AsyncClient) -> None:
        """POST /executions/{execution_id}/reassign should move execution."""
        headers = await _get_auth_headers(client, "reassign")
        source_trade = await _create_trade(client, headers)
        target_trade = await _create_trade(client, headers)

        # Get execution from source_trade
        list_res = await client.get(
            f"/api/v1/trades/{source_trade['id']}/executions", headers=headers
        )
        ex_id = list_res.json()[0]["id"]

        reassign_res = await client.post(
            f"/api/v1/executions/{ex_id}/reassign",
            json={"target_trade_id": target_trade["id"]},
            headers=headers,
        )
        assert reassign_res.status_code == 200
        assert reassign_res.json()["execution"]["trade_id"] == target_trade["id"]

        # Source trade should be deleted since it was empty
        get_res = await client.get(
            f"/api/v1/trades/{source_trade['id']}", headers=headers
        )
        assert get_res.status_code == 404

    async def test_detach_execution(self, client: AsyncClient) -> None:
        """POST /executions/{execution_id}/detach should create new trade."""
        headers = await _get_auth_headers(client, "detach")
        trade = await _create_trade(client, headers)
        trade_id = trade["id"]

        # Add a second execution so we can detach one
        payload = {
            "direction": "LONG",
            "quantity": "5.00",
            "price": "160.00",
            "executed_at": datetime.now(UTC).isoformat(),
        }
        await client.post(
            f"/api/v1/trades/{trade_id}/executions", json=payload, headers=headers
        )

        list_res = await client.get(
            f"/api/v1/trades/{trade_id}/executions", headers=headers
        )
        executions = list_res.json()
        assert len(executions) == 2
        ex_to_detach = executions[1]["id"]

        detach_res = await client.post(
            f"/api/v1/executions/{ex_to_detach}/detach", headers=headers
        )
        assert detach_res.status_code == 200
        new_trade_id = detach_res.json()["id"]
        assert new_trade_id != trade_id
