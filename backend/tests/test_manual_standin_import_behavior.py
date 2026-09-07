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

"""Integration tests for manual stand-in import suppression behavior."""

import uuid
from datetime import UTC, datetime
from typing import cast

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


_REGISTER_URL = "/api/v1/auth/register"
_TOKEN_URL = "/api/v1/auth/token"
_PORTFOLIOS_URL = "/api/v1/portfolios"


async def _auth_headers(client: AsyncClient, suffix: str) -> dict[str, str]:
    username = f"standin_{suffix}"
    email = f"standin_{suffix}@example.com"
    password = "StandIn@99"
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
    portfolio_res = await client.post(
        _PORTFOLIOS_URL,
        headers=headers,
        json={"name": "Standin Portfolio", "base_currency": "USD"},
    )
    assert portfolio_res.status_code == 201, portfolio_res.text
    portfolio_id = str(portfolio_res.json()["data"]["id"])

    res = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        headers=headers,
        json={"name": "Standin Account", "type": "ibkr", "currency": "USD"},
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
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/imports/upload",
        headers=headers,
        data={"broker": "ibkr", "account_id": account_id},
        files={"file": ("standin.xml", xml_content, "application/xml")},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _make_open_only_xml(symbol: str, conid: str, tx_prefix: str) -> bytes:
    opened_at = datetime(2026, 4, 1, 9, 30, tzinfo=UTC)
    row = (
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
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<FlexQueryResponse><FlexStatements><FlexStatement><Trades>"
        + row
        + "</Trades></FlexStatement>"
        + "</FlexStatements></FlexQueryResponse>"
    )
    return xml.encode("utf-8")


def _make_open_plus_new_close_xml(
    symbol: str,
    conid: str,
    tx_prefix: str,
    *,
    close_tx_suffix: str,
    close_price: str,
    close_day_offset: int,
) -> bytes:
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


@pytest.mark.integration
async def test_manual_standin_unlinked_is_flagged_and_trade_count_unchanged(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_account(client, headers)
    symbol, conid, tx_prefix = "MANSTAND", "710101", "MS"

    await _import_xml(
        client,
        headers,
        portfolio_id,
        account_id,
        _make_open_only_xml(symbol, conid, tx_prefix),
    )

    trades_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades?limit=20",
        headers=headers,
    )
    assert trades_resp.status_code == 200, trades_resp.text
    trade_id = trades_resp.json()["data"]["items"][0]["id"]

    partial_close_resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}/partial-close",
        headers=headers,
        json={
            "quantity": "100",
            "exit_price": "54.00",
            "exit_commission": "1.00",
            "closed_at": datetime(2026, 4, 2, 10, 0, tzinfo=UTC).isoformat(),
        },
    )
    assert partial_close_resp.status_code == 200, partial_close_resp.text

    trade_detail_before_import = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}",
        headers=headers,
    )
    assert trade_detail_before_import.status_code == 200, trade_detail_before_import.text
    assert trade_detail_before_import.json()["data"]["is_manually_edited"] is False

    count_before = await db_session.execute(
        text("SELECT COUNT(*) FROM trades WHERE account_id = :account_id"),
        {"account_id": uuid.UUID(account_id)},
    )
    before_trade_count = int(count_before.scalar() or 0)

    second_import = await _import_xml(
        client,
        headers,
        portfolio_id,
        account_id,
        _make_open_plus_new_close_xml(
            symbol,
            conid,
            tx_prefix,
            close_tx_suffix="C2",
            close_price="55",
            close_day_offset=3,
        ),
    )

    warnings = cast(list[str], second_import["warnings"])
    assert second_import["unlinked_executions"] == 1
    assert any(
        "manual_standin_unlinked_execution" in warning
        for warning in warnings
    )

    count_after = await db_session.execute(
        text("SELECT COUNT(*) FROM trades WHERE account_id = :account_id"),
        {"account_id": uuid.UUID(account_id)},
    )
    after_trade_count = int(count_after.scalar() or 0)
    assert after_trade_count == before_trade_count

    flagged_trades_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades?has_unlinked_executions=true&limit=20",
        headers=headers,
    )
    assert flagged_trades_resp.status_code == 200, flagged_trades_resp.text
    flagged_items = flagged_trades_resp.json()["data"]["items"]
    assert flagged_items
    assert any(item["symbol"] == symbol for item in flagged_items)


