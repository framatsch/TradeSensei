"""Integration tests for GET /api/v1/timeseries/monthly-winrate.

Requires a live database (TimescaleDB with migrations applied).
Uses the ``client`` fixture from ``conftest.py``.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient

_REGISTER_URL = "/api/v1/auth/register"
_TOKEN_URL = "/api/v1/auth/token"


async def _get_auth_headers(client: AsyncClient, suffix: str = "") -> dict[str, str]:
    """Register a throwaway user and return Bearer auth headers.

    Args:
        client: The HTTPX test client.
        suffix: Optional suffix to make the username unique across test classes.

    Returns:
        A dict with the ``Authorization: Bearer …`` header.
    """
    import uuid

    uid = uuid.uuid4().hex[:8] + suffix
    reg = await client.post(
        _REGISTER_URL,
        json={
            "username": f"mwr_{uid}",
            "email": f"mwr_{uid}@example.com",
            "password": "MwrTest@99",
        },
    )
    assert reg.status_code == 201, f"Register failed: {reg.text}"
    login = await client.post(
        _TOKEN_URL,
        data={"username": f"mwr_{uid}", "password": "MwrTest@99"},
    )
    assert login.status_code == 200, f"Login failed: {login.text}"
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_portfolio_and_account(
    client: AsyncClient,
    headers: dict[str, str],
    suffix: str,
) -> tuple[str, str]:
    """Create a portfolio and account for monthly win-rate tests.

    Args:
        client: The HTTPX test client.
        headers: Auth headers.
        suffix: Unique suffix for resource names.

    Returns:
        Tuple of ``(portfolio_id, account_id)``.
    """
    p_resp = await client.post(
        "/api/v1/portfolios",
        json={"name": f"MWR Portfolio {suffix}", "base_currency": "USD"},
        headers=headers,
    )
    assert p_resp.status_code == 201, p_resp.text
    portfolio_id = str(p_resp.json()["data"]["id"])

    a_resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        json={"name": f"MWR Account {suffix}", "type": "manual", "currency": "USD"},
        headers=headers,
    )
    assert a_resp.status_code == 201, a_resp.text
    account_id = str(a_resp.json()["data"]["id"])
    return portfolio_id, account_id


def _trade_payload(
    account_id: str,
    symbol: str = "AAPL",
    pnl: str | None = "100.00",
    closed_at: str | None = None,
    opened_at: str | None = None,
) -> dict[str, object]:
    """Build a minimal trade creation payload with optional PnL and closed_at.

    Args:
        symbol: Ticker symbol.
        pnl: Realised PnL string; ``None`` for an open trade.
        closed_at: ISO-8601 close timestamp.
        opened_at: ISO-8601 open timestamp.

    Returns:
        A dict suitable for ``POST /api/v1/trades``.
    """
    base: dict[str, object] = {
        "account_id": account_id,
        "symbol": symbol,
        "direction": "LONG",
        "asset_class": "EQUITY",
        "quantity": "10.00000000",
        "entry_price": "150.00000000",
        "opened_at": opened_at or datetime(2024, 5, 10, 10, 0, tzinfo=UTC).isoformat(),
    }
    if pnl is not None:
        base["pnl"] = pnl
    if closed_at is not None:
        base["closed_at"] = closed_at
    return base


@pytest.mark.integration
class TestMonthlyWinrateUnauthenticated:
    """Unauthenticated requests must return 401."""

    async def test_returns_401_without_token(self, client: AsyncClient) -> None:
        """GET /timeseries/monthly-winrate without auth should return 401."""
        response = await client.get(
            "/api/v1/portfolios/00000000-0000-0000-0000-000000000000/timeseries/monthly-winrate"
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestMonthlyWinrateEmpty:
    """Empty data set should return an empty list."""

    async def test_returns_empty_list_for_new_user(self, client: AsyncClient) -> None:
        """A user with no closed trades should receive an empty list."""
        headers = await _get_auth_headers(client, "empty")
        portfolio_id, _ = await _create_portfolio_and_account(client, headers, "empty")
        response = await client.get(
            f"/api/v1/portfolios/{portfolio_id}/timeseries/monthly-winrate",
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert body["data"] == []


@pytest.mark.integration
class TestMonthlyWinrateShape:
    """Monthly win-rate endpoint should return correct schema and values."""

    async def test_correct_shape_and_win_loss_counts(self, client: AsyncClient) -> None:
        """Endpoint should return correct win/loss counts and win_rate per month."""
        headers = await _get_auth_headers(client, "shape")
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "shape"
        )

        # Two wins and one loss in May 2024
        may_open = datetime(2024, 5, 1, 10, 0, tzinfo=UTC).isoformat()
        may_close = datetime(2024, 5, 15, 10, 0, tzinfo=UTC).isoformat()
        may_loss_close = datetime(2024, 5, 20, 10, 0, tzinfo=UTC).isoformat()

        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json=_trade_payload(
                account_id=account_id,
                pnl="200.00",
                opened_at=may_open,
                closed_at=may_close,
            ),
            headers=headers,
        )
        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json=_trade_payload(
                account_id=account_id,
                pnl="150.00",
                opened_at=may_open,
                closed_at=may_close,
            ),
            headers=headers,
        )
        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json=_trade_payload(
                account_id=account_id,
                pnl="-50.00", opened_at=may_open, closed_at=may_loss_close
            ),
            headers=headers,
        )

        response = await client.get(
            f"/api/v1/portfolios/{portfolio_id}/timeseries/monthly-winrate",
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        points = body["data"]
        assert len(points) >= 1

        may_point = next(
            (p for p in points if p["year"] == 2024 and p["month"] == 5), None
        )
        assert may_point is not None, "Expected a May 2024 data point"

        assert may_point["win_count"] == 2
        assert may_point["loss_count"] == 1
        assert may_point["trade_count"] == 3
        assert abs(Decimal(may_point["win_rate"]) - Decimal("0.6667")) < Decimal(
            "0.001"
        )
        assert may_point["label"] == "May 2024"

    async def test_two_months_ordered_chronologically(
        self, client: AsyncClient
    ) -> None:
        """Data points should be ordered by year/month ascending."""
        headers = await _get_auth_headers(client, "chron")
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "chron"
        )

        # One trade in March, one in June (different year)
        for opened_at, closed_at, pnl in [
            (
                datetime(2024, 3, 5, 10, 0, tzinfo=UTC).isoformat(),
                datetime(2024, 3, 10, 10, 0, tzinfo=UTC).isoformat(),
                "50.00",
            ),
            (
                datetime(2024, 6, 5, 10, 0, tzinfo=UTC).isoformat(),
                datetime(2024, 6, 10, 10, 0, tzinfo=UTC).isoformat(),
                "-30.00",
            ),
        ]:
            await client.post(
                f"/api/v1/portfolios/{portfolio_id}/trades",
                json=_trade_payload(
                    account_id=account_id,
                    pnl=pnl,
                    opened_at=opened_at,
                    closed_at=closed_at,
                ),
                headers=headers,
            )

        response = await client.get(
            f"/api/v1/portfolios/{portfolio_id}/timeseries/monthly-winrate",
            headers=headers,
        )
        assert response.status_code == 200
        points = response.json()["data"]
        assert len(points) == 2

        # Must be chronological: March before June
        assert (points[0]["year"], points[0]["month"]) == (2024, 3)
        assert (points[1]["year"], points[1]["month"]) == (2024, 6)

        # March: 1 win, 0 loss → win_rate = 1.0
        assert points[0]["win_count"] == 1
        assert points[0]["loss_count"] == 0
        assert Decimal(points[0]["win_rate"]) == Decimal("1")

        # June: 0 win, 1 loss → win_rate = 0.0
        assert points[1]["win_count"] == 0
        assert points[1]["loss_count"] == 1
        assert Decimal(points[1]["win_rate"]) == Decimal("0")

    async def test_open_trades_excluded(self, client: AsyncClient) -> None:
        """Trades without pnl or closed_at should be excluded from the series."""
        headers = await _get_auth_headers(client, "open")
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "open"
        )

        # One closed trade
        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json=_trade_payload(
                account_id=account_id,
                pnl="100.00",
                opened_at=datetime(2024, 7, 1, 10, 0, tzinfo=UTC).isoformat(),
                closed_at=datetime(2024, 7, 5, 10, 0, tzinfo=UTC).isoformat(),
            ),
            headers=headers,
        )
        # One open trade (no pnl, no closed_at)
        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json=_trade_payload(account_id=account_id, pnl=None),
            headers=headers,
        )

        response = await client.get(
            f"/api/v1/portfolios/{portfolio_id}/timeseries/monthly-winrate",
            headers=headers,
        )
        assert response.status_code == 200
        points = response.json()["data"]
        # Only the closed trade counts — should have exactly 1 month point
        assert len(points) == 1
        assert points[0]["trade_count"] == 1
