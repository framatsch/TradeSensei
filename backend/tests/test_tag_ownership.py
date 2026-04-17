"""Ownership tests for the /api/v1/tags endpoints.

Verifies that GET, PATCH, and DELETE on a tag owned by another user
returns 404 — the repository's WHERE user_id = :uid clause makes the
resource invisible rather than forbidden.

Task 10.14
"""

from typing import Any

import pytest
from httpx import AsyncClient


class TestTagOwnership:
    """Task 10.14: Cross-user tag access must be rejected with 404."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_other_users_tag_returns_404(
        self,
        client: AsyncClient,
        primary_user: dict[str, Any],
        other_users_tag: dict[str, Any],
    ) -> None:
        """GET /tags/{id} on another user's tag must return 404."""
        tag_id = other_users_tag["id"]
        resp = await client.get(
            f"/api/v1/tags/{tag_id}",
            headers=primary_user["headers"],
        )
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_patch_other_users_tag_returns_404(
        self,
        client: AsyncClient,
        primary_user: dict[str, Any],
        other_users_tag: dict[str, Any],
    ) -> None:
        """PATCH /tags/{id} on another user's tag must return 404."""
        tag_id = other_users_tag["id"]
        resp = await client.patch(
            f"/api/v1/tags/{tag_id}",
            json={"name": "hacked-tag"},
            headers=primary_user["headers"],
        )
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_delete_other_users_tag_returns_404(
        self,
        client: AsyncClient,
        primary_user: dict[str, Any],
        other_users_tag: dict[str, Any],
    ) -> None:
        """DELETE /tags/{id} on another user's tag must return 404."""
        tag_id = other_users_tag["id"]
        resp = await client.delete(
            f"/api/v1/tags/{tag_id}",
            headers=primary_user["headers"],
        )
        assert resp.status_code == 404, resp.text
