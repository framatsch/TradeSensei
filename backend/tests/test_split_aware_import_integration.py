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
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.flex_import_service import FlexImportService
from app.services.import_service import ImportService

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


async def _create_account(client: AsyncClient, headers: dict[str, str]) -> tuple[str, str]:
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


async def _create_ibkr_account_with_flex_properties(
    client: AsyncClient,
    headers: dict[str, str],
) -> tuple[str, str]:
    """Create an IBKR account configured for broker sync tests."""
    portfolio_res = await client.post(
        _PORTFOLIOS_URL,
        headers=headers,
        json={"name": "Sync Portfolio", "base_currency": "USD"},
    )
    assert portfolio_res.status_code == 201, portfolio_res.text
    portfolio_id = str(portfolio_res.json()["data"]["id"])

    res = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        headers=headers,
        json={
            "name": "IBKR Sync Account",
            "type": "ibkr",
            "currency": "USD",
            "properties": {
                "ibkr_flex_token": "dummy-token",
                "ibkr_flex_query_id": "dummy-query-id",
            },
        },
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


async def _sync_ibkr(
    client: AsyncClient,
    headers: dict[str, str],
    account_id: str,
    *,
    from_date: str = "20260301",
) -> dict[str, object]:
    """Run account-centric broker sync and return response data."""
    response = await client.post(
        f"/api/v1/broker/sync/{account_id}?from_date={from_date}",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


async def _fetch_account_trade_execution_raw_snapshots(
    db_session: AsyncSession,
    *,
    account_id: str,
) -> tuple[
    list[tuple[str, str, str | None, str | None, str | None, str | None]],
    list[tuple[str, str, str, str, str | None]],
    list[tuple[str, str, str, str]],
]:
    """Return normalized snapshots for trades, executions, and raw rows."""

    def _normalize_source_id(value: str | None) -> str | None:
        if value is None:
            return None
        return value.rsplit(":", 1)[-1]

    aid = uuid.UUID(account_id)

    trade_rows = await db_session.execute(
        text(
            "SELECT symbol, opened_at::text, quantity::text, entry_price::text, "
            "exit_price::text, net_pnl::text "
            "FROM trades WHERE account_id = :account_id ORDER BY symbol, opened_at, id"
        ),
        {"account_id": aid},
    )
    trades = sorted(
        (row[0], row[1], row[2], row[3], row[4], row[5])
        for row in trade_rows.fetchall()
    )

    execution_rows = await db_session.execute(
        text(
            "SELECT symbol, executed_at::text, direction::text, quantity::text, source_id "
            "FROM logical_executions "
            "WHERE account_id = :account_id AND deleted = false "
            "ORDER BY symbol, executed_at, id"
        ),
        {"account_id": aid},
    )
    executions = sorted(
        (row[0], row[1], row[2], row[3], _normalize_source_id(row[4]))
        for row in execution_rows.fetchall()
    )

    raw_rows = await db_session.execute(
        text(
            "SELECT symbol, executed_at::text, direction::text, id "
            "FROM broker_raw_transactions "
            "WHERE account_id = :account_id "
            "ORDER BY symbol, executed_at, id"
        ),
        {"account_id": aid},
    )
    raw = sorted(
        (row[0], row[1], row[2], _normalize_source_id(row[3]))
        for row in raw_rows.fetchall()
    )

    return trades, executions, raw


async def _projection_snapshot(
    client: AsyncClient,
    headers: dict[str, str],
    portfolio_id: str,
) -> list[tuple[str, str, str | None, str | None, str | None, str | None]]:
    """Return a stable projection snapshot for regression comparisons."""
    response = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades?limit=100",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    items = response.json()["data"]["items"]

    snapshot = [
        (
            item["symbol"],
            item["opened_at"],
            item.get("quantity"),
            item.get("entry_price"),
            item.get("exit_price"),
            item.get("net_pnl"),
        )
        for item in items
    ]
    return sorted(snapshot)


@pytest.mark.integration
async def test_ibkr_sync_creates_raw_and_linked_executions(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """IBKR sync must materialise raw rows, executions, and linked trades."""
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    _, account_id = await _create_ibkr_account_with_flex_properties(client, headers)
    xml_content = _make_split_xml(2)

    async def _fake_fetch(
        self: FlexImportService,
        *,
        query_id: str,
        from_date: str | None = None,
    ) -> bytes:
        del self, query_id, from_date
        return xml_content

    monkeypatch.setattr(FlexImportService, "fetch_flex_report", _fake_fetch)

    sync_result = await _sync_ibkr(client, headers, account_id)
    assert int(sync_result["imported_count"]) > 0

    aid = uuid.UUID(account_id)
    raw_count = await db_session.execute(
        text("SELECT COUNT(*) FROM broker_raw_transactions WHERE account_id = :account_id"),
        {"account_id": aid},
    )
    assert raw_count.scalar() > 0

    execution_count = await db_session.execute(
        text("SELECT COUNT(*) FROM logical_executions WHERE account_id = :account_id AND deleted = false"),
        {"account_id": aid},
    )
    assert execution_count.scalar() > 0

    trades_without_execution = await db_session.execute(
        text(
            "SELECT COUNT(*) FROM trades t "
            "WHERE t.account_id = :account_id "
            "AND NOT EXISTS ("
            "  SELECT 1 FROM logical_executions le "
            "  WHERE le.trade_id = t.id AND le.deleted = false"
            ")"
        ),
        {"account_id": aid},
    )
    assert trades_without_execution.scalar() == 0


@pytest.mark.integration
async def test_ibkr_sync_reimport_is_idempotent(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Re-syncing identical Flex payload should not create additional rows."""
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    _, account_id = await _create_ibkr_account_with_flex_properties(client, headers)
    xml_content = _make_split_xml(2)

    async def _fake_fetch(
        self: FlexImportService,
        *,
        query_id: str,
        from_date: str | None = None,
    ) -> bytes:
        del self, query_id, from_date
        return xml_content

    monkeypatch.setattr(FlexImportService, "fetch_flex_report", _fake_fetch)

    first = await _sync_ibkr(client, headers, account_id)
    assert int(first["imported_count"]) > 0
    before = await _fetch_account_trade_execution_raw_snapshots(db_session, account_id=account_id)

    second = await _sync_ibkr(client, headers, account_id)
    after = await _fetch_account_trade_execution_raw_snapshots(db_session, account_id=account_id)

    assert int(second["imported_count"]) == 0
    assert before == after


@pytest.mark.integration
async def test_second_consecutive_ibkr_sync_skips_projection_rebuild(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task 6.4: a second consecutive IBKR sync creates zero trades and
    triggers zero raw-transaction inserts (the zero-insert guard, D5).

    ``BrokerSyncResult`` does not surface ``raw_transactions_created``, so
    this wraps ``ImportService.import_trades`` to capture the underlying
    ``ImportResult`` the sync path produces and asserts directly on
    ``raw_transactions_created == 0`` and ``trades_created == 0`` — the
    exact input condition ``ImportService.import_trades`` uses internally
    (``should_rebuild_projection``) to skip the rebuild. This is strong
    evidence the rebuild is skipped (it is the guard's own trigger
    condition) but does not directly instrument the branch itself. Runs
    entirely against the local test database with only the IBKR Flex HTTP
    fetch mocked, so it does not require a live/unlocked IBKR Flex API.
    """
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    _, account_id = await _create_ibkr_account_with_flex_properties(client, headers)
    xml_content = _make_split_xml(2)

    async def _fake_fetch(
        self: FlexImportService,
        *,
        query_id: str,
        from_date: str | None = None,
    ) -> bytes:
        del self, query_id, from_date
        return xml_content

    monkeypatch.setattr(FlexImportService, "fetch_flex_report", _fake_fetch)

    original_import_trades = ImportService.import_trades
    captured_results: list[object] = []

    async def _capturing_import_trades(self: ImportService, **kwargs: object) -> object:
        result = await original_import_trades(self, **kwargs)  # type: ignore[arg-type]
        captured_results.append(result)
        return result

    monkeypatch.setattr(ImportService, "import_trades", _capturing_import_trades)

    first = await _sync_ibkr(client, headers, account_id)
    assert int(first["imported_count"]) > 0
    assert len(captured_results) == 1
    assert captured_results[0].raw_transactions_created > 0  # type: ignore[attr-defined]

    second = await _sync_ibkr(client, headers, account_id)
    assert int(second["imported_count"]) == 0
    assert len(captured_results) == 2

    second_import_result = captured_results[1]
    assert second_import_result.trades_created == 0  # type: ignore[attr-defined]
    assert second_import_result.raw_transactions_created == 0  # type: ignore[attr-defined]


@pytest.mark.integration
async def test_ibkr_sync_and_upload_equivalence(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same IBKR report via sync vs upload must produce identical persistence."""
    sync_headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    upload_headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    _, sync_account_id = await _create_ibkr_account_with_flex_properties(client, sync_headers)
    upload_portfolio_id, upload_account_id = await _create_account(client, upload_headers)
    xml_content = _make_split_xml(2)

    async def _fake_fetch(
        self: FlexImportService,
        *,
        query_id: str,
        from_date: str | None = None,
    ) -> bytes:
        del self, query_id, from_date
        return xml_content

    monkeypatch.setattr(FlexImportService, "fetch_flex_report", _fake_fetch)

    sync_result = await _sync_ibkr(client, sync_headers, sync_account_id)
    assert int(sync_result["imported_count"]) > 0

    upload_result = await _import_xml(
        client,
        upload_headers,
        upload_portfolio_id,
        upload_account_id,
        xml_content,
    )
    assert int(upload_result["trades_created"]) > 0

    sync_snapshot = await _fetch_account_trade_execution_raw_snapshots(
        db_session,
        account_id=sync_account_id,
    )
    upload_snapshot = await _fetch_account_trade_execution_raw_snapshots(
        db_session,
        account_id=upload_account_id,
    )

    assert sync_snapshot == upload_snapshot


@pytest.mark.integration
async def test_protected_trade_survives_ibkr_sync_without_sentinel_orphan(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Protected trade remains stable and no sentinel orphan is created via sync."""
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_ibkr_account_with_flex_properties(client, headers)
    symbol = "PROTSYNC"
    conid = "780001"
    tx_prefix = "PS"

    payloads = iter(
        [
            _make_single_leg_xml(symbol, conid, tx_prefix, include_close=False),
            _make_single_leg_xml(symbol, conid, tx_prefix, include_close=True),
        ]
    )

    async def _fake_fetch(
        self: FlexImportService,
        *,
        query_id: str,
        from_date: str | None = None,
    ) -> bytes:
        del self, query_id, from_date
        return next(payloads)

    monkeypatch.setattr(FlexImportService, "fetch_flex_report", _fake_fetch)

    first_sync = await _sync_ibkr(client, headers, account_id)
    assert int(first_sync["imported_count"]) > 0

    trades_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades?limit=20",
        headers=headers,
    )
    assert trades_resp.status_code == 200, trades_resp.text
    items = trades_resp.json()["data"]["items"]
    assert len(items) == 1
    protected_trade_id = items[0]["id"]

    patch_resp = await client.patch(
        f"/api/v1/portfolios/{portfolio_id}/trades/{protected_trade_id}",
        headers=headers,
        json={"journal": "sync-protected"},
    )
    assert patch_resp.status_code == 200, patch_resp.text

    second_sync = await _sync_ibkr(client, headers, account_id)
    assert int(second_sync["imported_count"]) == 0

    protected_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{protected_trade_id}",
        headers=headers,
    )
    assert protected_resp.status_code == 200, protected_resp.text
    protected_trade = protected_resp.json()["data"]
    assert protected_trade["journal"] == "sync-protected"
    assert protected_trade["closed_at"] is not None

    aid = uuid.UUID(account_id)
    sentinel_orphans = await db_session.execute(
        text(
            "SELECT COUNT(*) FROM trades "
            "WHERE account_id = :account_id AND symbol = :symbol AND entry_price = 0.001"
        ),
        {"account_id": aid, "symbol": symbol},
    )
    assert sentinel_orphans.scalar() == 0


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
async def test_trade_read_exposes_chart_basis_and_corporate_action_identity(client: AsyncClient) -> None:
    """Trade read endpoint should expose chart basis and actionable impact metadata."""
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, _account_id = await _create_account(client, headers)

    trade_response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers=headers,
        json={
            "symbol": "ATOS",
            "direction": "LONG",
            "asset_class": "EQUITY",
            "quantity": "100",
            "entry_price": "2",
            "opened_at": "2024-01-02T15:00:00Z",
            "currency": "USD",
        },
    )
    assert trade_response.status_code == 201, trade_response.text
    trade_id = str(trade_response.json()["data"]["id"])

    action_response = await client.post(
        "/api/v1/corporate-actions",
        headers=headers,
        json={
            "symbol": "ATOS",
            "date": "2024-03-13",
            "ratio": "0.05",
            "old_conid": "111",
            "new_conid": "222",
        },
    )
    assert action_response.status_code == 201, action_response.text
    action = action_response.json()["data"]

    get_trade_response = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}",
        headers=headers,
    )
    assert get_trade_response.status_code == 200, get_trade_response.text
    trade = get_trade_response.json()["data"]

    assert Decimal(trade["entry_price"]) == Decimal("40")
    assert Decimal(trade["chart_entry_price"]) == Decimal("40")
    assert Decimal(trade["chart_quantity"]) == Decimal("5")
    assert len(trade["corporate_action_impact"]) == 1
    impact = trade["corporate_action_impact"][0]
    assert impact["id"] == action["id"]
    assert impact["symbol"] == "ATOS"
    assert impact["date"] == "2024-03-13"
    assert Decimal(impact["ratio"]) == Decimal("0.05")
    assert impact["old_conid"] == "111"
    assert impact["new_conid"] == "222"


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
async def test_reimport_preserves_trade_projection_values(client: AsyncClient) -> None:
    """Re-importing the same file keeps the trade projection identical."""
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_account(client, headers)
    xml_content = _make_split_xml(4)

    await _import_xml(client, headers, portfolio_id, account_id, xml_content)
    first_snapshot = await _projection_snapshot(client, headers, portfolio_id)

    fresh = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/imports/{account_id}/fresh-start",
        headers=headers,
        data={"broker": "ibkr", "acknowledged": "true"},
        files={"file": ("split.xml", xml_content, "application/xml")},
    )
    assert fresh.status_code == 200, fresh.text

    second_snapshot = await _projection_snapshot(client, headers, portfolio_id)
    assert second_snapshot == first_snapshot


