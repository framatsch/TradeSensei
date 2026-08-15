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

"""Integration tests for filter and sort on GET /api/v1/trades.

Covers TradeFilterParams (symbol, direction, asset_class, pnl_positive,
opened_at_from/to, playbook_id, tag_ids) and TradeSortParams (sort_by,
sort_dir) as wired in the list_trades route handler.
"""

from datetime import UTC, datetime
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


_REGISTER_URL = "/api/v1/auth/register"
_TOKEN_URL = "/api/v1/auth/token"


async def _get_auth_headers(client: AsyncClient) -> dict[str, str]:
    """Register a throwaway user and return Bearer auth headers.

    Args:
        client: The HTTPX test client.

    Returns:
        A dict with the ``Authorization: Bearer …`` header.
    """
    import uuid

    uid = uuid.uuid4().hex[:8]
    reg = await client.post(
        _REGISTER_URL,
        json={
            "username": f"filt_{uid}",
            "email": f"filt_{uid}@example.com",
            "password": "FiltTest@99",
        },
    )
    assert reg.status_code == 201, reg.text
    login = await client.post(
        _TOKEN_URL,
        data={"username": f"filt_{uid}", "password": "FiltTest@99"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _create_portfolio_and_account(
    client: AsyncClient,
    headers: dict[str, str],
) -> tuple[str, str]:
    """Create a portfolio and account for filter/sort tests.

    Args:
        client: The HTTPX test client.
        headers: Auth headers.

    Returns:
        Tuple of ``(portfolio_id, account_id)``.
    """
    portfolio_resp = await client.post(
        "/api/v1/portfolios",
        json={"name": "Filter Sort Portfolio", "base_currency": "USD"},
        headers=headers,
    )
    assert portfolio_resp.status_code == 201, portfolio_resp.text
    portfolio_id = str(portfolio_resp.json()["data"]["id"])

    account_resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        json={"name": "Filter Sort Account", "type": "manual", "currency": "USD"},
        headers=headers,
    )
    assert account_resp.status_code == 201, account_resp.text
    account_id = str(account_resp.json()["data"]["id"])
    return portfolio_id, account_id


def _make_trade(
    symbol: str = "AAPL",
    direction: str = "LONG",
    asset_class: str = "EQUITY",
    pnl: str | None = None,
    opened_at: str | None = None,
    **kwargs: object,
) -> dict[str, object]:
    """Build a minimal trade payload.

    Args:
        symbol: Ticker symbol.
        direction: LONG or SHORT.
        asset_class: Asset class string.
        pnl: Optional PnL value.
        opened_at: Optional ISO-8601 opened_at (defaults to 2025-01-15).
        **kwargs: Additional field overrides.

    Returns:
        A dict suitable for ``POST /api/v1/trades``.
    """
    payload: dict[str, object] = {
        "symbol": symbol,
        "direction": direction,
        "asset_class": asset_class,
        "quantity": "10.00000000",
        "entry_price": "100.00000000",
        "opened_at": opened_at or datetime(2025, 1, 15, 10, 0, tzinfo=UTC).isoformat(),
    }
    if pnl is not None:
        payload["pnl"] = pnl
        payload["exit_price"] = "110.00000000"
        opened = datetime.fromisoformat((opened_at or datetime(2025, 1, 15, 10, 0, tzinfo=UTC).isoformat()).replace("Z", "+00:00"))
        payload["closed_at"] = opened.replace(hour=min(opened.hour + 1, 23)).isoformat()
    payload.update(kwargs)
    return payload


async def _post_trade(
    client: AsyncClient,
    headers: dict[str, str],
    portfolio_id: str,
    account_id: str,
    **kwargs: object,
) -> dict[str, object]:
    """Post a trade and return the response data dict.

    Args:
        client: The HTTPX test client.
        headers: Auth headers.
        **kwargs: Passed to :func:`_make_trade`.

    Returns:
        The ``data`` portion of the response envelope.
    """
    resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        json=_make_trade(account_id=account_id, **kwargs),
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return dict(resp.json()["data"])


async def _list_trades(
    client: AsyncClient,
    headers: dict[str, str],
    portfolio_id: str,
    **params: object,
) -> list[dict[str, object]]:
    """Call GET /api/v1/trades and return the items list.

    Args:
        client: The HTTPX test client.
        headers: Auth headers.
        **params: Query parameters to pass.

    Returns:
        The ``items`` list from the cursor page.
    """
    resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades", headers=headers, params=params
    )
    assert resp.status_code == 200, resp.text
    return list(resp.json()["data"]["items"])


