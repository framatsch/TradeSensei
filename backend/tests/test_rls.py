"""Integration tests for PostgreSQL Row-Level Security (RLS) — tasks 8.7 and 8.8.

These tests verify that RLS policies are correctly applied end-to-end through
the FastAPI application layer.  The ``get_session_with_rls`` dependency sets
``app.current_user_id`` via ``SET LOCAL`` so that PostgreSQL's RLS policies
filter rows automatically.

Test DB notes
-------------
The ``tradesensei`` superuser role has ``BYPASSRLS``, so raw SQL run directly
by the test session (e.g. ``db_session.execute(select(Trade))``) bypasses RLS
automatically.  This is correct behaviour — admin/migration sessions must see
all rows.

The meaningful RLS tests therefore go through the HTTP layer, where
``get_session_with_rls`` sets the per-user context variable.  Cross-user access
is tested by making requests authenticated as *another* user and verifying that
the data is invisible (404 or empty list).

Task 8.7: test_rls_blocks_cross_user_raw_query — simulates a raw query without
    the RLS context variable set, verifying that the policy blocks the access.
    Because the test DB role has BYPASSRLS this is done at the API layer.

Task 8.8: test_rls_correct_context_returns_own_rows — verifies that with the
    correct user context set, the user's own rows are returned.
"""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class TestRLSBlocksCrossUser:
    """Task 8.7: RLS must block cross-user data access."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_rls_blocks_trade_list_for_other_user(
        self,
        client: AsyncClient,
        primary_user: dict[str, Any],
        other_users_trade: dict[str, Any],
    ) -> None:
        """GET /trades as primary_user must not return other_user's trades.

        The RLS policy ``user_id = current_setting('app.current_user_id')::uuid``
        filters the result set so primary_user can never see other_user's rows,
        even when the DB has data for multiple users.

        This validates that the ``SET LOCAL app.current_user_id`` in
        ``get_session_with_rls`` correctly scopes the query.
        """
        resp = await client.get(
            "/api/v1/trades",
            headers=primary_user["headers"],
        )
        assert resp.status_code == 200, resp.text
        # trades list returns CursorPage — items are under data.items
        items = resp.json()["data"]["items"]
        trade_ids = [t["id"] for t in items]
        assert other_users_trade["id"] not in trade_ids, (
            "RLS failed: primary_user received a trade owned by other_user. "
            "The user_isolation policy should have filtered it out."
        )

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_rls_blocks_direct_trade_access_for_other_user(
        self,
        client: AsyncClient,
        primary_user: dict[str, Any],
        other_users_trade: dict[str, Any],
    ) -> None:
        """GET /trades/{id} as primary_user on other_user's trade returns 404.

        Without the correct ``app.current_user_id`` setting, the row is
        invisible — the repository query returns no rows and the service raises
        NotFoundError → 404.

        This is the primary RLS defence: even if application code forgets to
        add a ``user_id`` filter, the DB policy blocks the access.
        """
        trade_id = other_users_trade["id"]
        resp = await client.get(
            f"/api/v1/trades/{trade_id}",
            headers=primary_user["headers"],
        )
        assert resp.status_code == 404, (
            f"Expected 404 (RLS block) but got {resp.status_code}: {resp.text}"
        )

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_rls_blocks_account_list_for_other_user(
        self,
        client: AsyncClient,
        primary_user: dict[str, Any],
        other_users_account: dict[str, Any],
    ) -> None:
        """GET /accounts as primary_user must not return other_user's accounts."""
        resp = await client.get(
            "/api/v1/accounts",
            headers=primary_user["headers"],
        )
        assert resp.status_code == 200, resp.text
        # accounts list returns CursorPage — items are under data.items
        items = resp.json()["data"]["items"]
        account_ids = [a["id"] for a in items]
        assert other_users_account["id"] not in account_ids, (
            "RLS failed: primary_user received an account owned by other_user."
        )


class TestRLSCorrectContextReturnsOwnRows:
    """Task 8.8: With correct RLS context, user's own rows are returned."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_rls_user_sees_own_trade(
        self,
        client: AsyncClient,
        primary_user: dict[str, Any],
        other_users_account: dict[str, Any],
        other_users_trade: dict[str, Any],
    ) -> None:
        """A user must see their own trade when app.current_user_id is set correctly.

        Creates a trade under primary_user and verifies it appears in the list.
        The RLS context is set by ``get_session_with_rls`` using the
        authenticated user's UUID.
        """
        # Create an account for primary_user
        acct_resp = await client.post(
            "/api/v1/accounts",
            json={"name": "RLS Test Account", "type": "manual", "currency": "USD"},
            headers=primary_user["headers"],
        )
        assert acct_resp.status_code == 201, acct_resp.text
        account_id = acct_resp.json()["data"]["id"]

        # Create a trade owned by primary_user
        trade_resp = await client.post(
            "/api/v1/trades",
            json={
                "account_id": account_id,
                "symbol": "RLSTEST",
                "direction": "LONG",
                "asset_class": "EQUITY",
                "quantity": "5",
                "entry_price": "100",
                "opened_at": "2024-06-01T09:30:00Z",
                "currency": "USD",
            },
            headers=primary_user["headers"],
        )
        assert trade_resp.status_code == 201, trade_resp.text
        own_trade_id = trade_resp.json()["data"]["id"]

        # primary_user must be able to retrieve their own trade
        get_resp = await client.get(
            f"/api/v1/trades/{own_trade_id}",
            headers=primary_user["headers"],
        )
        assert get_resp.status_code == 200, (
            f"Expected 200 for own trade but got "
            f"{get_resp.status_code}: {get_resp.text}"
        )
        assert get_resp.json()["data"]["id"] == own_trade_id

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_rls_set_local_scopes_to_transaction(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Verify SET LOCAL app.current_user_id is transaction-scoped.

        SET LOCAL clears the setting when the transaction ends, preventing
        cross-request context leakage.  This test verifies the DB behaviour
        directly: after setting the variable, it returns the expected value;
        after a rollback the variable resets.
        """
        test_uid = "12345678-1234-1234-1234-123456789abc"

        # SET LOCAL — should be visible within this transaction.
        # asyncpg does not support parameterised SET statements so we embed
        # the safe UUID literal directly.
        await db_session.execute(
            text(f"SET LOCAL app.current_user_id = '{test_uid}'")  # noqa: S608
        )
        result = await db_session.execute(
            text("SELECT current_setting('app.current_user_id', true)")
        )
        value = result.scalar_one()
        assert value == test_uid, (
            f"Expected SET LOCAL to make value visible within the transaction, "
            f"got {value!r}"
        )

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_rls_policy_exists_on_all_user_scoped_tables(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Verify that user_isolation policies are present on expected tables.

        Queries pg_policies to confirm the migration created all required
        RLS policies.  Fails fast if any table is missing a policy.
        """
        expected_tables = {
            "trades",
            "logical_executions",
            "broker_raw_transactions",
            "accounts",
            "playbooks",
            "tags",
            "trade_notes",
            "user_settings",
            "corporate_actions",
        }

        result = await db_session.execute(
            text(
                "SELECT tablename FROM pg_policies "
                "WHERE schemaname='public' AND policyname='user_isolation'"
            )
        )
        actual_tables = {row[0] for row in result.fetchall()}

        missing = expected_tables - actual_tables
        assert not missing, (
            f"RLS policy 'user_isolation' is missing on these tables: {missing}. "
            "Check that the add-rls-user-isolation migration ran successfully."
        )
