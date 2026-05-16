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

"""Integration tests for the modelbook PATCH endpoints.

Tests cover:
- PATCH /api/v1/trades/{trade_id}/modelbook
- PATCH /api/v1/checkins/{checkin_date}/modelbook
"""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

_REGISTER_URL = "/api/v1/auth/register"
_TOKEN_URL = "/api/v1/auth/token"


async def _get_auth_headers(client: AsyncClient, suffix: str = "") -> dict[str, str]:
    uid = uuid.uuid4().hex[:8] + suffix
    reg = await client.post(
        _REGISTER_URL,
        json={
            "username": f"mb_{uid}",
            "email": f"mb_{uid}@example.com",
            "password": "ModelBook@99",
        },
    )
    assert reg.status_code == 201, reg.text
    login = await client.post(
        _TOKEN_URL,
        data={"username": f"mb_{uid}", "password": "ModelBook@99"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _create_portfolio_and_account(
    client: AsyncClient, headers: dict[str, str], suffix: str
) -> tuple[str, str]:
    p = await client.post(
        "/api/v1/portfolios",
        json={"name": f"MB Portfolio {suffix}", "base_currency": "USD"},
        headers=headers,
    )
    assert p.status_code == 201, p.text
    portfolio_id = p.json()["data"]["id"]

    a = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        json={"name": f"MB Account {suffix}", "type": "manual", "currency": "USD"},
        headers=headers,
    )
    assert a.status_code == 201, a.text
    return portfolio_id, a.json()["data"]["id"]


async def _create_trade(
    client: AsyncClient, headers: dict[str, str], portfolio_id: str, account_id: str
) -> str:
    resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        json={
            "account_id": account_id,
            "symbol": "AAPL",
            "direction": "LONG",
            "asset_class": "EQUITY",
            "quantity": "10",
            "entry_price": "150",
            "opened_at": datetime(2025, 1, 15, 10, 0, tzinfo=UTC).isoformat(),
            "currency": "USD",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


def _trade_modelbook_url(portfolio_id: str, trade_id: str) -> str:
    return f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}/modelbook"


async def _create_checkin(
    client: AsyncClient, headers: dict[str, str], checkin_date: str = "2025-01-15"
) -> None:
    resp = await client.post(
        "/api/v1/checkins",
        json={"date": checkin_date, "notes": "test checkin"},
        headers=headers,
    )
    assert resp.status_code in (201, 200), resp.text


@pytest.mark.integration
class TestTradeModelbook:
    """Tests for PATCH /api/v1/portfolios/{portfolio_id}/trades/{trade_id}/modelbook."""

    async def test_star_trade_returns_200_and_true(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client, "star")
        portfolio_id, account_id = await _create_portfolio_and_account(client, headers, "star")
        trade_id = await _create_trade(client, headers, portfolio_id, account_id)

        resp = await client.patch(
            _trade_modelbook_url(portfolio_id, trade_id),
            json={"is_modelbook": True},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["is_modelbook"] is True

    async def test_unstar_trade_returns_200_and_false(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client, "unstar")
        portfolio_id, account_id = await _create_portfolio_and_account(client, headers, "unstar")
        trade_id = await _create_trade(client, headers, portfolio_id, account_id)

        # Star first
        await client.patch(
            _trade_modelbook_url(portfolio_id, trade_id),
            json={"is_modelbook": True},
            headers=headers,
        )

        resp = await client.patch(
            _trade_modelbook_url(portfolio_id, trade_id),
            json={"is_modelbook": False},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["is_modelbook"] is False

    async def test_star_trade_idempotent(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client, "idem")
        portfolio_id, account_id = await _create_portfolio_and_account(client, headers, "idem")
        trade_id = await _create_trade(client, headers, portfolio_id, account_id)

        await client.patch(
            _trade_modelbook_url(portfolio_id, trade_id),
            json={"is_modelbook": True},
            headers=headers,
        )
        resp = await client.patch(
            _trade_modelbook_url(portfolio_id, trade_id),
            json={"is_modelbook": True},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["is_modelbook"] is True

    async def test_trade_owned_by_other_user_returns_404(
        self, client: AsyncClient, other_users_trade: dict
    ) -> None:
        headers = await _get_auth_headers(client, "xown")
        trade_id = other_users_trade["id"]
        portfolio_id = other_users_trade["portfolio_id"]

        resp = await client.patch(
            _trade_modelbook_url(portfolio_id, trade_id),
            json={"is_modelbook": True},
            headers=headers,
        )
        assert resp.status_code == 404


@pytest.mark.integration
class TestCheckinModelbook:
    """Tests for PATCH /api/v1/checkins/{checkin_date}/modelbook."""

    async def test_star_checkin_returns_200_and_true(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client, "cstar")
        checkin_date = "2025-02-10"
        await _create_checkin(client, headers, checkin_date)

        resp = await client.patch(
            f"/api/v1/checkins/{checkin_date}/modelbook",
            json={"is_modelbook": True},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["is_modelbook"] is True

    async def test_unstar_checkin_returns_200_and_false(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client, "cunstar")
        checkin_date = "2025-02-11"
        await _create_checkin(client, headers, checkin_date)

        await client.patch(
            f"/api/v1/checkins/{checkin_date}/modelbook",
            json={"is_modelbook": True},
            headers=headers,
        )
        resp = await client.patch(
            f"/api/v1/checkins/{checkin_date}/modelbook",
            json={"is_modelbook": False},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["is_modelbook"] is False

    async def test_checkin_owned_by_other_user_returns_404(
        self, client: AsyncClient, other_user: dict
    ) -> None:
        # Create a checkin for other_user
        checkin_date = "2025-03-01"
        await client.post(
            "/api/v1/checkins",
            json={"date": checkin_date, "notes": "other user checkin"},
            headers=other_user["headers"],
        )

        # Try to star it as a different user
        headers = await _get_auth_headers(client, "cxown")
        resp = await client.patch(
            f"/api/v1/checkins/{checkin_date}/modelbook",
            json={"is_modelbook": True},
            headers=headers,
        )
        assert resp.status_code == 404
