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

"""Integration tests for market indexes API."""

import uuid

import pytest
from httpx import AsyncClient


async def _auth_headers(client: AsyncClient, *, prefix: str) -> dict[str, str]:
    suffix = uuid.uuid4().hex[:8]
    username = f"{prefix}_{suffix}"
    email = f"{prefix}_{suffix}@example.com"
    password = "IndexP@ss99"

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


@pytest.mark.integration
async def test_market_indexes_crud_and_non_owner_access(client: AsyncClient) -> None:
    owner = await _auth_headers(client, prefix="index_owner")
    other = await _auth_headers(client, prefix="index_other")

    create = await client.post(
        "/api/v1/market-indexes",
        headers=owner,
        json={
            "symbol": "RTY",
            "name": "Russell 2000",
            "tradingview_url": "https://www.tradingview.com/symbols/TVC-RUT/",
            "is_active": True,
        },
    )
    assert create.status_code == 201, create.text
    index_id = str(create.json()["data"]["id"])

    listed = await client.get("/api/v1/market-indexes", headers=owner)
    assert listed.status_code == 200, listed.text

    patched = await client.patch(
        f"/api/v1/market-indexes/{index_id}",
        headers=owner,
        json={"name": "Russell 2000 Updated"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["name"] == "Russell 2000 Updated"

    foreign_patch = await client.patch(
        f"/api/v1/market-indexes/{index_id}",
        headers=other,
        json={"name": "Hacked"},
    )
    assert foreign_patch.status_code in {403, 404}, foreign_patch.text

    foreign_delete = await client.delete(
        f"/api/v1/market-indexes/{index_id}",
        headers=other,
    )
    assert foreign_delete.status_code in {403, 404}, foreign_delete.text

    deleted = await client.delete(f"/api/v1/market-indexes/{index_id}", headers=owner)
    assert deleted.status_code == 204, deleted.text