@pytest.mark.integration
class TestTradeFilterSymbol:
    """Tests for symbol filter on ``GET /api/v1/trades``."""

    async def test_filter_by_symbol_exact(self, client: AsyncClient) -> None:
        """symbols filter should return only trades with matching symbol."""
        h = await _get_auth_headers(client)
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)
        await _post_trade(client, h, portfolio_id, account_id, symbol="AAPL")
        await _post_trade(client, h, portfolio_id, account_id, symbol="GOOG")

        items = await _list_trades(client, h, portfolio_id, symbols=["AAPL"])
        assert all(t["symbol"] == "AAPL" for t in items)
        assert len(items) >= 1

    async def test_filter_by_symbol_case_insensitive(self, client: AsyncClient) -> None:
        """symbols filter should be case-insensitive."""
        h = await _get_auth_headers(client)
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)
        await _post_trade(client, h, portfolio_id, account_id, symbol="MSFT")

        items = await _list_trades(client, h, portfolio_id, symbols=["msft"])
        assert any(t["symbol"] == "MSFT" for t in items)

    async def test_filter_by_symbol_partial_match(self, client: AsyncClient) -> None:
        """symbols filter should support partial match (ILIKE %value%)."""
        h = await _get_auth_headers(client)
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)
        await _post_trade(client, h, portfolio_id, account_id, symbol="NVDA")
        await _post_trade(client, h, portfolio_id, account_id, symbol="NVDX")

        items = await _list_trades(client, h, portfolio_id, symbols=["NVD"])
        assert len(items) >= 2
        symbols = [t["symbol"] for t in items]
        assert "NVDA" in symbols
        assert "NVDX" in symbols


@pytest.mark.integration
class TestTradeFilterAccounts:
    """Tests for account filter on ``GET /api/v1/trades``."""

    async def test_filter_by_multiple_accounts(self, client: AsyncClient) -> None:
        """account_ids should return trades from any selected account."""
        h = await _get_auth_headers(client)
        portfolio_id, account_1 = await _create_portfolio_and_account(client, h)

        account_resp = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/accounts",
            json={"name": "Filter Sort Account 2", "type": "manual", "currency": "USD"},
            headers=h,
        )
        assert account_resp.status_code == 201, account_resp.text
        account_2 = str(account_resp.json()["data"]["id"])

        await _post_trade(client, h, portfolio_id, account_1, symbol="ACC1")
        await _post_trade(client, h, portfolio_id, account_2, symbol="ACC2")

        resp = await client.get(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            headers=h,
            params=[("account_ids", account_1), ("account_ids", account_2)],
        )
        assert resp.status_code == 200, resp.text
        items = list(resp.json()["data"]["items"])
        symbols = {trade["symbol"] for trade in items}
        assert {"ACC1", "ACC2"}.issubset(symbols)


