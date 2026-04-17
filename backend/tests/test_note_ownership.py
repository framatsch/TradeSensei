"""Ownership tests for the /api/v1/trades/{trade_id}/notes endpoints.

Verifies that PATCH and DELETE on a note owned by another user (under
another user's trade) returns 404 — the repository's WHERE user_id = :uid
and trade_id = :trade_id clauses make the resource invisible.

Task 10.15
"""

from typing import Any

import pytest
from httpx import AsyncClient


class TestNoteOwnership:
    """Task 10.15: Cross-user note access must be rejected with 404."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_patch_other_users_note_returns_404(
        self,
        client: AsyncClient,
        primary_user: dict[str, Any],
        other_users_trade: dict[str, Any],
        other_users_note: dict[str, Any],
    ) -> None:
        """PATCH /trades/{trade_id}/notes/{id} on another user's note must be 404."""
        trade_id = other_users_trade["id"]
        note_id = other_users_note["id"]
        resp = await client.patch(
            f"/api/v1/trades/{trade_id}/notes/{note_id}",
            json={"content": "hacked note content"},
            headers=primary_user["headers"],
        )
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_delete_other_users_note_returns_404(
        self,
        client: AsyncClient,
        primary_user: dict[str, Any],
        other_users_trade: dict[str, Any],
        other_users_note: dict[str, Any],
    ) -> None:
        """DELETE /trades/{trade_id}/notes/{id} on another user's note must be 404."""
        trade_id = other_users_trade["id"]
        note_id = other_users_note["id"]
        resp = await client.delete(
            f"/api/v1/trades/{trade_id}/notes/{note_id}",
            headers=primary_user["headers"],
        )
        assert resp.status_code == 404, resp.text
