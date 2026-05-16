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

"""Integration tests for the metadata correlation endpoint.

Tests cover:
- GET /api/v1/portfolios/{portfolio_id}/analytics/metadata-correlation
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
            "username": f"mc_{uid}",
            "email": f"mc_{uid}@example.com",
            "password": "MetaCorr@99",
        },
    )
    assert reg.status_code == 201, reg.text
    login = await client.post(
        _TOKEN_URL,
        data={"username": f"mc_{uid}", "password": "MetaCorr@99"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _create_portfolio_and_account(
    client: AsyncClient, headers: dict[str, str], suffix: str
) -> tuple[str, str]:
    p = await client.post(
        "/api/v1/portfolios",
        json={"name": f"MC Portfolio {suffix}", "base_currency": "USD"},
        headers=headers,
    )
    assert p.status_code == 201, p.text
    portfolio_id = p.json()["data"]["id"]

    a = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        json={"name": f"MC Account {suffix}", "type": "manual", "currency": "USD"},
        headers=headers,
    )
    assert a.status_code == 201, a.text
    return portfolio_id, a.json()["data"]["id"]


async def _create_annotation_def(
    client: AsyncClient, headers: dict[str, str], scope: str = "checkins", suffix: str = ""
) -> str:
    resp = await client.post(
        "/api/v1/annotation-definitions",
        json={
            "name": f"Ann {scope} {suffix}",
            "type": "int",
            "scope": scope,
            "scale_labels": {"min": 1, "max": 10},
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


def _correlation_url(portfolio_id: str) -> str:
    return f"/api/v1/portfolios/{portfolio_id}/analytics/metadata-correlation"


@pytest.mark.integration
class TestMetadataCorrelationEndpoint:
    """Tests for GET /api/v1/portfolios/{portfolio_id}/analytics/metadata-correlation."""

    async def test_empty_portfolio_returns_empty_data_points(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client, "empty")
        portfolio_id, _ = await _create_portfolio_and_account(client, headers, "empty")
        x_id = await _create_annotation_def(client, headers, scope="checkins", suffix="empty_x")
        y_id = await _create_annotation_def(client, headers, scope="trades", suffix="empty_y")

        resp = await client.get(
            _correlation_url(portfolio_id),
            params={
                "x_axis_type": "checkin_annotation",
                "x_axis_id": x_id,
                "y_axis_type": "trade_annotation",
                "y_axis_id": y_id,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["data_points"] == []

    async def test_trades_no_matching_checkins_returns_empty_data_points(
        self, client: AsyncClient
    ) -> None:
        headers = await _get_auth_headers(client, "nomatch")
        portfolio_id, account_id = await _create_portfolio_and_account(client, headers, "nomatch")
        x_id = await _create_annotation_def(client, headers, scope="checkins", suffix="nm_x")
        y_id = await _create_annotation_def(client, headers, scope="trades", suffix="nm_y")

        # Create a trade but no checkin on same date
        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json={
                "account_id": account_id,
                "symbol": "AAPL",
                "direction": "LONG",
                "asset_class": "EQUITY",
                "quantity": "10",
                "entry_price": "150",
                "opened_at": datetime(2025, 3, 1, 10, 0, tzinfo=UTC).isoformat(),
                "currency": "USD",
            },
            headers=headers,
        )

        resp = await client.get(
            _correlation_url(portfolio_id),
            params={
                "x_axis_type": "checkin_annotation",
                "x_axis_id": x_id,
                "y_axis_type": "trade_annotation",
                "y_axis_id": y_id,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["data_points"] == []

    async def test_kpis_total_trades_count_reflects_closed_trades(
        self, client: AsyncClient
    ) -> None:
        headers = await _get_auth_headers(client, "kpi")
        portfolio_id, account_id = await _create_portfolio_and_account(client, headers, "kpi")
        x_id = await _create_annotation_def(client, headers, scope="checkins", suffix="kpi_x")
        y_id = await _create_annotation_def(client, headers, scope="trades", suffix="kpi_y")

        # Create a closed trade
        trade_resp = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json={
                "account_id": account_id,
                "symbol": "TSLA",
                "direction": "LONG",
                "asset_class": "EQUITY",
                "quantity": "5",
                "entry_price": "200",
                "opened_at": datetime(2025, 4, 1, 10, 0, tzinfo=UTC).isoformat(),
                "closed_at": datetime(2025, 4, 1, 15, 0, tzinfo=UTC).isoformat(),
                "exit_price": "210",
                "currency": "USD",
            },
            headers=headers,
        )
        assert trade_resp.status_code == 201, trade_resp.text

        resp = await client.get(
            _correlation_url(portfolio_id),
            params={
                "x_axis_type": "checkin_annotation",
                "x_axis_id": x_id,
                "y_axis_type": "trade_annotation",
                "y_axis_id": y_id,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        kpis = resp.json()["data"]["kpis"]
        # KPIs are present in the response; total_trades_count counts trades with pnl set
        assert "total_trades_count" in kpis
        assert "matched_count" in kpis
        assert "win_rate" in kpis

    async def test_kpis_matched_count_zero_when_no_pairs(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client, "mc0")
        portfolio_id, _ = await _create_portfolio_and_account(client, headers, "mc0")
        x_id = await _create_annotation_def(client, headers, scope="checkins", suffix="mc0_x")
        y_id = await _create_annotation_def(client, headers, scope="trades", suffix="mc0_y")

        resp = await client.get(
            _correlation_url(portfolio_id),
            params={
                "x_axis_type": "checkin_annotation",
                "x_axis_id": x_id,
                "y_axis_type": "trade_annotation",
                "y_axis_id": y_id,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["kpis"]["matched_count"] == 0

    async def test_x_axis_scope_mismatch_returns_422(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client, "mism")
        portfolio_id, _ = await _create_portfolio_and_account(client, headers, "mism")
        # Create a trades-scoped annotation but use it as checkin_annotation
        x_id = await _create_annotation_def(client, headers, scope="trades", suffix="mism_x")
        y_id = await _create_annotation_def(client, headers, scope="trades", suffix="mism_y")

        resp = await client.get(
            _correlation_url(portfolio_id),
            params={
                "x_axis_type": "checkin_annotation",  # mismatch: annotation is trades-scoped
                "x_axis_id": x_id,
                "y_axis_type": "trade_annotation",
                "y_axis_id": y_id,
            },
            headers=headers,
        )
        assert resp.status_code == 422

    async def test_same_axis_id_and_type_returns_422(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client, "same")
        portfolio_id, _ = await _create_portfolio_and_account(client, headers, "same")
        x_id = await _create_annotation_def(client, headers, scope="checkins", suffix="same_x")

        resp = await client.get(
            _correlation_url(portfolio_id),
            params={
                "x_axis_type": "checkin_annotation",
                "x_axis_id": x_id,
                "y_axis_type": "checkin_annotation",
                "y_axis_id": x_id,
            },
            headers=headers,
        )
        assert resp.status_code == 422

    async def test_unknown_x_axis_id_returns_404(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client, "unk")
        portfolio_id, _ = await _create_portfolio_and_account(client, headers, "unk")
        fake_id = str(uuid.uuid4())
        y_id = await _create_annotation_def(client, headers, scope="trades", suffix="unk_y")

        resp = await client.get(
            _correlation_url(portfolio_id),
            params={
                "x_axis_type": "checkin_annotation",
                "x_axis_id": fake_id,
                "y_axis_type": "trade_annotation",
                "y_axis_id": y_id,
            },
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_missing_portfolio_id_returns_422(self, client: AsyncClient) -> None:
        headers = await _get_auth_headers(client, "nopf")
        x_id = await _create_annotation_def(client, headers, scope="checkins", suffix="nopf_x")
        y_id = await _create_annotation_def(client, headers, scope="trades", suffix="nopf_y")

        # portfolio_id is part of the path — omitting it means hitting a different route
        resp = await client.get(
            "/api/v1/portfolios/not-a-uuid/analytics/metadata-correlation",
            params={
                "x_axis_type": "checkin_annotation",
                "x_axis_id": x_id,
                "y_axis_type": "trade_annotation",
                "y_axis_id": y_id,
            },
            headers=headers,
        )
        assert resp.status_code == 422