@pytest.mark.integration
class TestTradeFilterDirection:
    """Tests for direction filter on ``GET /api/v1/trades``."""

    async def test_filter_long_only(self, client: AsyncClient) -> None:
        """direction=LONG should exclude SHORT trades."""
        h = await _get_auth_headers(client)
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)
        await _post_trade(
            client, h, portfolio_id, account_id, symbol="SPY", direction="LONG"
        )
        await _post_trade(
            client, h, portfolio_id, account_id, symbol="SPY", direction="SHORT"
        )

        items = await _list_trades(
            client, h, portfolio_id, symbols=["SPY"], direction="LONG"
        )
        assert all(t["direction"] == "LONG" for t in items)

    async def test_filter_short_only(self, client: AsyncClient) -> None:
        """direction=SHORT should exclude LONG trades."""
        h = await _get_auth_headers(client)
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)
        await _post_trade(
            client, h, portfolio_id, account_id, symbol="QQQ", direction="LONG"
        )
        await _post_trade(
            client, h, portfolio_id, account_id, symbol="QQQ", direction="SHORT"
        )

        items = await _list_trades(
            client, h, portfolio_id, symbols=["QQQ"], direction="SHORT"
        )
        assert all(t["direction"] == "SHORT" for t in items)


@pytest.mark.integration
class TestTradeFilterAssetClass:
    """Tests for asset_class filter on ``GET /api/v1/trades``."""

    async def test_filter_equity_only(self, client: AsyncClient) -> None:
        """asset_classes=EQUITY should exclude non-equity trades."""
        h = await _get_auth_headers(client)
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)
        await _post_trade(
            client, h, portfolio_id, account_id, symbol="EQF1", asset_class="EQUITY"
        )
        await _post_trade(
            client, h, portfolio_id, account_id, symbol="EQF1", asset_class="OPTION"
        )

        items = await _list_trades(
            client, h, portfolio_id, symbols=["EQF1"], asset_classes=["EQUITY"]
        )
        assert all(t["asset_class"] == "EQUITY" for t in items)


@pytest.mark.integration
class TestTradeFilterPnl:
    """Tests for pnl_positive filter on ``GET /api/v1/trades``."""

    async def test_filter_winners_only(self, client: AsyncClient) -> None:
        """pnl_positive=true should return only winning trades."""
        h = await _get_auth_headers(client)
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)
        await _post_trade(client, h, portfolio_id, account_id, symbol="WIN1", pnl="100.00")
        await _post_trade(client, h, portfolio_id, account_id, symbol="WIN1", pnl="-50.00")

        items = await _list_trades(
            client, h, portfolio_id, symbols=["WIN1"], pnl_positive="true"
        )
        assert all(float(t["pnl"]) > 0 for t in items if t["pnl"] is not None)

    async def test_filter_losers_only(self, client: AsyncClient) -> None:
        """pnl_positive=false should return only losing trades."""
        h = await _get_auth_headers(client)
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)
        await _post_trade(client, h, portfolio_id, account_id, symbol="LOSE1", pnl="200.00")
        await _post_trade(client, h, portfolio_id, account_id, symbol="LOSE1", pnl="-75.00")

        items = await _list_trades(
            client, h, portfolio_id, symbols=["LOSE1"], pnl_positive="false"
        )
        pnl_values = [float(t["pnl"]) for t in items if t["pnl"] is not None]
        assert all(v <= 0 for v in pnl_values)


@pytest.mark.integration
class TestTradeFilterDateRange:
    """Tests for opened_at_from / opened_at_to filter on ``GET /api/v1/trades``."""

    async def test_filter_from_date(self, client: AsyncClient) -> None:
        """opened_at_from should exclude trades opened before that date."""
        h = await _get_auth_headers(client)
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)
        early = datetime(2024, 1, 5, 10, 0, tzinfo=UTC).isoformat()
        late = datetime(2025, 6, 1, 10, 0, tzinfo=UTC).isoformat()
        await _post_trade(client, h, portfolio_id, account_id, symbol="DT1", opened_at=early)
        await _post_trade(client, h, portfolio_id, account_id, symbol="DT1", opened_at=late)

        cutoff = datetime(2025, 1, 1, tzinfo=UTC).isoformat()
        items = await _list_trades(
            client, h, portfolio_id, symbols=["DT1"], opened_at_from=cutoff
        )
        opened_dates = [t["opened_at"] for t in items]
        assert all(d >= cutoff for d in opened_dates)

    async def test_filter_to_date(self, client: AsyncClient) -> None:
        """opened_at_to should exclude trades opened after that date."""
        h = await _get_auth_headers(client)
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)
        early = datetime(2024, 3, 1, 10, 0, tzinfo=UTC).isoformat()
        late = datetime(2025, 9, 1, 10, 0, tzinfo=UTC).isoformat()
        await _post_trade(client, h, portfolio_id, account_id, symbol="DT2", opened_at=early)
        await _post_trade(client, h, portfolio_id, account_id, symbol="DT2", opened_at=late)

        cutoff = datetime(2024, 12, 31, tzinfo=UTC).isoformat()
        items = await _list_trades(
            client, h, portfolio_id, symbols=["DT2"], opened_at_to=cutoff
        )
        opened_dates = [t["opened_at"] for t in items]
        assert all(d <= cutoff for d in opened_dates)