@pytest.mark.integration
async def test_metadata_protected_trade_survives_reimport_without_override(
    client: AsyncClient,
) -> None:
    """Protected closed trade keeps structure and linked executions across re-import."""
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_account(client, headers)

    await _import_xml(client, headers, portfolio_id, account_id, _make_split_xml(1))

    trades_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades?limit=20", headers=headers
    )
    assert trades_resp.status_code == 200, trades_resp.text
    items = trades_resp.json()["data"]["items"]
    assert items
    protected_trade_id = items[0]["id"]

    before_trade_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{protected_trade_id}", headers=headers
    )
    assert before_trade_resp.status_code == 200, before_trade_resp.text
    before_trade = before_trade_resp.json()["data"]
    assert before_trade["closed_at"] is not None
    assert before_trade["pnl"] is not None
    assert before_trade["net_pnl"] is not None

    before_exec_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{protected_trade_id}/executions",
        headers=headers,
    )
    assert before_exec_resp.status_code == 200, before_exec_resp.text
    before_execs = before_exec_resp.json()["data"]
    before_exec_ids = {row["id"] for row in before_execs}
    assert before_exec_ids

    patch_resp = await client.patch(
        f"/api/v1/portfolios/{portfolio_id}/trades/{protected_trade_id}",
        headers=headers,
        json={"journal": "metadata-protected"},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    assert patch_resp.json()["data"]["journal"] == "metadata-protected"

    second_import = await _import_xml(
        client,
        headers,
        portfolio_id,
        account_id,
        _make_split_xml(2),
    )
    assert int(second_import["raw_transactions_created"]) > 0

    protected_trade_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{protected_trade_id}", headers=headers
    )
    assert protected_trade_resp.status_code == 200, protected_trade_resp.text
    protected_trade = protected_trade_resp.json()["data"]
    assert protected_trade["journal"] == "metadata-protected"
    assert protected_trade["closed_at"] == before_trade["closed_at"]
    assert protected_trade["pnl"] == before_trade["pnl"]
    assert protected_trade["net_pnl"] == before_trade["net_pnl"]

    after_exec_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{protected_trade_id}/executions",
        headers=headers,
    )
    assert after_exec_resp.status_code == 200, after_exec_resp.text
    after_execs = after_exec_resp.json()["data"]
    assert all(row["trade_id"] == protected_trade_id for row in after_execs)


