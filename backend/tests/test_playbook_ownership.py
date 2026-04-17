"""Ownership tests for the /api/v1/playbooks endpoints.

Verifies that GET, PATCH, and DELETE on a playbook owned by another user
returns 404 — the repository's WHERE user_id = :uid clause makes the
resource invisible rather than forbidden.

Task 10.13
"""

from typing import Any

import pytest
from httpx import AsyncClient


class TestPlaybookOwnership:
    """Task 10.13: Cross-user playbook access must be rejected with 404."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_other_users_playbook_returns_404(
        self,
        client: AsyncClient,
        primary_user: dict[str, Any],
        other_users_playbook: dict[str, Any],
    ) -> None:
        """GET /playbooks/{id} on another user's playbook must return 404."""
        playbook_id = other_users_playbook["id"]
        resp = await client.get(
            f"/api/v1/playbooks/{playbook_id}",
            headers=primary_user["headers"],
        )
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_patch_other_users_playbook_returns_404(
        self,
        client: AsyncClient,
        primary_user: dict[str, Any],
        other_users_playbook: dict[str, Any],
    ) -> None:
        """PATCH /playbooks/{id} on another user's playbook must return 404."""
        playbook_id = other_users_playbook["id"]
        resp = await client.patch(
            f"/api/v1/playbooks/{playbook_id}",
            json={"name": "hacked"},
            headers=primary_user["headers"],
        )
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_delete_other_users_playbook_returns_404(
        self,
        client: AsyncClient,
        primary_user: dict[str, Any],
        other_users_playbook: dict[str, Any],
    ) -> None:
        """DELETE /playbooks/{id} on another user's playbook must return 404."""
        playbook_id = other_users_playbook["id"]
        resp = await client.delete(
            f"/api/v1/playbooks/{playbook_id}",
            headers=primary_user["headers"],
        )
        assert resp.status_code == 404, resp.text
