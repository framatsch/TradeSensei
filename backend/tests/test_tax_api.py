"""Integration tests for the /api/v1/tax endpoints.

These tests require a live database (TimescaleDB with migrations applied).
They use the ``client`` fixture from ``conftest.py`` which overrides the
``get_session`` dependency with a rolled-back transaction.

Test scenarios:
- Normal year with equity and derivative trades: summary values are correct.
- Empty year (no trades): all monetary values are 0 (HTTP 200, not 404).
- Category split: EQUITY trades go to equities block, others to derivatives.
- CSV download: content-type, content-disposition header, CSV content check.
- Unauthenticated: endpoints return HTTP 401 without a valid token.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient

_REGISTER_URL = "/api/v1/auth/register"
_TOKEN_URL = "/api/v1/auth/token"
_TAX_SUMMARY_URL = "/api/v1/tax/annual-summary"
_TAX_CSV_URL = "/api/v1/tax/annual-summary/csv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_and_token(client: AsyncClient, suffix: str = "") -> str:
    """Register a user and return an access token.

    Args:
        client: Test HTTP client.
        suffix: Optional suffix to make the username/email unique per test.

    Returns:
        The ``access_token`` string from the login response.
    """
    username = f"taxtest{suffix}"
    email = f"taxtest{suffix}@example.com"
    password = "S3cureP@ss99"

    reg = await client.post(
        _REGISTER_URL,
        json={"username": username, "email": email, "password": password},
    )
    assert reg.status_code == 201, reg.text

    login = await client.post(
        _TOKEN_URL,
        data={"username": username, "password": password},
    )
    assert login.status_code == 200, login.text
    token: str = login.json()["access_token"]
    return token


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_portfolio_and_account(
    client: AsyncClient,
    headers: dict[str, str],
    suffix: str,
) -> tuple[str, str]:
    """Create a portfolio and account for tax integration tests.

    Args:
        client: Test HTTP client.
        headers: Authorization headers.
        suffix: Unique suffix for resource names.

    Returns:
        Tuple of ``(portfolio_id, account_id)``.
    """
    p_resp = await client.post(
        "/api/v1/portfolios",
        json={"name": f"Tax Portfolio {suffix}", "base_currency": "USD"},
        headers=headers,
    )
    assert p_resp.status_code == 201, p_resp.text
    portfolio_id = str(p_resp.json()["data"]["id"])

    a_resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        json={"name": f"Tax Account {suffix}", "type": "manual", "currency": "USD"},
        headers=headers,
    )
    assert a_resp.status_code == 201, a_resp.text
    account_id = str(a_resp.json()["data"]["id"])
    return portfolio_id, account_id


def _trade_payload(**kwargs: object) -> dict[str, object]:
    """Build a minimal closed trade creation payload.

    Args:
        **kwargs: Field overrides applied on top of defaults.

    Returns:
        A dict suitable for ``POST /api/v1/trades``.
    """
    defaults: dict[str, object] = {
        "symbol": "AAPL",
        "direction": "LONG",
        "asset_class": "EQUITY",
        "quantity": "10.00000000",
        "entry_price": "150.00000000",
        "exit_price": "160.00000000",
        "opened_at": datetime(2025, 6, 1, 10, 0, tzinfo=UTC).isoformat(),
        "closed_at": datetime(2025, 6, 1, 15, 0, tzinfo=UTC).isoformat(),
        "pnl": "100.00000000",
    }
    defaults.update(kwargs)
    return defaults


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestTaxSummaryUnauthenticated:
    """The tax endpoints require a valid Bearer token."""

    async def test_summary_without_token_returns_401(self, client: AsyncClient) -> None:
        """GET /tax/annual-summary without auth returns HTTP 401."""
        response = await client.get(_TAX_SUMMARY_URL, params={"year": 2025})
        assert response.status_code == 401

    async def test_csv_without_token_returns_401(self, client: AsyncClient) -> None:
        """GET /tax/annual-summary/csv without auth returns HTTP 401."""
        response = await client.get(_TAX_CSV_URL, params={"year": 2025})
        assert response.status_code == 401


@pytest.mark.integration
class TestTaxSummaryEmptyYear:
    """When no trades exist for a year, all values are zero (not 404)."""

    async def test_empty_year_returns_200_with_zeros(self, client: AsyncClient) -> None:
        """Summary for a year with no trades returns HTTP 200 with all-zero values."""
        token = await _register_and_token(client, suffix="empty")
        response = await client.get(
            _TAX_SUMMARY_URL,
            params={"year": 2020},
            headers=_auth_headers(token),
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["year"] == 2020
        assert Decimal(data["equities"]["gains_eur"]) == Decimal("0")
        assert Decimal(data["equities"]["losses_eur"]) == Decimal("0")
        assert Decimal(data["equities"]["net_eur"]) == Decimal("0")
        assert data["equities"]["trade_count"] == 0
        assert Decimal(data["derivatives"]["gains_eur"]) == Decimal("0")
        assert Decimal(data["derivatives"]["losses_eur"]) == Decimal("0")
        assert Decimal(data["total_net_eur"]) == Decimal("0")


@pytest.mark.integration
class TestTaxSummaryWithTrades:
    """Annual summary correctly aggregates trades by §20 EStG category."""

    async def test_equity_trade_appears_in_equities_block(
        self, client: AsyncClient
    ) -> None:
        """An EQUITY trade with pnl_eur set appears in the equities block."""
        token = await _register_and_token(client, suffix="eq1")
        headers = _auth_headers(token)
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "eq1"
        )

        # Create an equity trade and manually set pnl_eur.
        payload = _trade_payload(
            symbol="AAPL",
            asset_class="EQUITY",
            pnl="100.00000000",
            pnl_eur="92.50000000",
        )
        create_resp = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json={**payload, "account_id": account_id},
            headers=headers,
        )
        assert create_resp.status_code == 201

        response = await client.get(
            _TAX_SUMMARY_URL,
            params={"year": 2025},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]

        # pnl_eur=92.50 is a gain → appears in equities.gains_eur.
        assert Decimal(data["equities"]["gains_eur"]) == Decimal("92.50")
        assert Decimal(data["equities"]["losses_eur"]) == Decimal("0")
        assert data["equities"]["trade_count"] == 1

        # No derivative trades.
        assert Decimal(data["derivatives"]["gains_eur"]) == Decimal("0")
        assert data["derivatives"]["trade_count"] == 0

        assert Decimal(data["total_net_eur"]) == Decimal("92.50")

    async def test_option_trade_appears_in_derivatives_block(
        self, client: AsyncClient
    ) -> None:
        """An OPTION trade with negative pnl_eur appears in derivatives.losses_eur."""
        token = await _register_and_token(client, suffix="opt1")
        headers = _auth_headers(token)
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "opt1"
        )

        payload = _trade_payload(
            symbol="AAPL250620C00200000",
            asset_class="OPTION",
            pnl="-200.00000000",
            pnl_eur="-185.00000000",
        )
        create_resp = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json={**payload, "account_id": account_id},
            headers=headers,
        )
        assert create_resp.status_code == 201

        response = await client.get(
            _TAX_SUMMARY_URL,
            params={"year": 2025},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]

        assert Decimal(data["equities"]["gains_eur"]) == Decimal("0")
        assert Decimal(data["derivatives"]["losses_eur"]) == Decimal("-185.00")
        assert Decimal(data["derivatives"]["net_eur"]) == Decimal("-185.00")
        assert data["derivatives"]["trade_count"] == 1
        assert Decimal(data["total_net_eur"]) == Decimal("-185.00")

    async def test_mixed_trades_correct_split(self, client: AsyncClient) -> None:
        """Equity gains and derivative losses are split correctly."""
        token = await _register_and_token(client, suffix="mixed1")
        headers = _auth_headers(token)
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "mixed1"
        )

        # Equity gain.
        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json=_trade_payload(
                account_id=account_id,
                symbol="AAPL",
                asset_class="EQUITY",
                pnl="500.00000000",
                pnl_eur="460.00000000",
            ),
            headers=headers,
        )
        # Derivative loss.
        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json=_trade_payload(
                account_id=account_id,
                symbol="SPX",
                asset_class="FUTURE",
                pnl="-300.00000000",
                pnl_eur="-276.00000000",
            ),
            headers=headers,
        )

        response = await client.get(
            _TAX_SUMMARY_URL,
            params={"year": 2025},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]

        assert Decimal(data["equities"]["gains_eur"]) == Decimal("460.00")
        assert Decimal(data["equities"]["net_eur"]) == Decimal("460.00")
        assert data["equities"]["trade_count"] == 1

        assert Decimal(data["derivatives"]["losses_eur"]) == Decimal("-276.00")
        assert Decimal(data["derivatives"]["net_eur"]) == Decimal("-276.00")
        assert data["derivatives"]["trade_count"] == 1

        assert Decimal(data["total_net_eur"]) == Decimal("184.00")

    async def test_trades_without_pnl_eur_counted_as_missing(
        self, client: AsyncClient
    ) -> None:
        """Closed trades with pnl_eur=NULL are counted in trades_missing_eur."""
        token = await _register_and_token(client, suffix="missing1")
        headers = _auth_headers(token)
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "missing1"
        )

        # Trade without pnl_eur (no EUR conversion done at import).
        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json=_trade_payload(
                account_id=account_id,
                symbol="TSLA",
                asset_class="EQUITY",
                pnl="200.00000000",
                # pnl_eur intentionally omitted
            ),
            headers=headers,
        )

        response = await client.get(
            _TAX_SUMMARY_URL,
            params={"year": 2025},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["trades_missing_eur"] >= 1

    async def test_year_filter_isolates_trades(self, client: AsyncClient) -> None:
        """Trades from a different year do not appear in the summary."""
        token = await _register_and_token(client, suffix="yearfilt")
        headers = _auth_headers(token)
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "yearfilt"
        )

        # Trade in 2024.
        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json=_trade_payload(
                account_id=account_id,
                opened_at=datetime(2024, 3, 1, 10, 0, tzinfo=UTC).isoformat(),
                closed_at=datetime(2024, 3, 1, 15, 0, tzinfo=UTC).isoformat(),
                pnl_eur="100.00000000",
            ),
            headers=headers,
        )

        # Query 2025 — should be empty.
        response = await client.get(
            _TAX_SUMMARY_URL,
            params={"year": 2025},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert Decimal(data["total_net_eur"]) == Decimal("0")
        assert data["equities"]["trade_count"] == 0


@pytest.mark.integration
class TestTaxCsvDownload:
    """CSV download endpoint returns a well-formed CSV file."""

    async def test_csv_content_type_and_disposition(self, client: AsyncClient) -> None:
        """CSV response has correct Content-Type and Content-Disposition headers."""
        token = await _register_and_token(client, suffix="csv1")
        headers = _auth_headers(token)

        response = await client.get(
            _TAX_CSV_URL,
            params={"year": 2025},
            headers=headers,
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert 'filename="steuer_2025.csv"' in response.headers["content-disposition"]

    async def test_csv_contains_header_row(self, client: AsyncClient) -> None:
        """CSV body contains the expected column header row."""
        token = await _register_and_token(client, suffix="csv2")
        headers = _auth_headers(token)

        response = await client.get(
            _TAX_CSV_URL,
            params={"year": 2025},
            headers=headers,
        )
        assert response.status_code == 200
        # Strip BOM if present.
        content = response.text.lstrip("\ufeff")
        # The CSV now has section headers (lines starting with ##).
        # Find the first data-header line (not a comment line).
        header_line = next(
            (
                line
                for line in content.splitlines()
                if not line.startswith("##") and line.strip()
            ),
            "",
        )
        assert "Symbol" in header_line
        assert "P&L (EUR)" in header_line

    async def test_csv_contains_trade_row(self, client: AsyncClient) -> None:
        """A trade created for the year appears as a data row in the CSV."""
        token = await _register_and_token(client, suffix="csv3")
        headers = _auth_headers(token)
        portfolio_id, account_id = await _create_portfolio_and_account(
            client, headers, "csv3"
        )

        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json=_trade_payload(
                account_id=account_id,
                symbol="MSFT",
                asset_class="EQUITY",
                pnl="250.00000000",
                pnl_eur="230.00000000",
            ),
            headers=headers,
        )

        response = await client.get(
            _TAX_CSV_URL,
            params={"year": 2025},
            headers=headers,
        )
        assert response.status_code == 200
        content = response.text.lstrip("\ufeff")
        assert "MSFT" in content
        assert "230" in content
