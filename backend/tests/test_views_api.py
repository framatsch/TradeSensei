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

"""Integration tests for saved dashboard views API."""

import uuid

import pytest
from httpx import AsyncClient


async def _auth_headers(client: AsyncClient, *, prefix: str) -> dict[str, str]:
    suffix = uuid.uuid4().hex[:8]
    username = f"{prefix}_{suffix}"
    email = f"{prefix}_{suffix}@example.com"
    password = "ViewsP@ss99"

    register = await client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    assert register.status_code == 201, register.text

    login = await client.post(
        "/api/v1/auth/token",
        data={"username": username, "password": password},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _create_portfolio(client: AsyncClient, headers: dict[str, str], name: str) -> str:
    response = await client.post(
        "/api/v1/portfolios",
        json={"name": name, "base_currency": "USD"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return str(response.json()["data"]["id"])


@pytest.mark.integration
async def test_views_crud_owner_and_non_owner(client: AsyncClient) -> None:
    owner = await _auth_headers(client, prefix="views_owner")
    other = await _auth_headers(client, prefix="views_other")
    portfolio_id = await _create_portfolio(client, owner, "Views API")

    create = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/views",
        headers=owner,
        json={"name": "My View", "filter_config": {"currency_mode": "NATIVE"}},
    )
    assert create.status_code == 201, create.text
    view_id = str(create.json()["data"]["id"])

    foreign_create = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/views",
        headers=other,
        json={"name": "Forbidden", "filter_config": {"currency_mode": "NATIVE"}},
    )
    assert foreign_create.status_code in {403, 404}, foreign_create.text

    listed = await client.get(f"/api/v1/portfolios/{portfolio_id}/views", headers=owner)
    assert listed.status_code == 200, listed.text
    assert len(listed.json()["data"]) == 1

    get_ok = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/views/{view_id}",
        headers=owner,
    )
    assert get_ok.status_code == 200, get_ok.text

    get_missing = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/views/{uuid.uuid4()}",
        headers=owner,
    )
    assert get_missing.status_code == 404, get_missing.text

    patched = await client.patch(
        f"/api/v1/portfolios/{portfolio_id}/views/{view_id}",
        headers=owner,
        json={"name": "Renamed View"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["name"] == "Renamed View"

    deleted = await client.delete(
        f"/api/v1/portfolios/{portfolio_id}/views/{view_id}",
        headers=owner,
    )
    assert deleted.status_code == 204, deleted.text

    get_deleted = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/views/{view_id}",
        headers=owner,
    )
    assert get_deleted.status_code == 404, get_deleted.text