@pytest.mark.integration
class TestTradeSort:
    """Tests for sort_by / sort_dir on ``GET /api/v1/trades``."""

    async def test_sort_by_symbol_asc(self, client: AsyncClient) -> None:
        """sort_by=symbol&sort_dir=asc should return trades in ascending symbol order."""
        h = await _get_auth_headers(client)
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)
        await _post_trade(client, h, portfolio_id, account_id, symbol="ZZZ")
        await _post_trade(client, h, portfolio_id, account_id, symbol="AAA")
        await _post_trade(client, h, portfolio_id, account_id, symbol="MMM")

        items = await _list_trades(
            client, h, portfolio_id, sort_by="symbol", sort_dir="asc"
        )
        symbols = [t["symbol"] for t in items]
        assert symbols == sorted(symbols)

    async def test_sort_by_symbol_desc(self, client: AsyncClient) -> None:
        """sort_by=symbol&sort_dir=desc should return trades in descending symbol order."""
        h = await _get_auth_headers(client)
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)
        await _post_trade(client, h, portfolio_id, account_id, symbol="ZZZ")
        await _post_trade(client, h, portfolio_id, account_id, symbol="AAA")
        await _post_trade(client, h, portfolio_id, account_id, symbol="MMM")

        items = await _list_trades(
            client, h, portfolio_id, sort_by="symbol", sort_dir="desc"
        )
        symbols = [t["symbol"] for t in items]
        assert symbols == sorted(symbols, reverse=True)

    async def test_sort_by_opened_at_asc(self, client: AsyncClient) -> None:
        """sort_by=opened_at&sort_dir=asc should return oldest trade first."""
        h = await _get_auth_headers(client)
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)
        old = datetime(2023, 1, 1, tzinfo=UTC).isoformat()
        new = datetime(2025, 1, 1, tzinfo=UTC).isoformat()
        await _post_trade(client, h, portfolio_id, account_id, symbol="SORT1", opened_at=new)
        await _post_trade(client, h, portfolio_id, account_id, symbol="SORT1", opened_at=old)

        items = await _list_trades(
            client,
            h,
            portfolio_id,
            symbols=["SORT1"],
            sort_by="opened_at",
            sort_dir="asc",
        )
        dates = [t["opened_at"] for t in items]
        assert dates == sorted(dates)


