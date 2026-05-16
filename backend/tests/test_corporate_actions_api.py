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

import pytest
from httpx import AsyncClient

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
