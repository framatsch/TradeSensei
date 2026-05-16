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

"""Ownership tests for the portfolio-scoped account endpoints.

Verifies that GET, PATCH, and DELETE on an account owned by another user
returns 404 — the repository's WHERE user_id = :uid clause makes the
resource invisible rather than forbidden.

Task 10.12
"""

from typing import Any

import pytest
from httpx import AsyncClient


class TestAccountOwnership:
    """Task 10.12: Cross-user account access must be rejected with 404."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_other_users_account_returns_404(
        self,
        client: AsyncClient,
        primary_user: dict[str, Any],
        other_users_account: dict[str, Any],
    ) -> None:
        """GET scoped account on another user's portfolio must return 404."""
        account_id = other_users_account["id"]
        portfolio_id = other_users_account["portfolio_id"]
        resp = await client.get(
            f"/api/v1/portfolios/{portfolio_id}/accounts/{account_id}",
            headers=primary_user["headers"],
        )
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_patch_other_users_account_returns_404(
        self,
        client: AsyncClient,
        primary_user: dict[str, Any],
        other_users_account: dict[str, Any],
    ) -> None:
        """PATCH scoped account on another user's portfolio must return 404."""
        account_id = other_users_account["id"]
        portfolio_id = other_users_account["portfolio_id"]
        resp = await client.patch(
            f"/api/v1/portfolios/{portfolio_id}/accounts/{account_id}",
            json={"name": "hacked"},
            headers=primary_user["headers"],
        )
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_delete_other_users_account_returns_404(
        self,
        client: AsyncClient,
        primary_user: dict[str, Any],
        other_users_account: dict[str, Any],
    ) -> None:
        """DELETE scoped account on another user's portfolio must return 404."""
        account_id = other_users_account["id"]
        portfolio_id = other_users_account["portfolio_id"]
        resp = await client.delete(
            f"/api/v1/portfolios/{portfolio_id}/accounts/{account_id}",
            headers=primary_user["headers"],
        )
        assert resp.status_code == 404, resp.text
