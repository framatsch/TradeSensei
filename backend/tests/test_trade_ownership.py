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

"""Ownership tests for the /api/v1/trades endpoints.

Verifies that GET, PATCH, and DELETE on a trade owned by another user
returns 404 (not 403) — the repository's WHERE user_id = :uid clause
makes the resource invisible rather than forbidden.

Task 10.10
"""

from typing import Any

import pytest
from httpx import AsyncClient


class TestTradeOwnership:
    """Task 10.10: Cross-user trade access must be rejected with 404."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_other_users_trade_returns_404(
        self,
        client: AsyncClient,
        primary_user: dict[str, Any],
        other_users_trade: dict[str, Any],
    ) -> None:
        """GET /trades/{id} on another user's trade must return 404."""
        trade_id = other_users_trade["id"]
        portfolio_id = other_users_trade["portfolio_id"]
        resp = await client.get(
            f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}",
            headers=primary_user["headers"],
        )
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_patch_other_users_trade_returns_404(
        self,
        client: AsyncClient,
        primary_user: dict[str, Any],
        other_users_trade: dict[str, Any],
    ) -> None:
        """PATCH /trades/{id} on another user's trade must return 404."""
        trade_id = other_users_trade["id"]
        portfolio_id = other_users_trade["portfolio_id"]
        resp = await client.patch(
            f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}",
            json={"journal": "hacked"},
            headers=primary_user["headers"],
        )
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_delete_other_users_trade_returns_404(
        self,
        client: AsyncClient,
        primary_user: dict[str, Any],
        other_users_trade: dict[str, Any],
    ) -> None:
        """DELETE /trades/{id} on another user's trade must return 404."""
        trade_id = other_users_trade["id"]
        portfolio_id = other_users_trade["portfolio_id"]
        resp = await client.delete(
            f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}",
            headers=primary_user["headers"],
        )
        assert resp.status_code == 404, resp.text
