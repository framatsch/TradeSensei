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

# ---------------------------------------------------------------------------
# URL constants
# ---------------------------------------------------------------------------

_REGISTER_URL = "/api/v1/auth/register"
_TOKEN_URL = "/api/v1/auth/token"
_ACCOUNTS_URL = "/api/v1/accounts"


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


_DEFAULT_ACCOUNT_PAYLOAD = {
    "name": "IBKR Main",
    "broker": "IBKR",
    "currency": "USD",
}


# ---------------------------------------------------------------------------
# CRUD tests
# ---------------------------------------------------------------------------


class TestCreateAccount:
    """Integration tests for ``POST /api/v1/accounts``."""

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
        resp = await client.post(
            _ACCOUNTS_URL,
            json=_DEFAULT_ACCOUNT_PAYLOAD,
            headers=_auth(token),
        )
        assert resp.status_code == 201

        account = resp.json()["data"]
        assert account["name"] == "IBKR Main"
        assert account["broker"] == "IBKR"
        assert account["currency"] == "USD"
        assert account["is_active"] is True
        assert "id" in account
        assert "user_id" in account
        # Ensure the UUID is valid
        uuid.UUID(account["id"])

    @pytest.mark.integration
    async def test_create_account_requires_auth(self, client: AsyncClient) -> None:
        """POST /accounts without a token must return 401."""
        resp = await client.post(_ACCOUNTS_URL, json=_DEFAULT_ACCOUNT_PAYLOAD)
        assert resp.status_code == 401

    @pytest.mark.integration
    async def test_create_account_missing_name_returns_422(
        self, client: AsyncClient
    ) -> None:
        """POST /accounts without the required ``name`` field must return 422."""
        token = await _register_and_get_token(
            client, username="acc_noname", email="noname@example.com"
        )
        resp = await client.post(
            _ACCOUNTS_URL,
            json={"broker": "IBKR", "currency": "USD"},  # missing name
            headers=_auth(token),
        )
        assert resp.status_code == 422


class TestListAccounts:
    """Integration tests for ``GET /api/v1/accounts``."""

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

        await client.post(_ACCOUNTS_URL, json={"name": "Account A"}, headers=headers)
        await client.post(_ACCOUNTS_URL, json={"name": "Account B"}, headers=headers)

        resp = await client.get(_ACCOUNTS_URL, headers=headers)
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
        resp = await client.get(_ACCOUNTS_URL, headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["data"]["items"] == []
        assert resp.json()["data"]["total"] == 0


class TestGetAccount:
    """Integration tests for ``GET /api/v1/accounts/{account_id}``."""

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

        create_resp = await client.post(
            _ACCOUNTS_URL, json={"name": "Fetch Me"}, headers=headers
        )
        account_id = create_resp.json()["data"]["id"]

        resp = await client.get(f"{_ACCOUNTS_URL}/{account_id}", headers=headers)
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
        unknown_id = uuid.uuid4()
        resp = await client.get(f"{_ACCOUNTS_URL}/{unknown_id}", headers=_auth(token))
        assert resp.status_code == 404


class TestUpdateAccount:
    """Integration tests for ``PATCH /api/v1/accounts/{account_id}``."""

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

        create_resp = await client.post(
            _ACCOUNTS_URL,
            json={"name": "Before Update", "broker": "IBKR", "currency": "USD"},
            headers=headers,
        )
        account_id = create_resp.json()["data"]["id"]

        resp = await client.patch(
            f"{_ACCOUNTS_URL}/{account_id}",
            json={"name": "After Update"},
            headers=headers,
        )
        assert resp.status_code == 200
        updated = resp.json()["data"]
        assert updated["name"] == "After Update"
        # Untouched fields must be unchanged
        assert updated["broker"] == "IBKR"
        assert updated["currency"] == "USD"

    @pytest.mark.integration
    async def test_update_account_not_found_returns_404(
        self, client: AsyncClient
    ) -> None:
        """PATCH /accounts/{id} for an unknown UUID must return 404."""
        token = await _register_and_get_token(
            client, username="acc_upd404", email="upd404@example.com"
        )
        unknown_id = uuid.uuid4()
        resp = await client.patch(
            f"{_ACCOUNTS_URL}/{unknown_id}",
            json={"name": "Ghost"},
            headers=_auth(token),
        )
        assert resp.status_code == 404


class TestDeleteAccount:
    """Integration tests for ``DELETE /api/v1/accounts/{account_id}``."""

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

        create_resp = await client.post(
            _ACCOUNTS_URL, json={"name": "Delete Me"}, headers=headers
        )
        account_id = create_resp.json()["data"]["id"]

        del_resp = await client.delete(f"{_ACCOUNTS_URL}/{account_id}", headers=headers)
        assert del_resp.status_code == 204

        # Confirm the account is truly gone
        get_resp = await client.get(f"{_ACCOUNTS_URL}/{account_id}", headers=headers)
        assert get_resp.status_code == 404

    @pytest.mark.integration
    async def test_delete_account_not_found_returns_404(
        self, client: AsyncClient
    ) -> None:
        """DELETE /accounts/{id} for an unknown UUID must return 404."""
        token = await _register_and_get_token(
            client, username="acc_del404", email="del404@example.com"
        )
        unknown_id = uuid.uuid4()
        resp = await client.delete(
            f"{_ACCOUNTS_URL}/{unknown_id}", headers=_auth(token)
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

        # User B creates an account
        create_resp = await client.post(
            _ACCOUNTS_URL,
            json={"name": "User B's Secret Account"},
            headers=_auth(token_b),
        )
        assert create_resp.status_code == 201
        b_account_id = create_resp.json()["data"]["id"]

        # User A tries to GET User B's account by UUID — must get 404
        resp_a = await client.get(
            f"{_ACCOUNTS_URL}/{b_account_id}",
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

        await client.post(
            _ACCOUNTS_URL,
            json={"name": "Gamma's Account"},
            headers=_auth(token_a),
        )
        await client.post(
            _ACCOUNTS_URL,
            json={"name": "Delta's Account"},
            headers=_auth(token_b),
        )

        resp = await client.get(_ACCOUNTS_URL, headers=_auth(token_a))
        assert resp.status_code == 200

        items = resp.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["name"] == "Gamma's Account"
