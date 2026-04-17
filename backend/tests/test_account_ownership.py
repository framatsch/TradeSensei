"""Ownership tests for the /api/v1/accounts endpoints.

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
        """GET /accounts/{id} on another user's account must return 404."""
        account_id = other_users_account["id"]
        resp = await client.get(
            f"/api/v1/accounts/{account_id}",
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
        """PATCH /accounts/{id} on another user's account must return 404."""
        account_id = other_users_account["id"]
        resp = await client.patch(
            f"/api/v1/accounts/{account_id}",
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
        """DELETE /accounts/{id} on another user's account must return 404."""
        account_id = other_users_account["id"]
        resp = await client.delete(
            f"/api/v1/accounts/{account_id}",
            headers=primary_user["headers"],
        )
        assert resp.status_code == 404, resp.text
