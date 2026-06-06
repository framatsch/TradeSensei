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

"""Integration tests for the playbook taxonomy assignment endpoints.

Tests cover:
- POST /api/v1/playbooks/{playbook_id}/taxonomies
- GET /api/v1/playbooks/{playbook_id}/taxonomies
- DELETE /api/v1/playbooks/{playbook_id}/taxonomies/{taxonomy_id}
"""

import uuid

import pytest
from httpx import AsyncClient

_REGISTER_URL = "/api/v1/auth/register"
_TOKEN_URL = "/api/v1/auth/token"


async def _get_auth_headers(client: AsyncClient, suffix: str = "") -> dict[str, str]:
    uid = uuid.uuid4().hex[:8] + suffix
    reg = await client.post(
        _REGISTER_URL,
        json={
            "username": f"pt_{uid}",
            "email": f"pt_{uid}@example.com",
            "password": "PlaybookTax@99",
        },
    )
    assert reg.status_code == 201, reg.text
    login = await client.post(
        _TOKEN_URL,
        data={"username": f"pt_{uid}", "password": "PlaybookTax@99"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _create_playbook(client: AsyncClient, headers: dict[str, str], suffix: str = "") -> str:
    resp = await client.post(
        "/api/v1/playbooks",
        json={"name": f"Test Playbook {suffix}", "description": "test"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


async def _create_taxonomy(
    client: AsyncClient, headers: dict[str, str], scope: str = "checkins,playbook,trades", suffix: str = ""
) -> str:
    uid = uuid.uuid4().hex[:6]
    resp = await client.post(
        "/api/v1/taxonomies",
        json={"name": f"Tax {scope} {suffix} {uid}", "scope": scope, "color_hex": "#123456"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


@pytest.mark.integration
class TestAssignPlaybookTaxonomy:
    """Tests for POST /api/v1/playbooks/{playbook_id}/taxonomies."""

    async def test_assign_taxonomy_scope_all_returns_201(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client, "all")
        playbook_id = await _create_playbook(client, headers, "all")
        taxonomy_id = await _create_taxonomy(client, headers, scope="checkins,playbook,trades", suffix="all")

        resp = await client.post(
            f"/api/v1/playbooks/{playbook_id}/taxonomies",
            json={"taxonomy_id": taxonomy_id},
            headers=headers,
        )
        assert resp.status_code == 201

    async def test_assign_taxonomy_scope_playbook_returns_201(self, client: AsyncClient) -> None:
        """Taxonomy with scope='playbook' is valid for playbook assignment."""
        headers = await _get_auth_headers(client, "pb")
        playbook_id = await _create_playbook(client, headers, "pb")
        taxonomy_id = await _create_taxonomy(client, headers, scope="playbook", suffix="pb2")

        resp = await client.post(
            f"/api/v1/playbooks/{playbook_id}/taxonomies",
            json={"taxonomy_id": taxonomy_id},
            headers=headers,
        )
        assert resp.status_code == 201

    async def test_assign_taxonomy_scope_trades_returns_422(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client, "trd")
        playbook_id = await _create_playbook(client, headers, "trd")
        taxonomy_id = await _create_taxonomy(client, headers, scope="trades", suffix="trd")

        resp = await client.post(
            f"/api/v1/playbooks/{playbook_id}/taxonomies",
            json={"taxonomy_id": taxonomy_id},
            headers=headers,
        )
        assert resp.status_code == 422

    async def test_assign_taxonomy_scope_checkins_returns_422(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client, "chk")
        playbook_id = await _create_playbook(client, headers, "chk")
        taxonomy_id = await _create_taxonomy(client, headers, scope="checkins", suffix="chk")

        resp = await client.post(
            f"/api/v1/playbooks/{playbook_id}/taxonomies",
            json={"taxonomy_id": taxonomy_id},
            headers=headers,
        )
        assert resp.status_code == 422

    async def test_assign_archived_taxonomy_returns_422(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client, "arch")
        playbook_id = await _create_playbook(client, headers, "arch")
        taxonomy_id = await _create_taxonomy(client, headers, scope="checkins,playbook,trades", suffix="arch_all")

        # Archive by assigning to a trade and then deleting the taxonomy 
        # (DELETE archives when assignments exist).
        p = await client.post(
            "/api/v1/portfolios",
            json={"name": "Arch Portfolio", "base_currency": "USD"},
            headers=headers,
        )
        assert p.status_code == 201
        portfolio_id_arch = p.json()["data"]["id"]
        a = await client.post(
            f"/api/v1/portfolios/{portfolio_id_arch}/accounts",
            json={"name": "Arch Account", "type": "manual", "currency": "USD"},
            headers=headers,
        )
        assert a.status_code == 201
        account_id = a.json()["data"]["id"]
        t = await client.post(
            f"/api/v1/portfolios/{portfolio_id_arch}/trades",
            json={
                "account_id": account_id,
                "symbol": "ARCH",
                "direction": "LONG",
                "asset_class": "EQUITY",
                "quantity": "1",
                "entry_price": "100",
                "opened_at": "2025-01-01T10:00:00Z",
                "currency": "USD",
            },
            headers=headers,
        )
        assert t.status_code == 201
        trade_id = t.json()["data"]["id"]

        # Assign taxonomy to trade so DELETE will archive instead of hard-delete
        assign_resp = await client.post(
            f"/api/v1/trades/{trade_id}/taxonomies",
            json={"taxonomy_id": taxonomy_id},
            headers=headers,
        )
        assert assign_resp.status_code in (200, 201, 204), assign_resp.text

        # Now DELETE the taxonomy — should archive it since it has assignments
        del_resp = await client.delete(
            f"/api/v1/taxonomies/{taxonomy_id}",
            headers=headers,
        )
        assert del_resp.status_code in (200, 204), del_resp.text

        # Now try to assign the archived taxonomy to the playbook
        resp = await client.post(
            f"/api/v1/playbooks/{playbook_id}/taxonomies",
            json={"taxonomy_id": taxonomy_id},
            headers=headers,
        )
        assert resp.status_code == 422

    async def test_assign_duplicate_returns_409(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client, "dup")
        playbook_id = await _create_playbook(client, headers, "dup")
        taxonomy_id = await _create_taxonomy(client, headers, scope="checkins,playbook,trades", suffix="dup")

        await client.post(
            f"/api/v1/playbooks/{playbook_id}/taxonomies",
            json={"taxonomy_id": taxonomy_id},
            headers=headers,
        )
        resp = await client.post(
            f"/api/v1/playbooks/{playbook_id}/taxonomies",
            json={"taxonomy_id": taxonomy_id},
            headers=headers,
        )
        assert resp.status_code == 409

    async def test_assign_to_other_users_playbook_returns_404(
        self, client: AsyncClient, other_users_playbook: dict
    ) -> None:
        headers = await _get_auth_headers(client, "xpb")
        taxonomy_id = await _create_taxonomy(client, headers, scope="checkins,playbook,trades", suffix="xpb")

        resp = await client.post(
            f"/api/v1/playbooks/{other_users_playbook['id']}/taxonomies",
            json={"taxonomy_id": taxonomy_id},
            headers=headers,
        )
        assert resp.status_code == 404


@pytest.mark.integration
class TestListPlaybookTaxonomies:
    """Tests for GET /api/v1/playbooks/{playbook_id}/taxonomies."""

    async def test_list_returns_200_with_assigned_taxonomies(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client, "lst")
        playbook_id = await _create_playbook(client, headers, "lst")
        taxonomy_id = await _create_taxonomy(client, headers, scope="checkins,playbook,trades", suffix="lst")

        await client.post(
            f"/api/v1/playbooks/{playbook_id}/taxonomies",
            json={"taxonomy_id": taxonomy_id},
            headers=headers,
        )

        resp = await client.get(
            f"/api/v1/playbooks/{playbook_id}/taxonomies",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == taxonomy_id

    async def test_list_returns_empty_when_none_assigned(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client, "empty")
        playbook_id = await _create_playbook(client, headers, "empty")

        resp = await client.get(
            f"/api/v1/playbooks/{playbook_id}/taxonomies",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.integration
class TestRemovePlaybookTaxonomy:
    """Tests for DELETE /api/v1/playbooks/{playbook_id}/taxonomies/{taxonomy_id}."""

    async def test_delete_existing_assignment_returns_204(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client, "del")
        playbook_id = await _create_playbook(client, headers, "del")
        taxonomy_id = await _create_taxonomy(client, headers, scope="checkins,playbook,trades", suffix="del")

        await client.post(
            f"/api/v1/playbooks/{playbook_id}/taxonomies",
            json={"taxonomy_id": taxonomy_id},
            headers=headers,
        )

        resp = await client.delete(
            f"/api/v1/playbooks/{playbook_id}/taxonomies/{taxonomy_id}",
            headers=headers,
        )
        assert resp.status_code == 204

    async def test_delete_nonexistent_assignment_returns_404(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client, "delnx")
        playbook_id = await _create_playbook(client, headers, "delnx")
        fake_taxonomy_id = str(uuid.uuid4())

        resp = await client.delete(
            f"/api/v1/playbooks/{playbook_id}/taxonomies/{fake_taxonomy_id}",
            headers=headers,
        )
        assert resp.status_code == 404