@pytest.mark.integration
class TestTradeFilterExecutionState:
    """Tests for execution_state filter on ``GET /api/v1/trades``."""

    async def test_filter_by_execution_state_manual(self, client: AsyncClient) -> None:
        h = await _get_auth_headers(client)
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)
        manual_trade = await _post_trade(client, h, portfolio_id, account_id, symbol="ESTATEM")

        items = await _list_trades(
            client,
            h,
            portfolio_id,
            execution_state=["manual"],
            symbols=["ESTATE"],
        )
        returned_ids = {item["id"] for item in items}
        assert manual_trade["id"] in returned_ids

    async def test_filter_by_execution_state_edited_after_metadata_patch(
        self, client: AsyncClient
    ) -> None:
        h = await _get_auth_headers(client)
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)
        trade = await _post_trade(client, h, portfolio_id, account_id, symbol="ESTATEE")

        patch_res = await client.patch(
            f"/api/v1/portfolios/{portfolio_id}/trades/{trade['id']}",
            json={"journal": "metadata-edit"},
            headers=h,
        )
        assert patch_res.status_code == 200, patch_res.text

        items = await _list_trades(
            client,
            h,
            portfolio_id,
            execution_state=["edited"],
            symbols=["ESTATEE"],
        )
        returned_ids = {item["id"] for item in items}
        assert trade["id"] in returned_ids

    async def test_filter_by_execution_state_or_semantics(self, client: AsyncClient) -> None:
        h = await _get_auth_headers(client)
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)
        manual_trade = await _post_trade(client, h, portfolio_id, account_id, symbol="ESTATEOR1")
        edited_trade = await _post_trade(client, h, portfolio_id, account_id, symbol="ESTATEOR2")

        patch_res = await client.patch(
            f"/api/v1/portfolios/{portfolio_id}/trades/{edited_trade['id']}",
            json={"journal": "edited-trade"},
            headers=h,
        )
        assert patch_res.status_code == 200, patch_res.text

        items = await _list_trades(
            client,
            h,
            portfolio_id,
            execution_state=["manual", "edited"],
            symbols=["ESTATEOR"],
        )
        returned_ids = {item["id"] for item in items}
        assert manual_trade["id"] in returned_ids
        assert edited_trade["id"] in returned_ids


@pytest.mark.integration
class TestTradeFilterHasUnlinkedExecutions:
    """Tests for has_unlinked_executions filter on GET /api/v1/trades."""

    async def test_filter_by_has_unlinked_executions_true(self, client: AsyncClient, db_session: AsyncSession) -> None:
        h = await _get_auth_headers(client)
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)

        flagged_trade = await _post_trade(client, h, portfolio_id, account_id, symbol="ULINK1")
        unflagged_trade = await _post_trade(client, h, portfolio_id, account_id, symbol="ULINK2")

        patch_res = await client.patch(
            f"/api/v1/portfolios/{portfolio_id}/trades/{flagged_trade['id']}",
            headers=h,
            json={"has_unlinked_executions": True},
        )
        assert patch_res.status_code == 200, patch_res.text

        await db_session.execute(
            text("UPDATE trades SET has_unlinked_executions = true WHERE id = :trade_id"),
            {"trade_id": uuid.UUID(str(flagged_trade["id"]))},
        )
        await db_session.flush()

        items = await _list_trades(
            client,
            h,
            portfolio_id,
            has_unlinked_executions=True,
            symbols=["ULINK"],
        )
        returned_ids = {item["id"] for item in items}
        assert flagged_trade["id"] in returned_ids
        assert unflagged_trade["id"] not in returned_ids

    async def test_filter_by_has_unlinked_executions_omitted_preserves_behavior(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        h = await _get_auth_headers(client)
        portfolio_id, account_id = await _create_portfolio_and_account(client, h)

        trade_a = await _post_trade(client, h, portfolio_id, account_id, symbol="ULINK3")
        trade_b = await _post_trade(client, h, portfolio_id, account_id, symbol="ULINK4")

        patch_res = await client.patch(
            f"/api/v1/portfolios/{portfolio_id}/trades/{trade_a['id']}",
            headers=h,
            json={"has_unlinked_executions": True},
        )
        assert patch_res.status_code == 200, patch_res.text

        await db_session.execute(
            text("UPDATE trades SET has_unlinked_executions = true WHERE id = :trade_id"),
            {"trade_id": uuid.UUID(str(trade_a["id"]))},
        )
        await db_session.flush()

        all_items = await _list_trades(client, h, portfolio_id, symbols=["ULINK"])
        returned_ids = {item["id"] for item in all_items}
        assert trade_a["id"] in returned_ids
        assert trade_b["id"] in returned_ids