@pytest.mark.integration
async def test_linked_manual_leg_does_not_suppress_orphan_sentinel(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """When manual leg has source_id set, suppression must not apply."""
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_account(client, headers)
    symbol, conid, tx_prefix = "MANNOSUP", "710150", "MN"

    await _import_xml(
        client,
        headers,
        portfolio_id,
        account_id,
        _make_open_only_xml(symbol, conid, tx_prefix),
    )

    trades_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades?limit=20",
        headers=headers,
    )
    assert trades_resp.status_code == 200, trades_resp.text
    trade_id = trades_resp.json()["data"]["items"][0]["id"]

    close_resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}/partial-close",
        headers=headers,
        json={
            "quantity": "100",
            "exit_price": "54.00",
            "exit_commission": "1.00",
            "closed_at": datetime(2026, 4, 2, 10, 0, tzinfo=UTC).isoformat(),
        },
    )
    assert close_resp.status_code == 200, close_resp.text

    trade_meta = await db_session.execute(
        text("SELECT user_id FROM trades WHERE id = :trade_id"),
        {"trade_id": uuid.UUID(trade_id)},
    )
    user_id = trade_meta.scalar_one()

    manual_exec_meta = await db_session.execute(
        text(
            "SELECT id FROM logical_executions "
            "WHERE trade_id = :trade_id AND origin = 'manual' AND deleted = false "
            "ORDER BY executed_at DESC LIMIT 1"
        ),
        {"trade_id": uuid.UUID(trade_id)},
    )
    manual_exec_id = manual_exec_meta.scalar_one()

    linked_raw_id = f"{user_id}:manual-link-{uuid.uuid4().hex[:8]}"
    await db_session.execute(
        text(
            """
            INSERT INTO broker_raw_transactions (
                id, user_id, account_id, broker_type, symbol, conid, asset_class,
                direction, quantity, price, commission, executed_at, pnl, currency,
                multiplier, open_close, raw_data, suppressed, created_at
            ) VALUES (
                :id, :user_id, :account_id, 'ibkr', :symbol, :conid, 'EQUITY',
                'SHORT', 100, 54, 1, :executed_at, 400, 'USD',
                1, 'C', '{}'::jsonb, true, NOW()
            )
            """
        ),
        {
            "id": linked_raw_id,
            "user_id": user_id,
            "account_id": uuid.UUID(account_id),
            "symbol": symbol,
            "conid": conid,
            "executed_at": datetime(2026, 4, 2, 10, 0, tzinfo=UTC),
        },
    )
    await db_session.execute(
        text("UPDATE logical_executions SET source_id = :source_id WHERE id = :execution_id"),
        {
            "source_id": linked_raw_id,
            "execution_id": manual_exec_id,
        },
    )
    await db_session.commit()

    import_result = await _import_xml(
        client,
        headers,
        portfolio_id,
        account_id,
        _make_open_plus_new_close_xml(
            symbol,
            conid,
            tx_prefix,
            close_tx_suffix="C2",
            close_price="55",
            close_day_offset=3,
        ),
    )

    assert import_result["unlinked_executions"] == 0

    sentinel_count = await db_session.execute(
        text(
            "SELECT COUNT(*) FROM trades "
            "WHERE account_id = :account_id AND symbol = :symbol AND entry_price = 0.001"
        ),
        {
            "account_id": uuid.UUID(account_id),
            "symbol": symbol,
        },
    )
    assert int(sentinel_count.scalar() or 0) >= 1


@pytest.mark.integration
async def test_manual_standin_delete_resolution_clears_unlinked_flag(
    client: AsyncClient,
) -> None:
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_account(client, headers)
    symbol, conid, tx_prefix = "MANLINK", "710102", "ML"

    await _import_xml(
        client,
        headers,
        portfolio_id,
        account_id,
        _make_open_only_xml(symbol, conid, tx_prefix),
    )

    trades_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades?limit=20",
        headers=headers,
    )
    assert trades_resp.status_code == 200, trades_resp.text
    trade_id = trades_resp.json()["data"]["items"][0]["id"]

    partial_close_resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}/partial-close",
        headers=headers,
        json={
            "quantity": "100",
            "exit_price": "54.00",
            "exit_commission": "1.00",
            "closed_at": datetime(2026, 4, 2, 10, 0, tzinfo=UTC).isoformat(),
        },
    )
    assert partial_close_resp.status_code == 200, partial_close_resp.text

    await _import_xml(
        client,
        headers,
        portfolio_id,
        account_id,
        _make_open_plus_new_close_xml(
            symbol,
            conid,
            tx_prefix,
            close_tx_suffix="C2",
            close_price="55",
            close_day_offset=3,
        ),
    )

    executions_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}/executions",
        headers=headers,
    )
    assert executions_resp.status_code == 200, executions_resp.text
    executions = executions_resp.json()["data"]
    manual_execution = next(
        execution for execution in executions if execution["origin"] == "manual"
    )

    delete_resp = await client.delete(
        f"/api/v1/portfolios/{portfolio_id}/executions/{manual_execution['id']}",
        headers=headers,
    )
    assert delete_resp.status_code == 204, delete_resp.text

    reimport_after_delete = await _import_xml(
        client,
        headers,
        portfolio_id,
        account_id,
        _make_open_plus_new_close_xml(
            symbol,
            conid,
            tx_prefix,
            close_tx_suffix="C3",
            close_price="55",
            close_day_offset=4,
        ),
    )
    assert reimport_after_delete["unlinked_executions"] == 0

    trade_detail_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}",
        headers=headers,
    )
    assert trade_detail_resp.status_code == 200, trade_detail_resp.text
    trade_detail = trade_detail_resp.json()["data"]
    assert trade_detail["has_unlinked_executions"] is False
    assert trade_detail["exit_price"] is not None


