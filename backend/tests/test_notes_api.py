"""Integration tests for POST/PATCH /api/v1/trades/{id}/notes note length limits.

Requires a live database (TimescaleDB with migrations applied).
Uses the ``client`` fixture from ``conftest.py``.
"""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

_REGISTER_URL = "/api/v1/auth/register"
_TOKEN_URL = "/api/v1/auth/token"

NOTE_MAX_LENGTH = 5_000


async def _get_auth_headers(client: AsyncClient, suffix: str = "") -> dict[str, str]:
    """Register a throwaway user and return Bearer auth headers.

    Args:
        client: The HTTPX test client.
        suffix: Optional suffix to make the username unique across test classes.

    Returns:
        A dict with the ``Authorization: Bearer …`` header.
    """
    import uuid

    uid = uuid.uuid4().hex[:8] + suffix
    reg = await client.post(
        _REGISTER_URL,
        json={
            "username": f"nlen_{uid}",
            "email": f"nlen_{uid}@example.com",
            "password": "NotesLen@99",
        },
    )
    assert reg.status_code == 201, f"Register failed: {reg.text}"
    login = await client.post(
        _TOKEN_URL,
        data={"username": f"nlen_{uid}", "password": "NotesLen@99"},
    )
    assert login.status_code == 200, f"Login failed: {login.text}"
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_portfolio_and_account(
    client: AsyncClient,
    headers: dict[str, str],
    suffix: str,
) -> tuple[str, str]:
    """Create a portfolio and account for notes tests.

    Args:
        client: The HTTPX test client.
        headers: Auth headers for the request.
        suffix: Unique suffix for resource names.

    Returns:
        Tuple of ``(portfolio_id, account_id)``.
    """
    p_resp = await client.post(
        "/api/v1/portfolios",
        json={"name": f"Notes Portfolio {suffix}", "base_currency": "USD"},
        headers=headers,
    )
    assert p_resp.status_code == 201, p_resp.text
    portfolio_id = str(p_resp.json()["data"]["id"])

    a_resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        json={"name": f"Notes Account {suffix}", "type": "manual", "currency": "USD"},
        headers=headers,
    )
    assert a_resp.status_code == 201, a_resp.text
    account_id = str(a_resp.json()["data"]["id"])
    return portfolio_id, account_id


async def _create_trade(
    client: AsyncClient,
    headers: dict[str, str],
    portfolio_id: str,
    account_id: str,
) -> str:
    """Create a minimal trade and return its UUID string.

    Args:
        client: The HTTPX test client.
        headers: Auth headers for the request.

    Returns:
        The UUID string of the created trade.
    """
    payload = {
        "account_id": account_id,
        "symbol": "AAPL",
        "direction": "LONG",
        "asset_class": "EQUITY",
        "quantity": "10.00000000",
        "entry_price": "150.00000000",
        "opened_at": datetime(2024, 5, 10, 10, 0, tzinfo=UTC).isoformat(),
    }
    resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades", json=payload, headers=headers
    )
    assert resp.status_code == 201, f"Trade creation failed: {resp.text}"
    return str(resp.json()["data"]["id"])


@pytest.mark.integration
class TestNoteLengthCreate:
    """Tests for note length validation on POST /trades/{id}/notes."""

    async def test_create_note_exactly_max_length_returns_201(
        self, client: AsyncClient
    ) -> None:
        """Note with content of exactly 5000 characters should be accepted (201)."""
        headers = await _get_auth_headers(client, "create_max")
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "create_max"
        )
        trade_id = await _create_trade(client, headers, portfolio_id, account_id)

        content = "x" * NOTE_MAX_LENGTH
        resp = await client.post(
            f"/api/v1/trades/{trade_id}/notes",
            json={"content": content},
            headers=headers,
        )
        assert resp.status_code == 201, (
            f"Expected 201 for {NOTE_MAX_LENGTH}-char note, got {resp.status_code}: "
            f"{resp.text}"
        )

    async def test_create_note_over_max_length_returns_422(
        self, client: AsyncClient
    ) -> None:
        """Note with content of 5001 characters should be rejected (422)."""
        headers = await _get_auth_headers(client, "create_over")
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "create_over"
        )
        trade_id = await _create_trade(client, headers, portfolio_id, account_id)

        content = "x" * (NOTE_MAX_LENGTH + 1)
        resp = await client.post(
            f"/api/v1/trades/{trade_id}/notes",
            json={"content": content},
            headers=headers,
        )
        assert resp.status_code == 422, (
            f"Expected 422 for {NOTE_MAX_LENGTH + 1}-char note, got "
            f"{resp.status_code}: {resp.text}"
        )


@pytest.mark.integration
class TestNoteLengthUpdate:
    """Tests for note length validation on PATCH /trades/{id}/notes/{note_id}."""

    async def test_update_note_over_max_length_returns_422(
        self, client: AsyncClient
    ) -> None:
        """Updating a note with 5001 characters should be rejected (422)."""
        headers = await _get_auth_headers(client, "update_over")
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "update_over"
        )
        trade_id = await _create_trade(client, headers, portfolio_id, account_id)

        # First create a valid note
        create_resp = await client.post(
            f"/api/v1/trades/{trade_id}/notes",
            json={"content": "Initial note content"},
            headers=headers,
        )
        assert create_resp.status_code == 201, (
            f"Note creation failed: {create_resp.text}"
        )
        note_id = create_resp.json()["data"]["id"]

        # Now try to update with content over the limit
        content = "y" * (NOTE_MAX_LENGTH + 1)
        resp = await client.patch(
            f"/api/v1/trades/{trade_id}/notes/{note_id}",
            json={"content": content},
            headers=headers,
        )
        assert resp.status_code == 422, (
            f"Expected 422 for {NOTE_MAX_LENGTH + 1}-char update, got "
            f"{resp.status_code}: {resp.text}"
        )
