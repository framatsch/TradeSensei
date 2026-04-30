"""Ownership tests for the /api/v1/executions endpoints.

Verifies that PATCH and DELETE on an execution owned by another user
returns 404 — the repository's WHERE user_id = :uid clause makes the
resource invisible rather than forbidden.

Task 10.11
"""

from typing import Any

import pytest
from httpx import AsyncClient


class TestExecutionOwnership:
    """Task 10.11: Cross-user execution access must be rejected with 404."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_patch_other_users_execution_returns_404(
        self,
        client: AsyncClient,
        primary_user: dict[str, Any],
        other_users_execution: dict[str, Any],
    ) -> None:
        """PATCH /executions/{id} on another user's execution must return 404."""
        execution_id = other_users_execution["id"]
        portfolio_id = other_users_execution["portfolio_id"]
        resp = await client.patch(
            f"/api/v1/portfolios/{portfolio_id}/executions/{execution_id}",
            json={"price": "999"},
            headers=primary_user["headers"],
        )
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_delete_other_users_execution_returns_404(
        self,
        client: AsyncClient,
        primary_user: dict[str, Any],
        other_users_execution: dict[str, Any],
    ) -> None:
        """DELETE /executions/{id} on another user's execution must return 404."""
        execution_id = other_users_execution["id"]
        portfolio_id = other_users_execution["portfolio_id"]
        resp = await client.delete(
            f"/api/v1/portfolios/{portfolio_id}/executions/{execution_id}",
            headers=primary_user["headers"],
        )
        assert resp.status_code == 404, resp.text
