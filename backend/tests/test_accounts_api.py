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

"""Integration tests for the /api/v1/accounts resource.

These tests verify the full HTTP stack for the accounts CRUD endpoints:
list, create, get, update, and delete.  They also verify that accounts
are isolated between users (user A cannot see user B's accounts).

All tests use the ``client`` fixture from ``conftest.py`` which rolls back
the database after every test, keeping them fully isolated from each other.
"""

import uuid

import pytest
from httpx import AsyncClient

from app.services.broker_service import BrokerService

# ---------------------------------------------------------------------------
# URL constants
# ---------------------------------------------------------------------------

_REGISTER_URL = "/api/v1/auth/register"
_TOKEN_URL = "/api/v1/auth/token"
_PORTFOLIOS_URL = "/api/v1/portfolios"


def _accounts_url(portfolio_id: str) -> str:
    return f"/api/v1/portfolios/{portfolio_id}/accounts"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_and_get_token(
    client: AsyncClient,
    *,
    username: str,
    email: str,
    password: str = "S3cureP@ss99",
) -> str:
    """Register a user and return their JWT access token.

    Args:
        client: The test HTTP client.
        username: Username to register.
        email: Email address to register.
        password: Password to use for both registration and login.

    Returns:
        The ``access_token`` string extracted from the login response.
    """
    reg = await client.post(
        _REGISTER_URL,
        json={"username": username, "email": email, "password": password},
    )
    assert reg.status_code == 201, f"Registration failed: {reg.text}"

    login = await client.post(
        _TOKEN_URL,
        data={"username": username, "password": password},
    )
    assert login.status_code == 200, f"Login failed: {login.text}"
    return str(login.json()["access_token"])


def _auth(token: str) -> dict[str, str]:
    """Return an Authorization header dict for the given Bearer token.

    Args:
        token: The JWT access token string.

    Returns:
        A dict suitable for use as ``headers=`` in an HTTPX request.
    """
    return {"Authorization": f"Bearer {token}"}


async def _create_portfolio(
    client: AsyncClient,
    token: str,
    *,
    name: str,
    base_currency: str = "USD",
) -> str:
    resp = await client.post(
        _PORTFOLIOS_URL,
        json={"name": name, "base_currency": base_currency},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["data"]["id"])


_DEFAULT_ACCOUNT_PAYLOAD = {
    "name": "IBKR Main",
    "type": "ibkr",
    "currency": "USD",
}


# ---------------------------------------------------------------------------
# CRUD tests
# ---------------------------------------------------------------------------


class TestCreateAccount:
    """Integration tests for ``POST /api/v1/portfolios/{id}/accounts``."""

    @pytest.mark.integration
    async def test_create_account_success(self, client: AsyncClient) -> None:
        """POST /accounts must return 201 with an AccountRead envelope.

        The response body must contain a ``data`` object whose fields
        match the submitted payload.  The ``id`` must be a valid UUID and
        ``user_id`` must be present.
        """
        token = await _register_and_get_token(
            client, username="acc_creator", email="creator@example.com"
        )
        portfolio_id = await _create_portfolio(
            client,
            token,
            name="Creator Portfolio",
        )
        resp = await client.post(
            _accounts_url(portfolio_id),
            json=_DEFAULT_ACCOUNT_PAYLOAD,
            headers=_auth(token),
        )
        assert resp.status_code == 201

        account = resp.json()["data"]
        assert account["name"] == "IBKR Main"
        assert account["type"] == "ibkr"
        assert account["currency"] == "USD"
        assert account["is_active"] is True
        assert "id" in account
        assert "user_id" in account
        # Ensure the UUID is valid
        uuid.UUID(account["id"])

    @pytest.mark.integration
    async def test_create_account_requires_auth(self, client: AsyncClient) -> None:
        """POST scoped accounts without a token must return 401."""
        resp = await client.post(
            _accounts_url(str(uuid.uuid4())),
            json=_DEFAULT_ACCOUNT_PAYLOAD,
        )
        assert resp.status_code == 401

    @pytest.mark.integration
    async def test_create_account_missing_name_returns_422(
        self, client: AsyncClient
    ) -> None:
        """POST /accounts without the required ``name`` field must return 422."""
        token = await _register_and_get_token(
            client, username="acc_noname", email="noname@example.com"
        )
        portfolio_id = await _create_portfolio(
            client,
            token,
            name="No Name Portfolio",
        )
        resp = await client.post(
            _accounts_url(portfolio_id),
            json={"broker": "IBKR", "currency": "USD"},  # missing name
            headers=_auth(token),
        )
        assert resp.status_code == 422


