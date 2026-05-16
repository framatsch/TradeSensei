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

"""Integration tests verifying legacy endpoints are removed (return 404).

Spec: openspec/changes/legacy-metadata-cleanup/specs/legacy-metadata-removal/spec.md

These endpoints must not exist in the API:
- GET /api/v1/tags
- POST /api/v1/tags
- GET /api/v1/market-phases
- GET /api/v1/checkin-fields
"""

import uuid

import pytest
from httpx import AsyncClient

_REGISTER_URL = "/api/v1/auth/register"
_TOKEN_URL = "/api/v1/auth/token"


async def _get_auth_headers(client: AsyncClient) -> dict[str, str]:
    uid = uuid.uuid4().hex[:8]
    reg = await client.post(
        _REGISTER_URL,
        json={
            "username": f"leg_{uid}",
            "email": f"leg_{uid}@example.com",
            "password": "Legacy@99Test",
        },
    )
    assert reg.status_code == 201, reg.text
    login = await client.post(
        _TOKEN_URL,
        data={"username": f"leg_{uid}", "password": "Legacy@99Test"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.integration
class TestLegacyEndpointsRemoved:
    """Verify that legacy metadata endpoints return 404."""

    async def test_get_tags_returns_404(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client)
        resp = await client.get("/api/v1/tags", headers=headers)
        assert resp.status_code == 404

    async def test_post_tags_returns_404(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client)
        resp = await client.post(
            "/api/v1/tags",
            json={"name": "test-tag"},
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_get_market_phases_returns_404(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client)
        resp = await client.get("/api/v1/market-phases", headers=headers)
        assert resp.status_code == 404

    async def test_get_checkin_fields_returns_404(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client)
        resp = await client.get("/api/v1/checkin-fields", headers=headers)
        assert resp.status_code == 404
