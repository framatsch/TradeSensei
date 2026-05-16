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

"""Integration tests for the bulk trade endpoints.

Covers:
- POST /api/v1/trades/bulk/delete
- POST /api/v1/trades/bulk/assign-taxonomies
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


async def _create_portfolio_and_account(
    client: AsyncClient,
    headers: dict[str, str],
) -> tuple[str, str]:
    """Create a portfolio and account for bulk trade tests.

    Args:
        client: The HTTPX test client.
        headers: Auth headers.

    Returns:
        Tuple of ``(portfolio_id, account_id)``.
    """
    portfolio_resp = await client.post(
        "/api/v1/portfolios",
        json={"name": "Bulk Trades Portfolio", "base_currency": "USD"},
        headers=headers,
    )
    assert portfolio_resp.status_code == 201, portfolio_resp.text
    portfolio_id = str(portfolio_resp.json()["data"]["id"])

    account_resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        json={"name": "Bulk Trades Account", "type": "manual", "currency": "USD"},
        headers=headers,
    )
    assert account_resp.status_code == 201, account_resp.text
    account_id = str(account_resp.json()["data"]["id"])
    return portfolio_id, account_id


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
    portfolio_id: str,
    account_id: str,
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
        f"/api/v1/portfolios/{portfolio_id}/trades",
        json=_trade_payload(account_id=account_id, **kwargs),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return str(response.json()["data"]["id"])


async def _create_taxonomy(
    client: AsyncClient,
    headers: dict[str, str],
    name: str = "testbulktaxonomy",
) -> str:
    """Create a taxonomy and return its UUID string.

    Args:
        client: The HTTPX test client.
        headers: Auth headers for the request.
        name: Name to give the taxonomy.

    Returns:
        The created taxonomy's UUID as a string.
    """
    response = await client.post(
        "/api/v1/taxonomies",
        json={"name": name, "scope": "trades", "color_hex": "#22c55e"},
        headers=headers,
    )
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
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)
        id1 = await _create_trade(client, h, portfolio_id, account_id, symbol="GOOG")
        id2 = await _create_trade(client, h, portfolio_id, account_id, symbol="MSFT")

        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades/bulk/delete",
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
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)
        id1 = await _create_trade(client, h, portfolio_id, account_id, symbol="NVDA")
        fake_id = str(uuid.uuid4())

        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades/bulk/delete",
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
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)
        id1 = await _create_trade(client, h, portfolio_id, account_id, symbol="AMZN")

        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades/bulk/delete",
            json={"trade_ids": [id1]},
            headers=h,
        )

        get_resp = await client.get(
            f"/api/v1/portfolios/{portfolio_id}/trades/{id1}", headers=h
        )
        assert get_resp.status_code == 404

    async def test_bulk_delete_empty_list_returns_422(
        self, client: AsyncClient
    ) -> None:
        """An empty trade_ids list should fail validation (min_length=1)."""
        h = await _get_auth_headers(client)
        portfolio_id, _ = await _create_portfolio_and_account(client, h)
        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades/bulk/delete",
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
        portfolio_id, _ = await _create_portfolio_and_account(client, h)
        ids = [str(uuid.uuid4()) for _ in range(101)]
        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades/bulk/delete",
            json={"trade_ids": ids},
            headers=h,
        )
        assert response.status_code == 422


@pytest.mark.integration
class TestBulkAssignTags:
    """Integration tests for ``POST /api/v1/trades/bulk/assign-taxonomies``."""

    async def test_bulk_add_taxonomies_returns_200(self, client: AsyncClient) -> None:
        """Adding taxonomies to existing trades should return 200 with updated_count."""
        h = await _get_auth_headers(client)
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)
        trade_id = await _create_trade(client, h, portfolio_id, account_id, symbol="SPY")
        taxonomy_id = await _create_taxonomy(client, h)

        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades/bulk/assign-taxonomies",
            json={
                "trade_ids": [trade_id],
                "taxonomy_ids": [taxonomy_id],
                "mode": "add",
            },
            headers=h,
        )
        assert response.status_code == 200
        assert response.json()["data"]["updated_count"] == 1

    async def test_bulk_remove_taxonomies_returns_200(self, client: AsyncClient) -> None:
        """Removing taxonomies from trades should return 200."""
        h = await _get_auth_headers(client)
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)
        trade_id = await _create_trade(client, h, portfolio_id, account_id, symbol="QQQ")
        taxonomy_id = await _create_taxonomy(client, h, name="removetaxonomy")

        # Add first
        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades/bulk/assign-taxonomies",
            json={"trade_ids": [trade_id], "taxonomy_ids": [taxonomy_id], "mode": "add"},
            headers=h,
        )

        # Now remove
        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades/bulk/assign-taxonomies",
            json={
                "trade_ids": [trade_id],
                "taxonomy_ids": [taxonomy_id],
                "mode": "remove",
            },
            headers=h,
        )
        assert response.status_code == 200
        assert response.json()["data"]["updated_count"] == 1

    async def test_bulk_assign_taxonomies_unknown_taxonomy_returns_404(
        self, client: AsyncClient
    ) -> None:
        """Supplying an unknown taxonomy UUID should return 404."""
        import uuid

        h = await _get_auth_headers(client)
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)
        trade_id = await _create_trade(client, h, portfolio_id, account_id, symbol="IWM")
        fake_taxonomy_id = str(uuid.uuid4())

        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades/bulk/assign-taxonomies",
            json={
                "trade_ids": [trade_id],
                "taxonomy_ids": [fake_taxonomy_id],
                "mode": "add",
            },
            headers=h,
        )
        assert response.status_code == 404

    async def test_bulk_assign_taxonomies_empty_trade_ids_returns_422(
        self, client: AsyncClient
    ) -> None:
        """Empty trade_ids should fail validation."""
        h = await _get_auth_headers(client)
        portfolio_id, _ = await _create_portfolio_and_account(client, h)
        taxonomy_id = await _create_taxonomy(client, h, name="validationtaxonomy")
        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades/bulk/assign-taxonomies",
            json={
                "trade_ids": [],
                "taxonomy_ids": [taxonomy_id],
                "mode": "add",
            },
            headers=h,
        )
        assert response.status_code == 422

    async def test_bulk_assign_taxonomies_invalid_mode_returns_422(
        self, client: AsyncClient
    ) -> None:
        """An invalid mode value should fail validation."""
        import uuid

        h = await _get_auth_headers(client)
        portfolio_id, _ = await _create_portfolio_and_account(client, h)
        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades/bulk/assign-taxonomies",
            json={
                "trade_ids": [str(uuid.uuid4())],
                "taxonomy_ids": [str(uuid.uuid4())],
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
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)
        trade_id = await _create_trade(client, h, portfolio_id, account_id, symbol="META")
        playbook_id = await _create_playbook(client, h)

        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades/bulk/assign-playbook",
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
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)
        trade_id = await _create_trade(client, h, portfolio_id, account_id, symbol="TSLA")
        playbook_id = await _create_playbook(client, h, name="Unassign PB")

        # Assign first
        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades/bulk/assign-playbook",
            json={"trade_ids": [trade_id], "playbook_id": playbook_id},
            headers=h,
        )

        # Now unassign
        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades/bulk/assign-playbook",
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
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)
        trade_id = await _create_trade(client, h, portfolio_id, account_id, symbol="COIN")
        fake_pb_id = str(uuid.uuid4())

        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades/bulk/assign-playbook",
            json={"trade_ids": [trade_id], "playbook_id": fake_pb_id},
            headers=h,
        )
        assert response.status_code == 404

    async def test_bulk_assign_playbook_empty_trade_ids_returns_422(
        self, client: AsyncClient
    ) -> None:
        """Empty trade_ids should fail validation."""
        h = await _get_auth_headers(client)
        portfolio_id, _ = await _create_portfolio_and_account(client, h)
        playbook_id = await _create_playbook(client, h, name="Val PB")
        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades/bulk/assign-playbook",
            json={"trade_ids": [], "playbook_id": playbook_id},
            headers=h,
        )
        assert response.status_code == 422
