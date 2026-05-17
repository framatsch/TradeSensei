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

"""Integration tests for split-aware import flow and API visibility."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from time import perf_counter

import pytest
from httpx import AsyncClient

_REGISTER_URL = "/api/v1/auth/register"
_TOKEN_URL = "/api/v1/auth/token"
_PORTFOLIOS_URL = "/api/v1/portfolios"


def _make_split_xml(trade_count: int) -> bytes:
    """Build a deterministic IBKR XML fixture with split-producing trades.

    Args:
        trade_count: Number of split pairs to include.

    Returns:
        UTF-8 encoded FlexQuery XML bytes.
    """
    rows: list[str] = []
    base = datetime(2026, 3, 1, 9, 30, tzinfo=UTC)
    for idx in range(trade_count):
        opened_at = base.replace(day=min(28, 1 + (idx % 20)))
        close_1 = opened_at.replace(hour=10, minute=0)
        close_2 = opened_at.replace(hour=10, minute=30)
        trade_num = idx + 1
        symbol = f"SPL{trade_num:04d}"
        conid = f"{900000 + trade_num}"
        entry_tx = f"E{trade_num:05d}"
        close_a_tx = f"C{trade_num:05d}A"
        close_b_tx = f"C{trade_num:05d}B"
        rows.append(
            (
                '<Trade transactionID="{tx}" assetCategory="STK" symbol="{symbol}" '
                'conid="{conid}" tradeDate="{date}" dateTime="{datetime}" '
                'quantity="100" tradePrice="100" ibCommission="-1" currency="USD" />'
            ).format(
                tx=entry_tx,
                symbol=symbol,
                conid=conid,
                date=opened_at.strftime("%Y%m%d"),
                datetime=opened_at.strftime("%Y%m%d;%H%M%S"),
            )
        )
        rows.append(
            (
                '<Trade transactionID="{tx}" assetCategory="STK" symbol="{symbol}" '
                'conid="{conid}" tradeDate="{date}" dateTime="{datetime}" '
                'quantity="-60" tradePrice="110" ibCommission="0" '
                'fifoPnlRealized="600" currency="USD" />'
            ).format(
                tx=close_a_tx,
                symbol=symbol,
                conid=conid,
                date=close_1.strftime("%Y%m%d"),
                datetime=close_1.strftime("%Y%m%d;%H%M%S"),
            )
        )
        rows.append(
            (
                '<Trade transactionID="{tx}" assetCategory="STK" symbol="{symbol}" '
                'conid="{conid}" tradeDate="{date}" dateTime="{datetime}" '
                'quantity="-40" tradePrice="105" ibCommission="0" '
                'fifoPnlRealized="200" currency="USD" />'
            ).format(
                tx=close_b_tx,
                symbol=symbol,
                conid=conid,
                date=close_2.strftime("%Y%m%d"),
                datetime=close_2.strftime("%Y%m%d;%H%M%S"),
            )
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<FlexQueryResponse><FlexStatements><FlexStatement><Trades>"
        + "".join(rows)
        + "</Trades></FlexStatement>"
        + "</FlexStatements></FlexQueryResponse>"
    )
    return xml.encode("utf-8")


async def _auth_headers(client: AsyncClient, suffix: str) -> dict[str, str]:
    """Register/login and return auth headers.

    Args:
        client: HTTP test client.
        suffix: Unique suffix for user identity fields.

    Returns:
        Authorization header mapping.
    """
    username = f"split_{suffix}"
    email = f"split_{suffix}@example.com"
    password = "SplitAware@99"
    reg = await client.post(
        _REGISTER_URL,
        json={"username": username, "email": email, "password": password},
    )
    assert reg.status_code == 201, reg.text
    token_res = await client.post(
        _TOKEN_URL,
        data={"username": email, "password": password},
    )
    assert token_res.status_code == 200, token_res.text
    token = token_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_account(client: AsyncClient, headers: dict[str, str]) -> str:
    """Create an account and return its ID."""
    portfolio_res = await client.post(
        _PORTFOLIOS_URL,
        headers=headers,
        json={"name": "Split Portfolio", "base_currency": "USD"},
    )
    assert portfolio_res.status_code == 201, portfolio_res.text
    portfolio_id = str(portfolio_res.json()["data"]["id"])

    res = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        headers=headers,
        json={"name": "Split Import", "type": "ibkr", "currency": "USD"},
    )
    assert res.status_code == 201, res.text
    return portfolio_id, str(res.json()["data"]["id"])


async def _import_xml(
    client: AsyncClient,
    headers: dict[str, str],
    portfolio_id: str,
    account_id: str,
    xml_content: bytes,
) -> dict[str, object]:
    """Import xml content using public import API endpoint."""
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/imports/upload",
        headers=headers,
        data={"broker": "ibkr", "account_id": account_id},
        files={"file": ("split.xml", xml_content, "application/xml")},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


@pytest.mark.integration
async def test_complete_import_flow_with_split_scenarios(client: AsyncClient) -> None:
    """Import should produce trades whose execution legs include split-origin rows."""
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_account(client, headers)

    import_result = await _import_xml(
        client,
        headers,
        portfolio_id,
        account_id,
        _make_split_xml(3),
    )
    assert int(import_result["trades_created"]) >= 6

    trades_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades?limit=50", headers=headers
    )
    assert trades_resp.status_code == 200, trades_resp.text
    trades = trades_resp.json()["data"]["items"]
    assert trades, "Expected at least one imported trade"

    split_found = False
    for trade in trades:
        ex_resp = await client.get(
            f"/api/v1/portfolios/{portfolio_id}/trades/{trade['id']}/executions",
            headers=headers,
        )
        assert ex_resp.status_code == 200, ex_resp.text
        executions = ex_resp.json()["data"]
        if any(exec_row["origin"] == "split" for exec_row in executions):
            split_found = True
            for exec_row in executions:
                if exec_row["origin"] == "split":
                    assert exec_row["parent_id"] is not None
                    assert Decimal(exec_row["quantity"]) > Decimal("0")
            break

    assert split_found, "Expected at least one split execution after import"


@pytest.mark.integration
async def test_trade_executions_api_after_split_import(client: AsyncClient) -> None:
    """Trade executions endpoint should return split lineage fields after import."""
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_account(client, headers)
    await _import_xml(client, headers, portfolio_id, account_id, _make_split_xml(2))

    trades_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades?limit=20", headers=headers
    )
    assert trades_resp.status_code == 200, trades_resp.text
    trade_id = trades_resp.json()["data"]["items"][0]["id"]

    ex_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}/executions",
        headers=headers,
    )
    assert ex_resp.status_code == 200, ex_resp.text
    data = ex_resp.json()["data"]
    assert data
    assert {"origin", "parent_id", "trade_id"}.issubset(data[0].keys())


@pytest.mark.integration
async def test_reimport_idempotency_via_fresh_start(client: AsyncClient) -> None:
    """Fresh-start re-import with same file should produce stable trade counts."""
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_account(client, headers)
    xml_content = _make_split_xml(5)

    first = await _import_xml(client, headers, portfolio_id, account_id, xml_content)

    fresh = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/imports/{account_id}/fresh-start",
        headers=headers,
        data={"broker": "ibkr", "acknowledged": "true"},
        files={"file": ("split.xml", xml_content, "application/xml")},
    )
    assert fresh.status_code == 200, fresh.text
    second = fresh.json()["data"]["import_result"]

    assert int(first["trades_created"]) == int(second["trades_created"])
    assert int(second["trades_parsed"]) >= int(second["trades_created"])


@pytest.mark.integration
async def test_large_file_import_performance_smoke(client: AsyncClient) -> None:
    """Large split fixture should import in a bounded time and row count."""
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_account(client, headers)
    xml_content = _make_split_xml(340)

    started_at = perf_counter()
    result = await _import_xml(client, headers, portfolio_id, account_id, xml_content)
    elapsed_s = perf_counter() - started_at

    assert int(result["trades_created"]) >= 680
    # Non-flaky smoke cap for CI/local variance.
    assert elapsed_s < 60
