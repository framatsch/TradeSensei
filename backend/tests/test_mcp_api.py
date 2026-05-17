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

"""Integration tests for MCP transport endpoints."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.annotation_definition import AnnotationDefinition
from app.models.playbook import Playbook
from app.models.taxonomy import Taxonomy
from app.models.trade import Trade
from app.models.trade_annotation import TradeAnnotation
from app.models.trade_taxonomy import TradeTaxonomy
from tests.test_pat_api import _register_and_login


async def _create_pat(client: AsyncClient) -> str:
    headers = await _register_and_login(client)
    created = await client.post(
        "/api/v1/settings/tokens",
        json={"name": f"MCP-{uuid.uuid4().hex[:6]}"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    return str(created.json()["data"]["token"])


async def _create_pat_for_headers(client: AsyncClient, headers: dict[str, str]) -> str:
    created = await client.post(
        "/api/v1/settings/tokens",
        json={"name": f"MCP-{uuid.uuid4().hex[:6]}"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    return str(created.json()["data"]["token"])


async def _auth_and_pat(client: AsyncClient) -> tuple[dict[str, str], str]:
    headers = await _register_and_login(client)
    token = await _create_pat_for_headers(client, headers)
    return headers, token


async def _create_portfolio_and_account(
    client: AsyncClient,
    headers: dict[str, str],
    suffix: str,
) -> tuple[str, str]:
    portfolio = await client.post(
        "/api/v1/portfolios",
        json={"name": f"MCP Portfolio {suffix}", "base_currency": "USD"},
        headers=headers,
    )
    assert portfolio.status_code == 201, portfolio.text
    portfolio_id = portfolio.json()["data"]["id"]

    account = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        json={"name": f"MCP Account {suffix}", "type": "manual", "currency": "USD"},
        headers=headers,
    )
    assert account.status_code == 201, account.text
    return portfolio_id, account.json()["data"]["id"]


async def _create_trade(
    client: AsyncClient,
    headers: dict[str, str],
    portfolio_id: str,
    account_id: str,
    *,
    symbol: str,
    opened_at: datetime,
    pnl: str | None = None,
) -> str:
    payload: dict[str, object] = {
        "account_id": account_id,
        "symbol": symbol,
        "direction": "LONG",
        "asset_class": "EQUITY",
        "quantity": "10",
        "entry_price": "100",
        "opened_at": opened_at.isoformat(),
    }
    if pnl is not None:
        payload.update(
            {
                "closed_at": opened_at.isoformat(),
                "exit_price": "101",
                "pnl": pnl,
                "net_pnl": pnl,
            }
        )

    create = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        json=payload,
        headers=headers,
    )
    assert create.status_code == 201, create.text
    return create.json()["data"]["id"]


async def _mcp_tools_call(
    client: AsyncClient,
    token: str,
    *,
    tool_name: str,
    arguments: dict[str, object],
    message_id: int = 1,
) -> dict[str, object]:
    response = await client.post(
        "/mcp/messages",
        json={
            "jsonrpc": "2.0",
            "id": message_id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.integration
async def test_mcp_sse_missing_auth_returns_401(client: AsyncClient) -> None:
    response = await client.get("/mcp/sse")
    assert response.status_code == 401


@pytest.mark.integration
async def test_mcp_sse_invalid_pat_returns_401(client: AsyncClient) -> None:
    response = await client.get(
        "/mcp/sse",
        headers={"Authorization": "Bearer not-a-valid-token"},
    )
    assert response.status_code == 401


@pytest.mark.integration
@patch("app.api.mcp._KEEPALIVE_INTERVAL", 0.05)
async def test_mcp_sse_valid_pat_returns_ready_event(client: AsyncClient) -> None:
    token = await _create_pat(client)

    async with client.stream(
        "GET",
        "/mcp/sse",
        headers={"Authorization": f"Bearer {token}", "x-test-no-sse-keepalive": "true"},
    ) as response:
        assert response.status_code == 200, await response.aread()
        assert response.headers["content-type"].startswith("text/event-stream")
        first_line = ""
        async for line in response.aiter_lines():
            if line.startswith("event:"):
                first_line = line
                break

    assert "event: ready" in first_line


@pytest.mark.integration
async def test_mcp_sse_invalid_session_id_returns_400(client: AsyncClient) -> None:
    token = await _create_pat(client)
    response = await client.get(
        "/mcp/sse?session_id=bad!*session",
        headers={"Authorization": f"Bearer {token}", "x-test-no-sse-keepalive": "true"},
    )
    assert response.status_code == 400


@pytest.mark.integration
@patch("app.api.mcp._KEEPALIVE_INTERVAL", 0.05)
async def test_mcp_sse_valid_session_id_echoed_in_ready_event(client: AsyncClient) -> None:
    token = await _create_pat(client)
    session_id = "session_123"

    async with client.stream(
        "GET",
        f"/mcp/sse?session_id={session_id}",
        headers={"Authorization": f"Bearer {token}", "x-test-no-sse-keepalive": "true"},
    ) as response:
        assert response.status_code == 200, await response.aread()
        first_line = ""
        session_data = ""
        async for line in response.aiter_lines():
            if line.startswith("event:"):
                first_line = line
            if line.startswith("data:"):
                session_data = line
                break

    assert "event: ready" in first_line
    assert "session_id" in session_data
    assert session_id in session_data


@pytest.mark.integration
async def test_mcp_messages_without_pat_returns_401(client: AsyncClient) -> None:
    response = await client.post(
        "/mcp/messages",
        json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
    )
    assert response.status_code == 401


@pytest.mark.integration
async def test_mcp_tools_list_returns_all_domain_tools(client: AsyncClient) -> None:
    _headers, token = await _auth_and_pat(client)
    response = await client.post(
        "/mcp/messages",
        json={"jsonrpc": "2.0", "id": 11, "method": "tools/list"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    tools = payload["result"]["tools"]

    names = {tool["name"] for tool in tools}
    assert names == {
        "get_metadata_schema",
        "list_portfolios",
        "list_accounts",
        "search_trades_advanced",
        "sync_trade_metadata",
        "create_strategy_playbook",
    }
    for tool in tools:
        assert "description" in tool
        assert "inputSchema" in tool


@pytest.mark.integration
async def test_get_metadata_schema_excludes_archived_and_supports_empty(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers, token = await _auth_and_pat(client)
    me = await client.get("/api/v1/users/me", headers=headers)
    assert me.status_code == 200, me.text
    user_id = uuid.UUID(str(me.json()["data"]["id"]))

    await db_session.execute(
        Taxonomy.__table__.update()
        .where(Taxonomy.user_id == user_id)
        .values(is_archived=True),
    )
    await db_session.execute(
        AnnotationDefinition.__table__.update()
        .where(AnnotationDefinition.user_id == user_id)
        .values(is_archived=True),
    )
    await db_session.flush()

    empty_payload = await _mcp_tools_call(
        client,
        token,
        tool_name="get_metadata_schema",
        arguments={},
        message_id=12,
    )
    assert empty_payload["result"] == {"taxonomies": [], "annotation_definitions": []}

    create_taxonomy = await client.post(
        "/api/v1/taxonomies",
        json={"name": "Momentum", "scope": "trades", "color_hex": "#112233"},
        headers=headers,
    )
    assert create_taxonomy.status_code == 201, create_taxonomy.text
    taxonomy_id = create_taxonomy.json()["data"]["id"]

    create_definition = await client.post(
        "/api/v1/annotation-definitions",
        json={"name": "Mood", "type": "int", "scope": "trades", "scale_labels": {"min": 1, "max": 10}},
        headers=headers,
    )
    assert create_definition.status_code == 201, create_definition.text
    definition_id = create_definition.json()["data"]["id"]

    payload = await _mcp_tools_call(
        client,
        token,
        tool_name="get_metadata_schema",
        arguments={},
        message_id=13,
    )
    taxonomy_ids = {item["id"] for item in payload["result"]["taxonomies"]}
    definition_ids = {item["id"] for item in payload["result"]["annotation_definitions"]}
    assert taxonomy_id in taxonomy_ids
    assert definition_id in definition_ids


@pytest.mark.integration
async def test_list_portfolios_returns_user_portfolios(client: AsyncClient) -> None:
    headers, token = await _auth_and_pat(client)
    me = await client.get("/api/v1/users/me", headers=headers)
    user_id = uuid.UUID(str(me.json()["data"]["id"]))

    payload = await _mcp_tools_call(client, token, tool_name="list_portfolios", arguments={}, message_id=40)
    assert payload["result"]["portfolios"] == []

    created = await client.post(
        "/api/v1/portfolios",
        json={"name": "Schwab Main", "base_currency": "USD"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    portfolio_id = created.json()["data"]["id"]

    payload = await _mcp_tools_call(client, token, tool_name="list_portfolios", arguments={}, message_id=41)
    portfolios = payload["result"]["portfolios"]
    assert len(portfolios) == 1
    assert portfolios[0]["id"] == portfolio_id
    assert portfolios[0]["name"] == "Schwab Main"
    assert portfolios[0]["base_currency"] == "USD"


@pytest.mark.integration
async def test_list_accounts_filters_by_portfolio_and_broker(client: AsyncClient) -> None:
    headers, token = await _auth_and_pat(client)

    payload = await _mcp_tools_call(client, token, tool_name="list_accounts", arguments={}, message_id=50)
    assert payload["result"]["accounts"] == []

    portfolio = await client.post(
        "/api/v1/portfolios",
        json={"name": "My PF", "base_currency": "USD"},
        headers=headers,
    )
    assert portfolio.status_code == 201, portfolio.text
    pf_id = portfolio.json()["data"]["id"]

    acct1 = await client.post(
        f"/api/v1/portfolios/{pf_id}/accounts",
        json={"name": "Schwab", "type": "schwab", "currency": "USD", "account_number": "U9876543"},
        headers=headers,
    )
    assert acct1.status_code == 201, acct1.text
    acct1_id = acct1.json()["data"]["id"]

    acct2 = await client.post(
        f"/api/v1/portfolios/{pf_id}/accounts",
        json={"name": "IBKR Main", "type": "ibkr", "currency": "EUR", "account_number": "IB123456"},
        headers=headers,
    )
    assert acct2.status_code == 201, acct2.text
    acct2_id = acct2.json()["data"]["id"]

    # All accounts for portfolio
    payload = await _mcp_tools_call(
        client, token, tool_name="list_accounts",
        arguments={"portfolio_id": pf_id}, message_id=51,
    )
    accounts = payload["result"]["accounts"]
    assert len(accounts) == 2

    # Filter by broker
    payload = await _mcp_tools_call(
        client, token, tool_name="list_accounts",
        arguments={"portfolio_id": pf_id, "broker": "schwab"}, message_id=52,
    )
    accounts = payload["result"]["accounts"]
    assert len(accounts) == 1
    assert accounts[0]["id"] == acct1_id
    assert accounts[0]["name"] == "Schwab"
    assert accounts[0]["broker"] == "schwab"
    assert accounts[0]["account_number_masked"] == "****6543"
    assert accounts[0]["currency"] == "USD"
    assert accounts[0]["portfolio_id"] == pf_id

    # Filter by broker only (no portfolio_id)
    payload = await _mcp_tools_call(
        client, token, tool_name="list_accounts",
        arguments={"broker": "ibkr"}, message_id=53,
    )
    accounts = payload["result"]["accounts"]
    assert len(accounts) == 1
    assert accounts[0]["id"] == acct2_id
    assert accounts[0]["broker"] == "ibkr"
    assert accounts[0]["account_number_masked"] == "****3456"


@pytest.mark.integration
async def test_search_trades_advanced_filters_and_isolation(client: AsyncClient) -> None:
    headers1, token1 = await _auth_and_pat(client)
    portfolio1, account1 = await _create_portfolio_and_account(client, headers1, "s1")
    trade_day_1 = await _create_trade(
        client,
        headers1,
        portfolio1,
        account1,
        symbol="AAPL",
        opened_at=datetime(2026, 5, 5, 10, 0, tzinfo=UTC),
        pnl="10",
    )
    _trade_day_2 = await _create_trade(
        client,
        headers1,
        portfolio1,
        account1,
        symbol="MSFT",
        opened_at=datetime(2026, 5, 8, 10, 0, tzinfo=UTC),
        pnl="20",
    )

    headers2, _token2 = await _auth_and_pat(client)
    portfolio2, account2 = await _create_portfolio_and_account(client, headers2, "s2")
    _other_user_trade = await _create_trade(
        client,
        headers2,
        portfolio2,
        account2,
        symbol="AAPL",
        opened_at=datetime(2026, 5, 6, 10, 0, tzinfo=UTC),
        pnl="30",
    )

    by_date = await _mcp_tools_call(
        client,
        token1,
        tool_name="search_trades_advanced",
        arguments={
            "date_from": "2026-05-05T00:00:00Z",
            "date_to": "2026-05-06T23:59:59Z",
        },
        message_id=21,
    )
    date_ids = {trade["id"] for trade in by_date["result"]["trades"]}
    assert trade_day_1 in date_ids
    assert by_date["result"]["total"] == 1

    by_symbol = await _mcp_tools_call(
        client,
        token1,
        tool_name="search_trades_advanced",
        arguments={"symbol": "aapl"},
        message_id=22,
    )
    symbol_ids = {trade["id"] for trade in by_symbol["result"]["trades"]}
    assert trade_day_1 in symbol_ids
    assert len(symbol_ids) == 1

    annotation_requires_primary = await _mcp_tools_call(
        client,
        token1,
        tool_name="search_trades_advanced",
        arguments={
            "annotation_filters": [
                {
                    "annotation_definition_id": str(uuid.uuid4()),
                    "operator": "eq",
                    "value": 1,
                }
            ]
        },
        message_id=23,
    )
    assert annotation_requires_primary["error"]["code"] == -32602

    default_pagination = await _mcp_tools_call(
        client,
        token1,
        tool_name="search_trades_advanced",
        arguments={},
        message_id=24,
    )
    assert default_pagination["result"]["limit"] == 50
    assert default_pagination["result"]["offset"] == 0

    isolation_ids = {trade["id"] for trade in default_pagination["result"]["trades"]}
    assert trade_day_1 in isolation_ids
    assert len(isolation_ids) == 2


@pytest.mark.integration
async def test_sync_trade_metadata_updates_and_enforces_constraints(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers1, token1 = await _auth_and_pat(client)
    portfolio1, account1 = await _create_portfolio_and_account(client, headers1, "m1")
    trade_1 = await _create_trade(
        client,
        headers1,
        portfolio1,
        account1,
        symbol="NVDA",
        opened_at=datetime(2026, 5, 6, 14, 0, tzinfo=UTC),
    )
    trade_2 = await _create_trade(
        client,
        headers1,
        portfolio1,
        account1,
        symbol="AMD",
        opened_at=datetime(2026, 5, 6, 15, 0, tzinfo=UTC),
    )

    headers2, _token2 = await _auth_and_pat(client)
    portfolio2, account2 = await _create_portfolio_and_account(client, headers2, "m2")
    other_trade = await _create_trade(
        client,
        headers2,
        portfolio2,
        account2,
        symbol="TSLA",
        opened_at=datetime(2026, 5, 6, 16, 0, tzinfo=UTC),
    )

    taxonomy_old = await client.post(
        "/api/v1/taxonomies",
        json={"name": "Old Tag", "scope": "trades", "color_hex": "#101010"},
        headers=headers1,
    )
    assert taxonomy_old.status_code == 201, taxonomy_old.text
    taxonomy_old_id = taxonomy_old.json()["data"]["id"]

    taxonomy_new = await client.post(
        "/api/v1/taxonomies",
        json={"name": "Macro Volatility", "scope": "trades", "color_hex": "#202020"},
        headers=headers1,
    )
    assert taxonomy_new.status_code == 201, taxonomy_new.text
    taxonomy_new_id = taxonomy_new.json()["data"]["id"]

    assign_taxonomy = await client.post(
        f"/api/v1/trades/{trade_1}/taxonomies",
        json={"taxonomy_id": taxonomy_old_id},
        headers=headers1,
    )
    assert assign_taxonomy.status_code == 201, assign_taxonomy.text

    annotation_def = await client.post(
        "/api/v1/annotation-definitions",
        json={"name": "Confidence", "type": "int", "scope": "trades", "scale_labels": {"min": 1, "max": 10}},
        headers=headers1,
    )
    assert annotation_def.status_code == 201, annotation_def.text
    annotation_def_id = annotation_def.json()["data"]["id"]

    first_sync = await _mcp_tools_call(
        client,
        token1,
        tool_name="sync_trade_metadata",
        arguments={
            "trade_ids": [trade_1, trade_2, other_trade],
            "notes": "bulk note",
            "taxonomy_ids": [taxonomy_new_id],
            "annotations": [
                {
                    "annotation_definition_id": annotation_def_id,
                    "value": 7,
                }
            ],
        },
        message_id=31,
    )
    assert first_sync["result"]["updated_count"] == 2

    second_sync = await _mcp_tools_call(
        client,
        token1,
        tool_name="sync_trade_metadata",
        arguments={
            "trade_ids": [trade_1],
            "annotations": [
                {
                    "annotation_definition_id": annotation_def_id,
                    "value": 9,
                }
            ],
        },
        message_id=32,
    )
    assert second_sync["result"]["updated_count"] == 1

    trade_one_row = await db_session.execute(select(Trade).where(Trade.id == uuid.UUID(trade_1)))
    trade_one = trade_one_row.scalar_one()
    assert trade_one.notes == "bulk note"

    trade_two_row = await db_session.execute(select(Trade).where(Trade.id == uuid.UUID(trade_2)))
    trade_two = trade_two_row.scalar_one()
    assert trade_two.notes == "bulk note"

    other_trade_row = await db_session.execute(select(Trade).where(Trade.id == uuid.UUID(other_trade)))
    other_trade_model = other_trade_row.scalar_one()
    assert other_trade_model.notes is None

    taxonomy_rows = await db_session.execute(
        select(TradeTaxonomy).where(TradeTaxonomy.trade_id == uuid.UUID(trade_1)),
    )
    taxonomy_assignments = list(taxonomy_rows.scalars().all())
    assigned_ids = {str(ta.taxonomy_id) for ta in taxonomy_assignments}
    assert taxonomy_new_id in assigned_ids
    assert taxonomy_old_id in assigned_ids  # merge semantics: existing tag preserved

    annotation_rows = await db_session.execute(
        select(TradeAnnotation).where(
            TradeAnnotation.trade_id == uuid.UUID(trade_1),
            TradeAnnotation.annotation_definition_id == uuid.UUID(annotation_def_id),
        )
    )
    annotation_assignment = annotation_rows.scalar_one()
    assert annotation_assignment.value_int == 9

    max_50_error = await _mcp_tools_call(
        client,
        token1,
        tool_name="sync_trade_metadata",
        arguments={"trade_ids": [str(uuid.uuid4()) for _ in range(51)]},
        message_id=33,
    )
    assert max_50_error["error"]["code"] == -32602


@pytest.mark.integration
async def test_create_strategy_playbook_creates_and_rejects_duplicate(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    _headers, token = await _auth_and_pat(client)

    created = await _mcp_tools_call(
        client,
        token,
        tool_name="create_strategy_playbook",
        arguments={
            "name": "Breakout Momentum",
            "description": "Momentum setup",
            "rules": ["Wait for opening range breakout", "Risk 1R", "Move stop at +1R"],
            "target_winrate": 0.6,
        },
        message_id=41,
    )

    playbook_id = created["result"]["playbook_id"]
    row = await db_session.execute(select(Playbook).where(Playbook.id == uuid.UUID(str(playbook_id))))
    playbook = row.scalar_one()
    assert playbook.name == "Breakout Momentum"
    assert playbook.is_active is True
    assert playbook.content_markdown == "- Wait for opening range breakout\n- Risk 1R\n- Move stop at +1R"
    assert playbook.target_winrate == Decimal("0.6")

    duplicate = await _mcp_tools_call(
        client,
        token,
        tool_name="create_strategy_playbook",
        arguments={
            "name": "Breakout Momentum",
            "rules": ["Rule 1"],
        },
        message_id=42,
    )
    assert duplicate["error"]["code"] == -32602


@pytest.mark.integration
async def test_tools_call_unknown_tool_returns_32601(client: AsyncClient) -> None:
    _headers, token = await _auth_and_pat(client)
    payload = await _mcp_tools_call(
        client,
        token,
        tool_name="does_not_exist",
        arguments={},
        message_id=51,
    )
    assert payload["error"]["code"] == -32601