def _make_single_leg_xml(symbol: str, conid: str, tx_prefix: str, *, include_close: bool) -> bytes:
    """Build a single-symbol IBKR XML fixture: one opening leg, optionally closed.

    Args:
        symbol: Ticker symbol for the fixture.
        conid: Broker contract identifier.
        tx_prefix: Prefix for transaction IDs (kept identical across two
            imports of the same opening leg so the raw upsert is a no-op for
            the entry and only the new closing row is inserted).
        include_close: When ``True``, adds a fully-closing leg.

    Returns:
        UTF-8 encoded FlexQuery XML bytes.
    """
    opened_at = datetime(2026, 4, 1, 9, 30, tzinfo=UTC)
    closed_at = datetime(2026, 4, 2, 10, 0, tzinfo=UTC)
    rows = [
        (
            '<Trade transactionID="{tx}" assetCategory="STK" symbol="{symbol}" '
            'conid="{conid}" tradeDate="{date}" dateTime="{datetime}" '
            'quantity="100" tradePrice="50" ibCommission="-1" currency="USD" />'
        ).format(
            tx=f"{tx_prefix}E1",
            symbol=symbol,
            conid=conid,
            date=opened_at.strftime("%Y%m%d"),
            datetime=opened_at.strftime("%Y%m%d;%H%M%S"),
        )
    ]
    if include_close:
        rows.append(
            (
                '<Trade transactionID="{tx}" assetCategory="STK" symbol="{symbol}" '
                'conid="{conid}" tradeDate="{date}" dateTime="{datetime}" '
                'quantity="-100" tradePrice="55" ibCommission="-1" '
                'fifoPnlRealized="500" currency="USD" />'
            ).format(
                tx=f"{tx_prefix}C1",
                symbol=symbol,
                conid=conid,
                date=closed_at.strftime("%Y%m%d"),
                datetime=closed_at.strftime("%Y%m%d;%H%M%S"),
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


def _make_single_leg_with_new_close_xml(
    symbol: str,
    conid: str,
    tx_prefix: str,
    *,
    close_tx_suffix: str,
    close_price: str = "55",
    close_day_offset: int = 2,
) -> bytes:
    """Build fixture with same opening tx and a distinct closing tx for re-imports."""
    opened_at = datetime(2026, 4, 1, 9, 30, tzinfo=UTC)
    closed_at = datetime(2026, 4, 1 + close_day_offset, 10, 0, tzinfo=UTC)
    rows = [
        (
            '<Trade transactionID="{tx}" assetCategory="STK" symbol="{symbol}" '
            'conid="{conid}" tradeDate="{date}" dateTime="{datetime}" '
            'quantity="100" tradePrice="50" ibCommission="-1" currency="USD" />'
        ).format(
            tx=f"{tx_prefix}E1",
            symbol=symbol,
            conid=conid,
            date=opened_at.strftime("%Y%m%d"),
            datetime=opened_at.strftime("%Y%m%d;%H%M%S"),
        ),
        (
            '<Trade transactionID="{tx}" assetCategory="STK" symbol="{symbol}" '
            'conid="{conid}" tradeDate="{date}" dateTime="{datetime}" '
            'quantity="-100" tradePrice="{close_price}" ibCommission="-1" '
            'fifoPnlRealized="500" currency="USD" />'
        ).format(
            tx=f"{tx_prefix}{close_tx_suffix}",
            symbol=symbol,
            conid=conid,
            date=closed_at.strftime("%Y%m%d"),
            datetime=closed_at.strftime("%Y%m%d;%H%M%S"),
            close_price=close_price,
        ),
    ]
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<FlexQueryResponse><FlexStatements><FlexStatement><Trades>"
        + "".join(rows)
        + "</Trades></FlexStatement>"
        + "</FlexStatements></FlexQueryResponse>"
    )
    return xml.encode("utf-8")


def _make_same_symbol_two_contracts_xml(*, include_trigger_trade: bool) -> bytes:
    """Build two same-symbol opening legs on different contracts.

    Args:
        include_trigger_trade: Adds a third, unrelated opening leg with a fresh
            transaction id to force non-zero raw inserts on re-import.

    Returns:
        UTF-8 encoded FlexQuery XML bytes.
    """
    opened_at = datetime(2026, 5, 1, 9, 30, tzinfo=UTC)
    rows = [
        (
            '<Trade transactionID="SME1" assetCategory="STK" symbol="SAMESYM" '
            'conid="710001" tradeDate="{date}" dateTime="{datetime}" '
            'quantity="100" tradePrice="50" ibCommission="-1" currency="USD" />'
        ).format(
            date=opened_at.strftime("%Y%m%d"),
            datetime=opened_at.strftime("%Y%m%d;%H%M%S"),
        ),
        (
            '<Trade transactionID="SME2" assetCategory="STK" symbol="SAMESYM" '
            'conid="710002" tradeDate="{date}" dateTime="{datetime}" '
            'quantity="100" tradePrice="52" ibCommission="-1" currency="USD" />'
        ).format(
            date=opened_at.strftime("%Y%m%d"),
            datetime=opened_at.replace(minute=40).strftime("%Y%m%d;%H%M%S"),
        ),
    ]

    if include_trigger_trade:
        rows.append(
            (
                '<Trade transactionID="TRIGGER1" assetCategory="STK" symbol="TRGSYM" '
                'conid="719999" tradeDate="{date}" dateTime="{datetime}" '
                'quantity="10" tradePrice="10" ibCommission="-1" currency="USD" />'
            ).format(
                date=opened_at.strftime("%Y%m%d"),
                datetime=opened_at.replace(hour=11, minute=0).strftime("%Y%m%d;%H%M%S"),
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
async def test_protected_open_trade_absorbs_new_closing_execution(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Open protected trade absorbs a new closing execution on re-import.

    With seed-lot carry-forward, a metadata-protected OPEN trade should close
    in place when the broker close appears, preserving metadata while linking
    the closing execution.
    """
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_account(client, headers)
    symbol, conid, tx_prefix = "PROT001", "700001", "PR"

    await _import_xml(
        client,
        headers,
        portfolio_id,
        account_id,
        _make_single_leg_xml(symbol, conid, tx_prefix, include_close=False),
    )

    trades_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades?limit=20", headers=headers
    )
    assert trades_resp.status_code == 200, trades_resp.text
    items = trades_resp.json()["data"]["items"]
    assert items
    protected_trade_id = items[0]["id"]

    patch_resp = await client.patch(
        f"/api/v1/portfolios/{portfolio_id}/trades/{protected_trade_id}",
        headers=headers,
        json={"journal": "protected-open-trade"},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    assert patch_resp.json()["data"]["is_manually_edited"] is True

    before_count_result = await db_session.execute(
        text("SELECT COUNT(*) FROM trades WHERE account_id = :account_id"),
        {"account_id": uuid.UUID(account_id)},
    )
    before_trade_count = int(before_count_result.scalar() or 0)

    # Re-import the same opening leg (no-op upsert) plus a NEW closing leg.
    second_import = await _import_xml(
        client,
        headers,
        portfolio_id,
        account_id,
        _make_single_leg_with_new_close_xml(
            symbol,
            conid,
            tx_prefix,
            close_tx_suffix="C2",
            close_day_offset=3,
        ),
    )
    assert second_import["trades_created"] == 0
    assert second_import["protected_positions_closed"] == 1
    assert second_import["unlinked_executions"] == 0
    assert not any("protected_unlinked_execution" in warning for warning in second_import["warnings"])

    after_count_result = await db_session.execute(
        text("SELECT COUNT(*) FROM trades WHERE account_id = :account_id"),
        {"account_id": uuid.UUID(account_id)},
    )
    after_trade_count = int(after_count_result.scalar() or 0)
    assert after_trade_count == before_trade_count

    reconciled_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{protected_trade_id}", headers=headers
    )
    assert reconciled_resp.status_code == 200, reconciled_resp.text
    reconciled = reconciled_resp.json()["data"]
    # Trade is closed in place and keeps metadata.
    assert reconciled["journal"] == "protected-open-trade"
    assert reconciled["closed_at"] is not None
    assert reconciled["exit_price"] is not None
    assert reconciled["pnl"] is not None
    assert reconciled["net_pnl"] is not None

    ex_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{protected_trade_id}/executions",
        headers=headers,
    )
    assert ex_resp.status_code == 200, ex_resp.text
    executions = ex_resp.json()["data"]
    assert len(executions) == 2
    assert all(exec_row["trade_id"] == protected_trade_id for exec_row in executions)


@pytest.mark.integration
async def test_closed_protected_trade_keeps_new_closing_execution_unlinked(
    client: AsyncClient,
) -> None:
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_account(client, headers)
    symbol, conid, tx_prefix = "PROTCLOSED", "700003", "PR3"

    await _import_xml(
        client,
        headers,
        portfolio_id,
        account_id,
        _make_single_leg_xml(symbol, conid, tx_prefix, include_close=True),
    )

    trades_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades?limit=20", headers=headers
    )
    assert trades_resp.status_code == 200, trades_resp.text
    items = trades_resp.json()["data"]["items"]
    assert items
    closed_trade_id = items[0]["id"]

    patch_resp = await client.patch(
        f"/api/v1/portfolios/{portfolio_id}/trades/{closed_trade_id}",
        headers=headers,
        json={"journal": "protected-closed-trade"},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    assert patch_resp.json()["data"]["is_manually_edited"] is True
    before_closed_at = patch_resp.json()["data"]["closed_at"]

    second_import = await _import_xml(
        client,
        headers,
        portfolio_id,
        account_id,
        _make_single_leg_with_new_close_xml(
            symbol,
            conid,
            tx_prefix,
            close_tx_suffix="C2",
            close_day_offset=3,
        ),
    )
    assert second_import["unlinked_executions"] == 1
    assert any(
        "protected_unlinked_execution" in warning
        for warning in second_import["warnings"]
    )

    closed_trade_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{closed_trade_id}",
        headers=headers,
    )
    assert closed_trade_resp.status_code == 200, closed_trade_resp.text
    closed_trade = closed_trade_resp.json()["data"]
    assert closed_trade["closed_at"] == before_closed_at
    assert closed_trade["journal"] == "protected-closed-trade"
    assert closed_trade["has_unlinked_executions"] is True


@pytest.mark.integration
async def test_close_by_import_preserves_trade_metadata_and_relations(
    client: AsyncClient,
) -> None:
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_account(client, headers)
    symbol, conid, tx_prefix = "PROTMETA", "700004", "PR4"

    await _import_xml(
        client,
        headers,
        portfolio_id,
        account_id,
        _make_single_leg_xml(symbol, conid, tx_prefix, include_close=False),
    )

    trades_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades?limit=20", headers=headers
    )
    assert trades_resp.status_code == 200, trades_resp.text
    trade_id = trades_resp.json()["data"]["items"][0]["id"]

    playbook_resp = await client.post(
        "/api/v1/playbooks",
        json={"name": f"PB-{uuid.uuid4().hex[:8]}", "description": ""},
        headers=headers,
    )
    assert playbook_resp.status_code == 201, playbook_resp.text
    playbook_id = playbook_resp.json()["data"]["id"]

    patch_trade = await client.patch(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}",
        headers=headers,
        json={
            "journal": "metadata-survives",
            "user_rating": 4,
            "tradingview_link": "https://tradingview.com/chart/protmeta",
            "image_urls": ["tradesensei/trades/protmeta.png"],
            "playbook_id": playbook_id,
        },
    )
    assert patch_trade.status_code == 200, patch_trade.text

    note_resp = await client.post(
        f"/api/v1/trades/{trade_id}/notes",
        json={"content": "important context"},
        headers=headers,
    )
    assert note_resp.status_code == 201, note_resp.text

    taxonomy_resp = await client.post(
        "/api/v1/taxonomies",
        json={
            "name": f"Tax-{uuid.uuid4().hex[:8]}",
            "scope": "trades",
            "color_hex": "#A1B2C3",
        },
        headers=headers,
    )
    assert taxonomy_resp.status_code == 201, taxonomy_resp.text
    taxonomy_id = taxonomy_resp.json()["data"]["id"]
    assign_taxonomy = await client.post(
        f"/api/v1/trades/{trade_id}/taxonomies",
        json={"taxonomy_id": taxonomy_id},
        headers=headers,
    )
    assert assign_taxonomy.status_code == 201, assign_taxonomy.text

    ann_def_resp = await client.post(
        "/api/v1/annotation-definitions",
        json={
            "name": f"Ann-{uuid.uuid4().hex[:8]}",
            "type": "int",
            "scope": "trades",
            "scale_labels": {"min": 1, "max": 10},
        },
        headers=headers,
    )
    assert ann_def_resp.status_code == 201, ann_def_resp.text
    ann_def_id = ann_def_resp.json()["data"]["id"]
    assign_annotation = await client.post(
        f"/api/v1/trades/{trade_id}/annotations/{ann_def_id}",
        json={"value": 7},
        headers=headers,
    )
    assert assign_annotation.status_code == 201, assign_annotation.text

    second_import = await _import_xml(
        client,
        headers,
        portfolio_id,
        account_id,
        _make_single_leg_xml(symbol, conid, tx_prefix, include_close=True),
    )
    assert second_import["unlinked_executions"] == 0

    detail_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}", headers=headers
    )
    assert detail_resp.status_code == 200, detail_resp.text
    detail = detail_resp.json()["data"]

    assert detail["closed_at"] is not None
    assert detail["journal"] == "metadata-survives"
    assert detail["user_rating"] == 4
    assert detail["tradingview_link"] == "https://tradingview.com/chart/protmeta"
    assert detail["image_urls"] == ["tradesensei/trades/protmeta.png"]
    assert detail["playbook_id"] == playbook_id
    assert any(note["content"] == "important context" for note in detail["trade_notes"])
    assert any(taxonomy["id"] == taxonomy_id for taxonomy in detail["taxonomies"])
    assert any(
        annotation["annotation_definition_id"] == ann_def_id
        for annotation in detail["annotations"]
    )


@pytest.mark.integration
async def test_protected_and_non_protected_same_symbol_coexist_through_rebuild(
    client: AsyncClient,
) -> None:
    """A protected and non-protected trade on one symbol must coexist after rebuild."""
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_account(client, headers)

    await _import_xml(
        client,
        headers,
        portfolio_id,
        account_id,
        _make_same_symbol_two_contracts_xml(include_trigger_trade=False),
    )

    trades_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades?limit=50", headers=headers
    )
    assert trades_resp.status_code == 200, trades_resp.text
    same_symbol_trades = [
        trade for trade in trades_resp.json()["data"]["items"] if trade["symbol"] == "SAMESYM"
    ]
    assert len(same_symbol_trades) == 2

    protected_trade_id = same_symbol_trades[0]["id"]
    protect_resp = await client.patch(
        f"/api/v1/portfolios/{portfolio_id}/trades/{protected_trade_id}",
        headers=headers,
        json={"journal": "protect-one-same-symbol"},
    )
    assert protect_resp.status_code == 200, protect_resp.text
    assert protect_resp.json()["data"]["is_manually_edited"] is True

    second_import = await _import_xml(
        client,
        headers,
        portfolio_id,
        account_id,
        _make_same_symbol_two_contracts_xml(include_trigger_trade=True),
    )
    assert int(second_import["raw_transactions_created"]) > 0

    protected_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{protected_trade_id}", headers=headers
    )
    assert protected_resp.status_code == 200, protected_resp.text
    protected_trade = protected_resp.json()["data"]
    assert protected_trade["journal"] == "protect-one-same-symbol"
    assert protected_trade["is_manually_edited"] is True

    after_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades?limit=100", headers=headers
    )
    assert after_resp.status_code == 200, after_resp.text
    after_trades = after_resp.json()["data"]["items"]

    same_symbol_after = [trade for trade in after_trades if trade["symbol"] == "SAMESYM"]
    assert len(same_symbol_after) == 2
    assert any(trade["id"] == protected_trade_id for trade in same_symbol_after)
    assert any(trade["id"] != protected_trade_id for trade in same_symbol_after)


@pytest.mark.integration
async def test_merged_trade_survives_subsequent_import_with_legs_intact(
    client: AsyncClient,
) -> None:
    """Merged trade keeps identity, structure, and linked legs across import rebuild."""
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_account(client, headers)

    await _import_xml(
        client,
        headers,
        portfolio_id,
        account_id,
        _make_same_symbol_two_contracts_xml(include_trigger_trade=False),
    )

    trades_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades?limit=50", headers=headers
    )
    assert trades_resp.status_code == 200, trades_resp.text
    same_symbol_trades = [
        trade for trade in trades_resp.json()["data"]["items"] if trade["symbol"] == "SAMESYM"
    ]
    assert len(same_symbol_trades) == 2

    merge_resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades/merge",
        headers=headers,
        json={"trade_ids": [same_symbol_trades[0]["id"], same_symbol_trades[1]["id"]]},
    )
    assert merge_resp.status_code == 200, merge_resp.text
    merged_trade = merge_resp.json()["data"]
    merged_trade_id = merged_trade["id"]
    assert merged_trade["is_manually_edited"] is True
    assert merged_trade["is_combo"] is True

    before_exec_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{merged_trade_id}/executions",
        headers=headers,
    )
    assert before_exec_resp.status_code == 200, before_exec_resp.text
    before_execs = before_exec_resp.json()["data"]
    before_exec_ids = {row["id"] for row in before_execs}
    assert len(before_exec_ids) == 2
    assert all(row["trade_id"] == merged_trade_id for row in before_execs)

    second_import = await _import_xml(
        client,
        headers,
        portfolio_id,
        account_id,
        _make_same_symbol_two_contracts_xml(include_trigger_trade=True),
    )
    assert int(second_import["raw_transactions_created"]) > 0

    merged_after_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{merged_trade_id}", headers=headers
    )
    assert merged_after_resp.status_code == 200, merged_after_resp.text
    merged_after = merged_after_resp.json()["data"]
    assert merged_after["id"] == merged_trade_id
    assert merged_after["is_manually_edited"] is True
    assert merged_after["is_combo"] is True

    after_exec_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{merged_trade_id}/executions",
        headers=headers,
    )
    assert after_exec_resp.status_code == 200, after_exec_resp.text
    after_execs = after_exec_resp.json()["data"]
    after_exec_ids = {row["id"] for row in after_execs}
    assert after_exec_ids == before_exec_ids
    assert all(row["trade_id"] == merged_trade_id for row in after_execs)


@pytest.mark.integration
async def test_reconciled_import_leaves_zero_orphaned_imported_executions(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Task 15.2: after a rebuild reconciles a protected trade, no imported
    execution should be left with ``trade_id IS NULL`` for the account.

    Regression coverage for the orphaned-execution defect (D8): before the
    reconcile-before-skip fix, the new closing leg landed unlinked.
    """
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_account(client, headers)
    symbol, conid, tx_prefix = "PROT002", "700002", "PR2"

    await _import_xml(
        client,
        headers,
        portfolio_id,
        account_id,
        _make_single_leg_xml(symbol, conid, tx_prefix, include_close=False),
    )

    trades_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades?limit=20", headers=headers
    )
    assert trades_resp.status_code == 200, trades_resp.text
    items = trades_resp.json()["data"]["items"]
    assert items
    protected_trade_id = items[0]["id"]

    patch_resp = await client.patch(
        f"/api/v1/portfolios/{portfolio_id}/trades/{protected_trade_id}",
        headers=headers,
        json={"journal": "zero-orphan-check"},
    )
    assert patch_resp.status_code == 200, patch_resp.text

    second_import = await _import_xml(
        client,
        headers,
        portfolio_id,
        account_id,
        _make_single_leg_xml(symbol, conid, tx_prefix, include_close=True),
    )

    assert second_import["unlinked_executions"] == 0
    assert not any("protected_unlinked_execution" in warning for warning in second_import["warnings"])

    result = await db_session.execute(
        text(
            "SELECT COUNT(*) FROM logical_executions "
            "WHERE origin='imported' AND deleted=false AND trade_id IS NULL "
            "AND account_id = :account_id"
        ),
        {"account_id": uuid.UUID(account_id)},
    )
    assert result.scalar() == 0


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
async def test_reset_to_broker_state_hard_deletes_and_releases_guard(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Task 15.6 (D11): ``DELETE .../executions/{id}?reset=true`` on an
    imported leg returns 204, physically removes the ``LogicalExecution``
    row, and releases the linked ``BrokerRawTransaction.suppressed`` guard.

    Re-materialisation on a subsequent plain re-import (the third THEN of
    the "Reset re-materialises the broker leg on next import" scenario) is
    covered separately by
    ``test_reset_then_plain_reimport_rematerialises_the_execution`` below.
    """
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_account(client, headers)
    symbol, conid, tx_prefix = "RST001", "700003", "RS"
    xml_content = _make_single_leg_xml(symbol, conid, tx_prefix, include_close=False)

    first_import = await _import_xml(client, headers, portfolio_id, account_id, xml_content)
    assert int(first_import["raw_transactions_created"]) == 1

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
    execution_id = ex_resp.json()["data"][0]["id"]

    delete_resp = await client.delete(
        f"/api/v1/portfolios/{portfolio_id}/executions/{execution_id}?reset=true",
        headers=headers,
    )
    assert delete_resp.status_code == 204, delete_resp.text

    remaining = await db_session.execute(
        text("SELECT COUNT(*) FROM logical_executions WHERE id = :id"),
        {"id": uuid.UUID(execution_id)},
    )
    assert remaining.scalar() == 0

    suppressed_after_reset = await db_session.execute(
        text("SELECT suppressed FROM broker_raw_transactions WHERE id LIKE :pat"),
        {"pat": f"%{tx_prefix}E1"},
    )
    assert suppressed_after_reset.scalar() is False


@pytest.mark.integration
async def test_reset_then_plain_reimport_rematerialises_the_execution(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Task 15.6 (D11): a plain re-import after reset recreates the
    execution/trade from the (still-present, now un-suppressed) broker raw
    transaction — the "Reset re-materialises the broker leg on next import"
    spec scenario.

    Regression coverage: ``bulk_upsert`` uses ``ON CONFLICT (id) DO
    NOTHING``, so a raw row released by reset is never reported as "newly
    inserted" on a plain re-import. ``ImportService`` additionally checks
    ``BrokerRawTransactionRepository.list_released_without_execution`` for
    un-suppressed rows with no active/any execution and materialises those
    too, so the zero-insert guard (D5) does not wrongly skip the rebuild.
    """
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_account(client, headers)
    symbol, conid, tx_prefix = "RST002", "700004", "RS2"
    xml_content = _make_single_leg_xml(symbol, conid, tx_prefix, include_close=False)

    await _import_xml(client, headers, portfolio_id, account_id, xml_content)

    trades_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades?limit=20", headers=headers
    )
    trade_id = trades_resp.json()["data"]["items"][0]["id"]
    ex_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}/executions",
        headers=headers,
    )
    execution_id = ex_resp.json()["data"][0]["id"]

    delete_resp = await client.delete(
        f"/api/v1/portfolios/{portfolio_id}/executions/{execution_id}?reset=true",
        headers=headers,
    )
    assert delete_resp.status_code == 204, delete_resp.text

    # raw_transactions_created stays 0 — the raw row was never removed, only
    # released — but the execution/trade must still re-materialise.
    second_import = await _import_xml(client, headers, portfolio_id, account_id, xml_content)
    assert int(second_import["raw_transactions_created"]) == 0

    trades_resp_2 = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades?limit=20", headers=headers
    )
    rematerialised = trades_resp_2.json()["data"]["items"]
    matching_trades = [trade for trade in rematerialised if trade["symbol"] == symbol]
    assert len(matching_trades) == 1, (
        "Reset-then-reimport must re-materialise onto the original trade, "
        f"not create a duplicate: found {len(matching_trades)} trades for {symbol}"
    )

    suppressed_after_reimport = await db_session.execute(
        text("SELECT suppressed FROM broker_raw_transactions WHERE id LIKE :pat"),
        {"pat": f"%{tx_prefix}E1"},
    )
    assert suppressed_after_reimport.scalar() is False

    # No orphaned executions: the released raw row must materialise onto a
    # LogicalExecution that is actually linked to a trade, not left dangling
    # with trade_id IS NULL (the exact defect class this OpenSpec change
    # exists to eliminate).
    orphaned_executions = await db_session.execute(
        text(
            "SELECT COUNT(*) FROM logical_executions "
            "WHERE account_id = :account_id AND trade_id IS NULL AND deleted = false"
        ),
        {"account_id": account_id},
    )
    assert orphaned_executions.scalar() == 0