class TestListAccounts:
    """Integration tests for ``GET /api/v1/portfolios/{id}/accounts``."""

    @pytest.mark.integration
    async def test_list_accounts(self, client: AsyncClient) -> None:
        """GET /accounts must return 200 with a CursorPage of AccountRead objects.

        After creating two accounts the list endpoint must return both of
        them in the ``data.items`` array with the correct total count.
        """
        token = await _register_and_get_token(
            client, username="acc_lister", email="lister@example.com"
        )
        headers = _auth(token)
        portfolio_id = await _create_portfolio(
            client,
            token,
            name="Lister Portfolio",
        )

        await client.post(
            _accounts_url(portfolio_id),
            json={"name": "Account A"},
            headers=headers,
        )
        await client.post(
            _accounts_url(portfolio_id),
            json={"name": "Account B"},
            headers=headers,
        )

        resp = await client.get(_accounts_url(portfolio_id), headers=headers)
        assert resp.status_code == 200

        page = resp.json()["data"]
        assert "items" in page
        assert "total" in page
        assert page["total"] == 2
        names = {item["name"] for item in page["items"]}
        assert names == {"Account A", "Account B"}

    @pytest.mark.integration
    async def test_list_accounts_empty_for_new_user(self, client: AsyncClient) -> None:
        """GET /accounts for a brand-new user must return an empty items list."""
        token = await _register_and_get_token(
            client, username="acc_empty", email="empty@example.com"
        )
        portfolio_id = await _create_portfolio(
            client,
            token,
            name="Empty Portfolio",
        )
        resp = await client.get(_accounts_url(portfolio_id), headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["data"]["items"] == []
        assert resp.json()["data"]["total"] == 0


class TestGetAccount:
    """Integration tests for ``GET /api/v1/portfolios/{id}/accounts/{account_id}``."""

    @pytest.mark.integration
    async def test_get_account_success(self, client: AsyncClient) -> None:
        """GET /accounts/{id} must return 200 with the matching AccountRead.

        The response ``data.id`` must match the UUID from the creation
        response, and the name must match the submitted value.
        """
        token = await _register_and_get_token(
            client, username="acc_getter", email="getter@example.com"
        )
        headers = _auth(token)
        portfolio_id = await _create_portfolio(
            client,
            token,
            name="Getter Portfolio",
        )

        create_resp = await client.post(
            _accounts_url(portfolio_id), json={"name": "Fetch Me"}, headers=headers
        )
        account_id = create_resp.json()["data"]["id"]

        resp = await client.get(
            f"{_accounts_url(portfolio_id)}/{account_id}", headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "Fetch Me"
        assert resp.json()["data"]["id"] == account_id

    @pytest.mark.integration
    async def test_get_account_not_found_returns_404(self, client: AsyncClient) -> None:
        """GET /accounts/{id} for an unknown UUID must return 404.

        A random UUID that was never inserted must not produce a server
        error; the API must return HTTP 404 Not Found.
        """
        token = await _register_and_get_token(
            client, username="acc_404", email="notfound@example.com"
        )
        portfolio_id = await _create_portfolio(
            client,
            token,
            name="Not Found Portfolio",
        )
        unknown_id = uuid.uuid4()
        resp = await client.get(
            f"{_accounts_url(portfolio_id)}/{unknown_id}", headers=_auth(token)
        )
        assert resp.status_code == 404


class TestUpdateAccount:
    """Integration tests for scoped account update endpoints."""

    @pytest.mark.integration
    async def test_update_account_success(self, client: AsyncClient) -> None:
        """PATCH /accounts/{id} must return 200 with the updated AccountRead.

        Only the fields included in the request body must change; omitted
        fields must remain at their original values.
        """
        token = await _register_and_get_token(
            client, username="acc_updater", email="updater@example.com"
        )
        headers = _auth(token)
        portfolio_id = await _create_portfolio(
            client,
            token,
            name="Updater Portfolio",
        )

        create_resp = await client.post(
            _accounts_url(portfolio_id),
            json={"name": "Before Update", "type": "ibkr", "currency": "USD"},
            headers=headers,
        )
        account_id = create_resp.json()["data"]["id"]

        resp = await client.patch(
            f"{_accounts_url(portfolio_id)}/{account_id}",
            json={"name": "After Update"},
            headers=headers,
        )
        assert resp.status_code == 200
        updated = resp.json()["data"]
        assert updated["name"] == "After Update"
        # Untouched fields must be unchanged
        assert updated["type"] == "ibkr"
        assert updated["currency"] == "USD"

    @pytest.mark.integration
    async def test_update_account_not_found_returns_404(
        self, client: AsyncClient
    ) -> None:
        """PATCH /accounts/{id} for an unknown UUID must return 404."""
        token = await _register_and_get_token(
            client, username="acc_upd404", email="upd404@example.com"
        )
        portfolio_id = await _create_portfolio(
            client,
            token,
            name="Update 404 Portfolio",
        )
        unknown_id = uuid.uuid4()
        resp = await client.patch(
            f"{_accounts_url(portfolio_id)}/{unknown_id}",
            json={"name": "Ghost"},
            headers=_auth(token),
        )
        assert resp.status_code == 404


class TestAccountConnectionTest:
    """Integration tests for POST /accounts/test-connection."""

    @pytest.mark.integration
    async def test_test_connection_missing_required_property_returns_400(
        self, client: AsyncClient
    ) -> None:
        token = await _register_and_get_token(
            client, username="acc_conn_missing", email="conn-missing@example.com"
        )
        portfolio_id = await _create_portfolio(
            client,
            token,
            name="Connection Portfolio",
        )

        resp = await client.post(
            f"{_accounts_url(portfolio_id)}/test-connection",
            json={
                "type": "ibkr",
                "properties": {"ibkr_flex_query_id": "12345"},
            },
            headers=_auth(token),
        )
        assert resp.status_code == 400
        assert "ibkr_flex_token" in resp.json()["detail"]

    @pytest.mark.integration
    async def test_test_connection_ibkr_success_without_real_broker_keys(
        self,
        client: AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        token = await _register_and_get_token(
            client,
            username="acc_conn_ok",
            email="conn-ok@example.com",
        )
        portfolio_id = await _create_portfolio(
            client,
            token,
            name="Connection OK Portfolio",
        )

        async def _fake_test_ibkr(
            self: BrokerService,
            provided: dict[str, str],
            account: object,
            user_id: uuid.UUID,
            portfolio_id: uuid.UUID,
        ) -> None:
            del self, account, user_id, portfolio_id
            assert provided["ibkr_flex_token"] == "dummy-token"
            assert provided["ibkr_flex_query_id"] == "dummy-query"

        monkeypatch.setattr(BrokerService, "_test_ibkr", _fake_test_ibkr)

        resp = await client.post(
            f"{_accounts_url(portfolio_id)}/test-connection",
            json={
                "type": "ibkr",
                "properties": {
                    "ibkr_flex_token": "dummy-token",
                    "ibkr_flex_query_id": "dummy-query",
                },
            },
            headers=_auth(token),
        )

        assert resp.status_code == 200
        payload = resp.json()["data"]
        assert payload["success"] is True

    @pytest.mark.integration
    async def test_test_connection_schwab_success_without_real_broker_keys(
        self,
        client: AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        token = await _register_and_get_token(
            client,
            username="acc_conn_ok_schwab",
            email="conn-ok-schwab@example.com",
        )
        portfolio_id = await _create_portfolio(
            client,
            token,
            name="Connection Schwab Portfolio",
        )

        async def _fake_test_schwab(
            self: BrokerService,
            provided: dict[str, str],
            account: object,
        ) -> None:
            del self, account
            assert provided["schwab_app_key"] == "dummy-key"
            assert provided["schwab_app_secret"] == "dummy-secret"

        monkeypatch.setattr(BrokerService, "_test_schwab", _fake_test_schwab)

        resp = await client.post(
            f"{_accounts_url(portfolio_id)}/test-connection",
            json={
                "type": "schwab",
                "properties": {
                    "schwab_app_key": "dummy-key",
                    "schwab_app_secret": "dummy-secret",
                },
            },
            headers=_auth(token),
        )

        assert resp.status_code == 200
        payload = resp.json()["data"]
        assert payload["success"] is True


class TestDeleteAccount:
    """Integration tests for scoped account delete endpoints."""

    @pytest.mark.integration
    async def test_delete_account_success(self, client: AsyncClient) -> None:
        """DELETE /accounts/{id} must return 204 and the account must be gone.

        After a successful delete the subsequent GET for the same ID must
        return 404 confirming the row has been removed.
        """
        token = await _register_and_get_token(
            client, username="acc_deleter", email="deleter@example.com"
        )
        headers = _auth(token)
        portfolio_id = await _create_portfolio(
            client,
            token,
            name="Delete Portfolio",
        )

        create_resp = await client.post(
            _accounts_url(portfolio_id), json={"name": "Delete Me"}, headers=headers
        )
        account_id = create_resp.json()["data"]["id"]

        del_resp = await client.delete(
            f"{_accounts_url(portfolio_id)}/{account_id}", headers=headers
        )
        assert del_resp.status_code == 204

        # Confirm the account is truly gone
        get_resp = await client.get(
            f"{_accounts_url(portfolio_id)}/{account_id}", headers=headers
        )
        assert get_resp.status_code == 404

    @pytest.mark.integration
    async def test_delete_account_not_found_returns_404(
        self, client: AsyncClient
    ) -> None:
        """DELETE /accounts/{id} for an unknown UUID must return 404."""
        token = await _register_and_get_token(
            client, username="acc_del404", email="del404@example.com"
        )
        portfolio_id = await _create_portfolio(
            client,
            token,
            name="Delete 404 Portfolio",
        )
        unknown_id = uuid.uuid4()
        resp = await client.delete(
            f"{_accounts_url(portfolio_id)}/{unknown_id}", headers=_auth(token)
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Cross-user isolation tests
# ---------------------------------------------------------------------------


class TestAccountIsolation:
    """Integration tests verifying that accounts are isolated between users."""

    @pytest.mark.integration
    async def test_accounts_isolated_between_users(self, client: AsyncClient) -> None:
        """User A must receive 404 when requesting User B's account by ID.

        The account repository always filters by ``user_id`` so an account
        owned by user B must be invisible to user A — even if user A knows
        the exact UUID.
        """
        token_a = await _register_and_get_token(
            client, username="user_alpha", email="alpha@example.com"
        )
        token_b = await _register_and_get_token(
            client, username="user_beta", email="beta@example.com"
        )

        portfolio_a = await _create_portfolio(
            client,
            token_a,
            name="Alpha Portfolio",
        )
        portfolio_b = await _create_portfolio(
            client,
            token_b,
            name="Beta Portfolio",
        )

        # User B creates an account
        create_resp = await client.post(
            _accounts_url(portfolio_b),
            json={"name": "User B's Secret Account"},
            headers=_auth(token_b),
        )
        assert create_resp.status_code == 201
        b_account_id = create_resp.json()["data"]["id"]

        # User A tries to GET User B's account by UUID — must get 404
        resp_a = await client.get(
            f"{_accounts_url(portfolio_a)}/{b_account_id}",
            headers=_auth(token_a),
        )
        assert resp_a.status_code == 404

    @pytest.mark.integration
    async def test_list_accounts_shows_only_own_accounts(
        self, client: AsyncClient
    ) -> None:
        """GET /accounts must return only accounts owned by the requesting user.

        After user A and user B each create an account, user A's list must
        contain exactly one item (their own account) and not user B's.
        """
        token_a = await _register_and_get_token(
            client, username="user_gamma", email="gamma@example.com"
        )
        token_b = await _register_and_get_token(
            client, username="user_delta", email="delta@example.com"
        )

        portfolio_a = await _create_portfolio(
            client,
            token_a,
            name="Gamma Portfolio",
        )
        portfolio_b = await _create_portfolio(
            client,
            token_b,
            name="Delta Portfolio",
        )

        await client.post(
            _accounts_url(portfolio_a),
            json={"name": "Gamma's Account"},
            headers=_auth(token_a),
        )
        await client.post(
            _accounts_url(portfolio_b),
            json={"name": "Delta's Account"},
            headers=_auth(token_b),
        )

        resp = await client.get(_accounts_url(portfolio_a), headers=_auth(token_a))
        assert resp.status_code == 200

        items = resp.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["name"] == "Gamma's Account"