@pytest.mark.integration
async def test_manual_standin_link_resolution_clears_unlinked_without_duplicate(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Linking manual leg to broker raw after reset clears unlinked and keeps trade count stable."""
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_account(client, headers)
    symbol, conid, tx_prefix = "MANLNK2", "710160", "M2"

    await _import_xml(
        client,
        headers,
        portfolio_id,
        account_id,
        _make_open_only_xml(symbol, conid, tx_prefix),
    )

    trades_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades?limit=20",
        headers=headers,
    )
    assert trades_resp.status_code == 200, trades_resp.text
    trade_id = trades_resp.json()["data"]["items"][0]["id"]

    close_resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}/partial-close",
        headers=headers,
        json={
            "quantity": "100",
            "exit_price": "54.00",
            "exit_commission": "1.00",
            "closed_at": datetime(2026, 4, 2, 10, 0, tzinfo=UTC).isoformat(),
        },
    )
    assert close_resp.status_code == 200, close_resp.text

    count_before = await db_session.execute(
        text("SELECT COUNT(*) FROM trades WHERE account_id = :account_id"),
        {"account_id": uuid.UUID(account_id)},
    )
    before_trade_count = int(count_before.scalar() or 0)

    await _import_xml(
        client,
        headers,
        portfolio_id,
        account_id,
        _make_open_plus_new_close_xml(
            symbol,
            conid,
            tx_prefix,
            close_tx_suffix="C2",
            close_price="55",
            close_day_offset=3,
        ),
    )

    unresolved = await db_session.execute(
        text(
            "SELECT id, source_id FROM logical_executions "
            "WHERE account_id = :account_id AND symbol = :symbol "
            "AND origin = 'imported' AND trade_id IS NULL AND deleted = false "
            "ORDER BY executed_at DESC LIMIT 1"
        ),
        {
            "account_id": uuid.UUID(account_id),
            "symbol": symbol,
        },
    )
    unresolved_row = unresolved.first()
    assert unresolved_row is not None
    unresolved_execution_id = unresolved_row[0]
    unresolved_source_id = unresolved_row[1]
    assert unresolved_source_id is not None

    reset_resp = await client.delete(
        f"/api/v1/portfolios/{portfolio_id}/executions/{unresolved_execution_id}?reset=true",
        headers=headers,
    )
    assert reset_resp.status_code == 204, reset_resp.text

    trade_execs_resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}/executions",
        headers=headers,
    )
    assert trade_execs_resp.status_code == 200, trade_execs_resp.text
    manual_execution = next(
        execution for execution in trade_execs_resp.json()["data"] if execution["origin"] == "manual"
    )

    link_resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/executions/{manual_execution['id']}/link-broker-transaction",
        headers=headers,
        json={"raw_transaction_id": unresolved_source_id},
    )
    assert link_resp.status_code == 200, link_resp.text

    reimport_after_link = await _import_xml(
        client,
        headers,
        portfolio_id,
        account_id,
        _make_open_plus_new_close_xml(
            symbol,
            conid,
            tx_prefix,
            close_tx_suffix="C2",
            close_price="55",
            close_day_offset=3,
        ),
    )
    assert reimport_after_link["unlinked_executions"] == 0

    trade_detail = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}",
        headers=headers,
    )
    assert trade_detail.status_code == 200, trade_detail.text
    assert trade_detail.json()["data"]["has_unlinked_executions"] is False

    trade_execs_after = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}/executions",
        headers=headers,
    )
    assert trade_execs_after.status_code == 200, trade_execs_after.text
    rows = trade_execs_after.json()["data"]
    assert not any(
        row["origin"] == "imported" and row["source_id"] == unresolved_source_id
        for row in rows
    )

    count_after = await db_session.execute(
        text("SELECT COUNT(*) FROM trades WHERE account_id = :account_id"),
        {"account_id": uuid.UUID(account_id)},
    )
    after_trade_count = int(count_after.scalar() or 0)
    assert after_trade_count == before_trade_count