@pytest.mark.integration
async def test_default_delete_on_imported_execution_remains_soft_delete(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Task 15.6 (D11): default DELETE on imported legs remains soft-delete.

    This guards the non-reset contract: without ``?reset=true``, imported
    executions must remain in-place with ``deleted=true`` (not physically
    removed), preserving explicit user suppression intent.
    """
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_account(client, headers)
    symbol, conid, tx_prefix = "RST003", "700005", "RS3"
    xml_content = _make_single_leg_xml(symbol, conid, tx_prefix, include_close=False)

    await _import_xml(client, headers, portfolio_id, account_id, xml_content)

    trades_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades?limit=20", headers=headers
    )
    trade_id = trades_resp.json()["data"]["items"][0]["id"]
    ex_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}/executions",
        headers=headers,
    )
    execution_id = ex_resp.json()["data"][0]["id"]

    delete_resp = await client.delete(
        f"/api/v1/portfolios/{portfolio_id}/executions/{execution_id}",
        headers=headers,
    )
    assert delete_resp.status_code == 200, delete_resp.text
    assert delete_resp.json()["data"]["deleted"] is True

    remaining = await db_session.execute(
        text("SELECT COUNT(*) FROM logical_executions WHERE id = :id"),
        {"id": uuid.UUID(execution_id)},
    )
    assert remaining.scalar() == 1

    # Default imported-delete keeps the BRT row untouched (no forced release).
    # The fixture's initial import path may leave it suppressed either way
    # depending on prior state, but it must remain present.
    raw_row_exists = await db_session.execute(
        text("SELECT COUNT(*) FROM broker_raw_transactions WHERE id LIKE :pat"),
        {"pat": f"%{tx_prefix}E1"},
    )
    assert raw_row_exists.scalar() == 1


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
