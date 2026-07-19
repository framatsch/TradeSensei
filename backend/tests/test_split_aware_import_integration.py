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


def _make_split_and_open_combo_xml(trade_count: int) -> bytes:
    """Split-producing trades plus one never-closed 2-leg combo position.

    Used to reproduce a regression where any open combo position in an
    account caused repeated (non-cleared) re-imports to silently duplicate
    every fragmented/split single-instrument trade on each run.
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
        rows.append(
            (
                '<Trade transactionID="E{n:05d}" assetCategory="STK" symbol="{symbol}" '
                'conid="{conid}" tradeDate="{date}" dateTime="{datetime}" '
                'quantity="100" tradePrice="100" ibCommission="-1" currency="USD" />'
            ).format(
                n=trade_num,
                symbol=symbol,
                conid=conid,
                date=opened_at.strftime("%Y%m%d"),
                datetime=opened_at.strftime("%Y%m%d;%H%M%S"),
            )
        )
        rows.append(
            (
                '<Trade transactionID="C{n:05d}A" assetCategory="STK" symbol="{symbol}" '
                'conid="{conid}" tradeDate="{date}" dateTime="{datetime}" '
                'quantity="-60" tradePrice="110" ibCommission="0" '
                'fifoPnlRealized="600" currency="USD" />'
            ).format(
                n=trade_num,
                symbol=symbol,
                conid=conid,
                date=close_1.strftime("%Y%m%d"),
                datetime=close_1.strftime("%Y%m%d;%H%M%S"),
            )
        )
        rows.append(
            (
                '<Trade transactionID="C{n:05d}B" assetCategory="STK" symbol="{symbol}" '
                'conid="{conid}" tradeDate="{date}" dateTime="{datetime}" '
                'quantity="-40" tradePrice="105" ibCommission="0" '
                'fifoPnlRealized="200" currency="USD" />'
            ).format(
                n=trade_num,
                symbol=symbol,
                conid=conid,
                date=close_2.strftime("%Y%m%d"),
                datetime=close_2.strftime("%Y%m%d;%H%M%S"),
            )
        )

    # One 2-leg combo order that opens and is never closed (mirrors a
    # real-world still-open vertical spread).
    combo_opened_at = base.replace(day=1, hour=14)
    rows.append(
        '<Trade transactionID="COMBO001" assetCategory="OPT" symbol="QQQ   260807C00735000" '
        'conid="800001" multiplier="100" tradeDate="{date}" dateTime="{datetime}" '
        'quantity="1" tradePrice="10" ibCommission="-1" netCash="-1001" '
        'openCloseIndicator="O" fifoPnlRealized="0" brokerageOrderID="combo-open-1" '
        'currency="USD" />'.format(
            date=combo_opened_at.strftime("%Y%m%d"),
            datetime=combo_opened_at.strftime("%Y%m%d;%H%M%S"),
        )
    )
    rows.append(
        '<Trade transactionID="COMBO002" assetCategory="OPT" symbol="QQQ   260807C00743000" '
        'conid="800002" multiplier="100" tradeDate="{date}" dateTime="{datetime}" '
        'quantity="-1" tradePrice="7" ibCommission="-1" netCash="699" '
        'openCloseIndicator="O" fifoPnlRealized="0" brokerageOrderID="combo-open-1" '
        'currency="USD" />'.format(
            date=combo_opened_at.strftime("%Y%m%d"),
            datetime=combo_opened_at.strftime("%Y%m%d;%H%M%S"),
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


@pytest.mark.integration
async def test_reimport_with_open_combo_does_not_duplicate_split_trades(
    client: AsyncClient,
) -> None:
    """Regression: re-importing the same file must not duplicate trades when
    the account has an open combo position.

    Root cause (fixed): the raw-pipeline import skipped its normal
    "delete all trades and rebuild" safety net for the WHOLE account whenever
    ANY combo position was still open, so fragmented/split single-instrument
    trades (whose split-parent execution loses its `trade_id` link on
    restore) were re-inserted as duplicates on every subsequent import,
    unbounded. The fix scopes the delete-and-rebuild to exclude only the
    trades backing the open combo position(s), and runs it before execution
    `trade_id` values are read into memory.
    """
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_account(client, headers)
    xml_content = _make_split_and_open_combo_xml(3)

    first = await _import_xml(client, headers, portfolio_id, account_id, xml_content)
    first_total = int(first["trades_created"])
    assert first_total > 0

    async def _trade_count() -> int:
        resp = await client.get(
            f"/api/v1/portfolios/{portfolio_id}/trades?limit=100", headers=headers
        )
        assert resp.status_code == 200, resp.text
        return len(resp.json()["data"]["items"])

    assert await _trade_count() == first_total

    # Re-import the SAME file three more times without clearing in between —
    # this must not grow the total trade count beyond the first import.
    for _ in range(3):
        await _import_xml(client, headers, portfolio_id, account_id, xml_content)
        assert await _trade_count() == first_total


def _make_two_opens_one_shared_close_combo_xml() -> bytes:
    """Real-world META scenario: two separate opening combo orders on the
    same 2-leg contract set, closed together in one combined order.

    Reproduces the exact shape that exposed a regression where the closing
    leg's typed option fields (strike/expiry/option_type) and open_close
    were lost when it got split across the two resulting trades.
    """
    day1 = datetime(2026, 3, 1, 9, 30, tzinfo=UTC)
    day1_b = datetime(2026, 3, 1, 9, 50, tzinfo=UTC)
    close_at = datetime(2026, 3, 1, 9, 57, tzinfo=UTC)

    def leg(
        tx: str,
        symbol: str,
        conid: str,
        dt: datetime,
        quantity: str,
        price: str,
        open_close: str,
        order_id: str,
        pnl: str | None = None,
    ) -> str:
        pnl_attr = f'fifoPnlRealized="{pnl}"' if pnl is not None else 'fifoPnlRealized="0"'
        return (
            f'<Trade transactionID="{tx}" assetCategory="OPT" symbol="{symbol}" '
            f'conid="{conid}" multiplier="100" tradeDate="{dt.strftime("%Y%m%d")}" '
            f'dateTime="{dt.strftime("%Y%m%d;%H%M%S")}" quantity="{quantity}" tradePrice="{price}" '
            f'ibCommission="-1" netCash="0" openCloseIndicator="{open_close}" {pnl_attr} '
            f'brokerageOrderID="{order_id}" currency="USD" />'
        )

    rows = [
        # Order A opens 620C short / 640C long.
        leg("A1", "META  260731C00620000", "700001", day1, "-1", "63.55", "O", "order-open-a"),
        leg("A2", "META  260731C00640000", "700002", day1, "1", "51.55", "O", "order-open-a"),
        # Order B opens the SAME spread again, 20 minutes later.
        leg("B1", "META  260731C00620000", "700001", day1_b, "-1", "63.42", "O", "order-open-b"),
        leg("B2", "META  260731C00640000", "700002", day1_b, "1", "50.97", "O", "order-open-b"),
        # One combined closing order for BOTH open positions (qty=2 per leg).
        leg("C1", "META  260731C00620000", "700001", close_at, "2", "63.03", "C", "order-close", pnl="87.27"),
        leg("C2", "META  260731C00640000", "700002", close_at, "-2", "50.48", "C", "order-close", pnl="-159.67"),
    ]
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<FlexQueryResponse><FlexStatements><FlexStatement><Trades>"
        + "".join(rows)
        + "</Trades></FlexStatement>"
        + "</FlexStatements></FlexQueryResponse>"
    )
    return xml.encode("utf-8")


@pytest.mark.integration
async def test_combo_split_close_preserves_option_fields_on_split_children(
    client: AsyncClient,
) -> None:
    """Regression: split-child executions must keep strike/expiry/option_type
    and open_close from their parent execution.

    Root cause (fixed): when a single closing execution is shared across two
    trades (e.g. two separate opening orders on the same spread closed
    together — see test_build_combo_positions_two_opens_split_close_produces_two_trades),
    the resulting split-origin `LogicalExecution` rows were created via
    `_process_execution_split` / `_split_execution_for_trade` without copying
    `strike`, `expiry`, `option_type`, or `open_close` from the parent, even
    though these fields are always populated for the parent (it's a real
    option leg). This broke both display (ExecutionLegsTable / SummaryCard
    fell back to raw conid) and grouping (ExecutionSummaryCard's grouping key
    includes these fields, so a split child with nulled-out fields no longer
    matched its own opening leg's group and appeared as a spurious extra row).
    """
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_account(client, headers)
    xml_content = _make_two_opens_one_shared_close_combo_xml()

    result = await _import_xml(client, headers, portfolio_id, account_id, xml_content)
    assert result["warnings"] == []
    assert int(result["trades_created"]) == 2

    trades_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades?limit=20", headers=headers
    )
    assert trades_resp.status_code == 200, trades_resp.text
    trades = trades_resp.json()["data"]["items"]
    assert len(trades) == 2

    for trade in trades:
        ex_resp = await client.get(
            f"/api/v1/portfolios/{portfolio_id}/trades/{trade['id']}/executions",
            headers=headers,
        )
        assert ex_resp.status_code == 200, ex_resp.text
        executions = ex_resp.json()["data"]
        assert len(executions) == 4  # 2 opening legs + 2 closing (split) legs

        split_legs = [e for e in executions if e["origin"] == "split"]
        assert len(split_legs) == 2, "Expected both closing legs to be split across the two trades"

        for execution in executions:
            assert execution["option_type"] == "C", execution
            assert execution["strike"] in ("620.00000000", "640.00000000"), execution
            assert execution["expiry"] == "2026-07-31", execution
            assert execution["open_close"] in ("O", "C"), execution


@pytest.mark.integration
@pytest.mark.slow
async def test_large_file_import_performance_smoke(client: AsyncClient) -> None:
    """Large split fixture should import in a bounded time and row count."""
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_account(client, headers)
    xml_content = _make_split_xml(100)

    started_at = perf_counter()
    result = await _import_xml(client, headers, portfolio_id, account_id, xml_content)
    elapsed_s = perf_counter() - started_at

    assert int(result["trades_created"]) >= 200
    # Non-flaky smoke cap for CI/local variance.
    assert elapsed_s < 120
