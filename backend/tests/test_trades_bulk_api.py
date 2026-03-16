"""Integration tests for the bulk trade endpoints.

Covers:
- POST /api/v1/trades/bulk/delete
- POST /api/v1/trades/bulk/assign-tags
- POST /api/v1/trades/bulk/assign-playbook
"""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

_REGISTER_URL = "/api/v1/auth/register"
_TOKEN_URL = "/api/v1/auth/token"


async def _get_auth_headers(client: AsyncClient) -> dict[str, str]:
    """Register a throwaway user and return Bearer auth headers.

    Args:
        client: The HTTPX test client.

    Returns:
        A dict with the ``Authorization: Bearer …`` header.
    """
    import uuid

    uid = uuid.uuid4().hex[:8]
    reg = await client.post(
        _REGISTER_URL,
        json={
            "username": f"bulk_{uid}",
            "email": f"bulk_{uid}@example.com",
            "password": "BulkTest@99",
        },
    )
    assert reg.status_code == 201, f"Register failed: {reg.text}"
    login = await client.post(
        _TOKEN_URL,
        data={"username": f"bulk_{uid}", "password": "BulkTest@99"},
    )
    assert login.status_code == 200, f"Login failed: {login.text}"
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _trade_payload(**kwargs: object) -> dict[str, object]:
    """Build a minimal valid trade creation payload.

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


async def _create_trade(
    client: AsyncClient,
    headers: dict[str, str],
    **kwargs: object,
) -> str:
    """Create a trade and return its UUID string.

    Args:
        client: The HTTPX test client.
        headers: Auth headers for the request.
        **kwargs: Payload overrides passed to :func:`_trade_payload`.

    Returns:
        The created trade's UUID as a string.
    """
    response = await client.post(
        "/api/v1/trades", json=_trade_payload(**kwargs), headers=headers
    )
    assert response.status_code == 201, response.text
    return str(response.json()["data"]["id"])


async def _create_tag(
    client: AsyncClient,
    headers: dict[str, str],
    name: str = "testbulktag",
) -> str:
    """Create a tag and return its UUID string.

    Args:
        client: The HTTPX test client.
        headers: Auth headers for the request.
        name: Name to give the tag.

    Returns:
        The created tag's UUID as a string.
    """
    response = await client.post("/api/v1/tags", json={"name": name}, headers=headers)
    assert response.status_code == 201, response.text
    return str(response.json()["data"]["id"])


async def _create_playbook(
    client: AsyncClient,
    headers: dict[str, str],
    name: str = "Bulk Playbook",
) -> str:
    """Create a playbook and return its UUID string.

    Args:
        client: The HTTPX test client.
        headers: Auth headers for the request.
        name: Name to give the playbook.

    Returns:
        The created playbook's UUID as a string.
    """
    response = await client.post(
        "/api/v1/playbooks",
        json={"name": name, "description": "test"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return str(response.json()["data"]["id"])


@pytest.mark.integration
class TestBulkDeleteTrades:
    """Integration tests for ``POST /api/v1/trades/bulk/delete``."""

    async def test_bulk_delete_returns_200_and_count(self, client: AsyncClient) -> None:
        """Deleting existing trades should return 200 with correct deleted_count."""
        h = await _get_auth_headers(client)
        id1 = await _create_trade(client, h, symbol="GOOG")
        id2 = await _create_trade(client, h, symbol="MSFT")

        response = await client.post(
            "/api/v1/trades/bulk/delete",
            json={"trade_ids": [id1, id2]},
            headers=h,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["deleted_count"] == 2

    async def test_bulk_delete_unknown_ids_skipped(self, client: AsyncClient) -> None:
        """Unknown UUIDs are silently skipped; deleted_count only counts real deletes."""
        import uuid

        h = await _get_auth_headers(client)
        id1 = await _create_trade(client, h, symbol="NVDA")
        fake_id = str(uuid.uuid4())

        response = await client.post(
            "/api/v1/trades/bulk/delete",
            json={"trade_ids": [id1, fake_id]},
            headers=h,
        )
        assert response.status_code == 200
        assert response.json()["data"]["deleted_count"] == 1

    async def test_bulk_delete_trades_no_longer_accessible(
        self, client: AsyncClient
    ) -> None:
        """After bulk delete, each deleted trade should return 404 on GET."""
        h = await _get_auth_headers(client)
        id1 = await _create_trade(client, h, symbol="AMZN")

        await client.post(
            "/api/v1/trades/bulk/delete",
            json={"trade_ids": [id1]},
            headers=h,
        )

        get_resp = await client.get(f"/api/v1/trades/{id1}", headers=h)
        assert get_resp.status_code == 404

    async def test_bulk_delete_empty_list_returns_422(
        self, client: AsyncClient
    ) -> None:
        """An empty trade_ids list should fail validation (min_length=1)."""
        h = await _get_auth_headers(client)
        response = await client.post(
            "/api/v1/trades/bulk/delete",
            json={"trade_ids": []},
            headers=h,
        )
        assert response.status_code == 422

    async def test_bulk_delete_too_many_ids_returns_422(
        self, client: AsyncClient
    ) -> None:
        """More than 100 IDs should fail validation (max_length=100)."""
        import uuid

        h = await _get_auth_headers(client)
        ids = [str(uuid.uuid4()) for _ in range(101)]
        response = await client.post(
            "/api/v1/trades/bulk/delete",
            json={"trade_ids": ids},
            headers=h,
        )
        assert response.status_code == 422


@pytest.mark.integration
class TestBulkAssignTags:
    """Integration tests for ``POST /api/v1/trades/bulk/assign-tags``."""

    async def test_bulk_add_tags_returns_200(self, client: AsyncClient) -> None:
        """Adding tags to existing trades should return 200 with updated_count."""
        h = await _get_auth_headers(client)
        trade_id = await _create_trade(client, h, symbol="SPY")
        tag_id = await _create_tag(client, h)

        response = await client.post(
            "/api/v1/trades/bulk/assign-tags",
            json={
                "trade_ids": [trade_id],
                "tag_ids": [tag_id],
                "mode": "add",
            },
            headers=h,
        )
        assert response.status_code == 200
        assert response.json()["data"]["updated_count"] == 1

    async def test_bulk_remove_tags_returns_200(self, client: AsyncClient) -> None:
        """Removing tags from trades should return 200."""
        h = await _get_auth_headers(client)
        trade_id = await _create_trade(client, h, symbol="QQQ")
        tag_id = await _create_tag(client, h, name="removetag")

        # Add first
        await client.post(
            "/api/v1/trades/bulk/assign-tags",
            json={"trade_ids": [trade_id], "tag_ids": [tag_id], "mode": "add"},
            headers=h,
        )

        # Now remove
        response = await client.post(
            "/api/v1/trades/bulk/assign-tags",
            json={
                "trade_ids": [trade_id],
                "tag_ids": [tag_id],
                "mode": "remove",
            },
            headers=h,
        )
        assert response.status_code == 200
        assert response.json()["data"]["updated_count"] == 1

    async def test_bulk_assign_tags_unknown_tag_returns_404(
        self, client: AsyncClient
    ) -> None:
        """Supplying an unknown tag UUID should return 404."""
        import uuid

        h = await _get_auth_headers(client)
        trade_id = await _create_trade(client, h, symbol="IWM")
        fake_tag_id = str(uuid.uuid4())

        response = await client.post(
            "/api/v1/trades/bulk/assign-tags",
            json={
                "trade_ids": [trade_id],
                "tag_ids": [fake_tag_id],
                "mode": "add",
            },
            headers=h,
        )
        assert response.status_code == 404

    async def test_bulk_assign_tags_empty_trade_ids_returns_422(
        self, client: AsyncClient
    ) -> None:
        """Empty trade_ids should fail validation."""
        h = await _get_auth_headers(client)
        tag_id = await _create_tag(client, h, name="validationtag")
        response = await client.post(
            "/api/v1/trades/bulk/assign-tags",
            json={
                "trade_ids": [],
                "tag_ids": [tag_id],
                "mode": "add",
            },
            headers=h,
        )
        assert response.status_code == 422

    async def test_bulk_assign_tags_invalid_mode_returns_422(
        self, client: AsyncClient
    ) -> None:
        """An invalid mode value should fail validation."""
        import uuid

        h = await _get_auth_headers(client)
        response = await client.post(
            "/api/v1/trades/bulk/assign-tags",
            json={
                "trade_ids": [str(uuid.uuid4())],
                "tag_ids": [str(uuid.uuid4())],
                "mode": "INVALID_MODE",
            },
            headers=h,
        )
        assert response.status_code == 422


@pytest.mark.integration
class TestBulkAssignPlaybook:
    """Integration tests for ``POST /api/v1/trades/bulk/assign-playbook``."""

    async def test_bulk_assign_playbook_returns_200(self, client: AsyncClient) -> None:
        """Assigning a valid playbook to trades should return 200 with updated_count."""
        h = await _get_auth_headers(client)
        trade_id = await _create_trade(client, h, symbol="META")
        playbook_id = await _create_playbook(client, h)

        response = await client.post(
            "/api/v1/trades/bulk/assign-playbook",
            json={
                "trade_ids": [trade_id],
                "playbook_id": playbook_id,
            },
            headers=h,
        )
        assert response.status_code == 200
        assert response.json()["data"]["updated_count"] == 1

    async def test_bulk_unassign_playbook_returns_200(
        self, client: AsyncClient
    ) -> None:
        """Sending playbook_id=null should unassign the playbook from the trades."""
        h = await _get_auth_headers(client)
        trade_id = await _create_trade(client, h, symbol="TSLA")
        playbook_id = await _create_playbook(client, h, name="Unassign PB")

        # Assign first
        await client.post(
            "/api/v1/trades/bulk/assign-playbook",
            json={"trade_ids": [trade_id], "playbook_id": playbook_id},
            headers=h,
        )

        # Now unassign
        response = await client.post(
            "/api/v1/trades/bulk/assign-playbook",
            json={"trade_ids": [trade_id], "playbook_id": None},
            headers=h,
        )
        assert response.status_code == 200
        assert response.json()["data"]["updated_count"] == 1

    async def test_bulk_assign_unknown_playbook_returns_404(
        self, client: AsyncClient
    ) -> None:
        """Supplying an unknown playbook UUID should return 404."""
        import uuid

        h = await _get_auth_headers(client)
        trade_id = await _create_trade(client, h, symbol="COIN")
        fake_pb_id = str(uuid.uuid4())

        response = await client.post(
            "/api/v1/trades/bulk/assign-playbook",
            json={"trade_ids": [trade_id], "playbook_id": fake_pb_id},
            headers=h,
        )
        assert response.status_code == 404

    async def test_bulk_assign_playbook_empty_trade_ids_returns_422(
        self, client: AsyncClient
    ) -> None:
        """Empty trade_ids should fail validation."""
        h = await _get_auth_headers(client)
        playbook_id = await _create_playbook(client, h, name="Val PB")
        response = await client.post(
            "/api/v1/trades/bulk/assign-playbook",
            json={"trade_ids": [], "playbook_id": playbook_id},
            headers=h,
        )
        assert response.status_code == 422
