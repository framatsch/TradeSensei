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

import json
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
from app.models.playbook_taxonomy import PlaybookTaxonomy
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
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": message_id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    payload: dict[str, object] = response.json()
    # Unwrap MCP content array so tests can access result fields directly.
    result = payload.get("result")
    if isinstance(result, dict) and "content" in result:
        content = result["content"]
        if isinstance(content, list) and content:
            text = content[0].get("text", "")
            payload["result"] = json.loads(text)
    return payload


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
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
    )
    assert response.status_code == 401


@pytest.mark.integration
async def test_mcp_tools_list_returns_all_domain_tools(client: AsyncClient) -> None:
    _headers, token = await _auth_and_pat(client)
    response = await client.post(
        "/mcp",
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
        "list_checkins",
        "sync_checkin_metadata",
        "search_trades_advanced",
        "sync_trade_metadata",
        "sync_playbook_metadata",
        "create_strategy_playbook",
        "list_strategy_playbooks",
        "get_strategy_playbook",
        "update_strategy_playbook",
        "create_taxonomy",
        "update_taxonomy",
        "delete_taxonomy",
        "create_annotation_definition",
        "update_annotation_definition",
        "delete_annotation_definition",
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
            "description": "Wait for opening range breakout\n\nRisk 1R\n\nMove stop at +1R",
            "target_winrate": 0.6,
        },
        message_id=41,
    )

    playbook_id = created["result"]["playbook_id"]
    row = await db_session.execute(select(Playbook).where(Playbook.id == uuid.UUID(str(playbook_id))))
    playbook = row.scalar_one()
    assert playbook.name == "Breakout Momentum"
    assert playbook.is_active is True
    assert playbook.description == "Wait for opening range breakout\n\nRisk 1R\n\nMove stop at +1R"
    assert playbook.target_winrate == Decimal("0.6")

    duplicate = await _mcp_tools_call(
        client,
        token,
        tool_name="create_strategy_playbook",
        arguments={
            "name": "Breakout Momentum",
            "description": "Rule 1",
        },
        message_id=42,
    )
    assert duplicate["error"]["code"] == -32602


@pytest.mark.integration
async def test_sync_playbook_metadata_and_playbook_reads_include_taxonomies(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers, token = await _auth_and_pat(client)

    create_playbook = await _mcp_tools_call(
        client,
        token,
        tool_name="create_strategy_playbook",
        arguments={"name": "VWAP Reclaim", "description": "Initial markdown"},
        message_id=60,
    )
    playbook_id = create_playbook["result"]["playbook_id"]

    valid_scope_taxonomy = await client.post(
        "/api/v1/taxonomies",
        json={"name": "PB Scope", "scope": "playbook", "color_hex": "#112233"},
        headers=headers,
    )
    assert valid_scope_taxonomy.status_code == 201, valid_scope_taxonomy.text
    taxonomy_valid_id = valid_scope_taxonomy.json()["data"]["id"]

    second_valid_taxonomy = await client.post(
        "/api/v1/taxonomies",
        json={"name": "PB Scope 2", "scope": "checkins,playbook", "color_hex": "#223344"},
        headers=headers,
    )
    assert second_valid_taxonomy.status_code == 201, second_valid_taxonomy.text
    taxonomy_second_id = second_valid_taxonomy.json()["data"]["id"]

    invalid_scope_taxonomy = await client.post(
        "/api/v1/taxonomies",
        json={"name": "Trade-only", "scope": "trades", "color_hex": "#334455"},
        headers=headers,
    )
    assert invalid_scope_taxonomy.status_code == 201, invalid_scope_taxonomy.text
    taxonomy_invalid_scope_id = invalid_scope_taxonomy.json()["data"]["id"]

    first_sync = await _mcp_tools_call(
        client,
        token,
        tool_name="sync_playbook_metadata",
        arguments={
            "playbook_id": playbook_id,
            "taxonomy_ids": [taxonomy_valid_id],
        },
        message_id=61,
    )
    assert first_sync["result"]["updated_count"] == 1

    idempotent_sync = await _mcp_tools_call(
        client,
        token,
        tool_name="sync_playbook_metadata",
        arguments={
            "playbook_id": playbook_id,
            "taxonomy_ids": [taxonomy_valid_id],
        },
        message_id=62,
    )
    assert idempotent_sync["result"]["updated_count"] == 1

    additive_sync = await _mcp_tools_call(
        client,
        token,
        tool_name="sync_playbook_metadata",
        arguments={
            "playbook_id": playbook_id,
            "taxonomy_ids": [taxonomy_second_id],
        },
        message_id=63,
    )
    assert additive_sync["result"]["updated_count"] == 1

    assignment_rows = await db_session.execute(
        select(PlaybookTaxonomy).where(PlaybookTaxonomy.playbook_id == uuid.UUID(str(playbook_id))),
    )
    assigned_taxonomy_ids = {str(row.taxonomy_id) for row in assignment_rows.scalars().all()}
    assert taxonomy_valid_id in assigned_taxonomy_ids
    assert taxonomy_second_id in assigned_taxonomy_ids

    get_playbook = await _mcp_tools_call(
        client,
        token,
        tool_name="get_strategy_playbook",
        arguments={"playbook_id": playbook_id},
        message_id=64,
    )
    assert "content_markdown" not in get_playbook["result"]
    assert get_playbook["result"]["description"] == "Initial markdown"
    get_assignment_ids = {entry["taxonomy_id"] for entry in get_playbook["result"]["taxonomy_assignments"]}
    assert taxonomy_valid_id in get_assignment_ids
    assert taxonomy_second_id in get_assignment_ids

    list_playbooks = await _mcp_tools_call(
        client,
        token,
        tool_name="list_strategy_playbooks",
        arguments={},
        message_id=65,
    )
    listed_playbook = next((item for item in list_playbooks["result"]["playbooks"] if item["id"] == playbook_id), None)
    assert listed_playbook is not None
    listed_assignment_ids = {entry["taxonomy_id"] for entry in listed_playbook["taxonomy_assignments"]}
    assert taxonomy_valid_id in listed_assignment_ids
    assert taxonomy_second_id in listed_assignment_ids

    update_with_taxonomies = await _mcp_tools_call(
        client,
        token,
        tool_name="update_strategy_playbook",
        arguments={
            "playbook_id": playbook_id,
            "description": "Updated markdown",
            "taxonomy_ids": [taxonomy_valid_id],
        },
        message_id=66,
    )
    assert update_with_taxonomies["result"]["playbook_id"] == playbook_id

    row = await db_session.execute(select(Playbook).where(Playbook.id == uuid.UUID(str(playbook_id))))
    updated_playbook = row.scalar_one()
    assert updated_playbook.description == "Updated markdown"

    invalid_scope_sync = await _mcp_tools_call(
        client,
        token,
        tool_name="sync_playbook_metadata",
        arguments={
            "playbook_id": playbook_id,
            "taxonomy_ids": [taxonomy_invalid_scope_id],
        },
        message_id=67,
    )
    assert invalid_scope_sync["error"]["code"] == -32602

    archived_taxonomy = await client.post(
        "/api/v1/taxonomies",
        json={"name": "Archived PB", "scope": "playbook", "color_hex": "#445566"},
        headers=headers,
    )
    assert archived_taxonomy.status_code == 201, archived_taxonomy.text
    archived_id = archived_taxonomy.json()["data"]["id"]

    assign_taxonomy = await client.post(
        f"/api/v1/playbooks/{playbook_id}/taxonomies",
        json={"taxonomy_id": archived_id},
        headers=headers,
    )
    assert assign_taxonomy.status_code in (200, 201, 204), assign_taxonomy.text

    archive_update = await client.delete(
        f"/api/v1/taxonomies/{archived_id}",
        headers=headers,
    )
    assert archive_update.status_code in (200, 204), archive_update.text

    archived_sync = await _mcp_tools_call(
        client,
        token,
        tool_name="sync_playbook_metadata",
        arguments={
            "playbook_id": playbook_id,
            "taxonomy_ids": [archived_id],
        },
        message_id=68,
    )
    assert archived_sync["error"]["code"] == -32602

    invalid_id_sync = await _mcp_tools_call(
        client,
        token,
        tool_name="sync_playbook_metadata",
        arguments={
            "playbook_id": playbook_id,
            "taxonomy_ids": [str(uuid.uuid4())],
        },
        message_id=69,
    )
    assert invalid_id_sync["error"]["code"] == -32602

    not_found_sync = await _mcp_tools_call(
        client,
        token,
        tool_name="sync_playbook_metadata",
        arguments={
            "playbook_id": str(uuid.uuid4()),
            "taxonomy_ids": [taxonomy_valid_id],
        },
        message_id=70,
    )
    assert not_found_sync["error"]["code"] == -32602


@pytest.mark.integration
async def test_update_strategy_playbook_optional_fields_and_duplicate_name_paths(
    client: AsyncClient,
) -> None:
    _headers, token = await _auth_and_pat(client)

    first = await _mcp_tools_call(
        client,
        token,
        tool_name="create_strategy_playbook",
        arguments={"name": "PB One", "description": "first"},
        message_id=71,
    )
    first_id = first["result"]["playbook_id"]

    second = await _mcp_tools_call(
        client,
        token,
        tool_name="create_strategy_playbook",
        arguments={"name": "PB Two", "description": "second"},
        message_id=72,
    )
    second_id = second["result"]["playbook_id"]

    update_ok = await _mcp_tools_call(
        client,
        token,
        tool_name="update_strategy_playbook",
        arguments={
            "playbook_id": first_id,
            "target_winrate": 0.55,
            "is_active": False,
        },
        message_id=73,
    )
    assert update_ok["result"]["playbook_id"] == first_id

    duplicate_name = await _mcp_tools_call(
        client,
        token,
        tool_name="update_strategy_playbook",
        arguments={
            "playbook_id": second_id,
            "name": "PB One",
        },
        message_id=74,
    )
    assert duplicate_name["error"]["code"] == -32602

    missing_playbook = await _mcp_tools_call(
        client,
        token,
        tool_name="update_strategy_playbook",
        arguments={
            "playbook_id": str(uuid.uuid4()),
            "name": "Nope",
        },
        message_id=75,
    )
    assert missing_playbook["error"]["code"] == -32602


@pytest.mark.integration
async def test_sync_playbook_metadata_empty_list_is_noop(
    client: AsyncClient,
) -> None:
    _headers, token = await _auth_and_pat(client)

    created = await _mcp_tools_call(
        client,
        token,
        tool_name="create_strategy_playbook",
        arguments={"name": "PB Empty Sync"},
        message_id=76,
    )
    playbook_id = created["result"]["playbook_id"]

    sync_empty = await _mcp_tools_call(
        client,
        token,
        tool_name="sync_playbook_metadata",
        arguments={"playbook_id": playbook_id, "taxonomy_ids": []},
        message_id=77,
    )
    assert sync_empty["result"]["updated_count"] == 0


@pytest.mark.integration
async def test_update_strategy_playbook_without_taxonomy_ids_keeps_assignments(
    client: AsyncClient,
) -> None:
    headers, token = await _auth_and_pat(client)

    created = await _mcp_tools_call(
        client,
        token,
        tool_name="create_strategy_playbook",
        arguments={"name": "PB Preserve Tags", "description": "before"},
        message_id=78,
    )
    playbook_id = created["result"]["playbook_id"]

    taxonomy = await client.post(
        "/api/v1/taxonomies",
        json={"name": "Keep Me", "scope": "playbook", "color_hex": "#665544"},
        headers=headers,
    )
    assert taxonomy.status_code == 201, taxonomy.text
    taxonomy_id = taxonomy.json()["data"]["id"]

    synced = await _mcp_tools_call(
        client,
        token,
        tool_name="sync_playbook_metadata",
        arguments={"playbook_id": playbook_id, "taxonomy_ids": [taxonomy_id]},
        message_id=79,
    )
    assert synced["result"]["updated_count"] == 1

    updated = await _mcp_tools_call(
        client,
        token,
        tool_name="update_strategy_playbook",
        arguments={"playbook_id": playbook_id, "description": "after"},
        message_id=80,
    )
    assert updated["result"]["playbook_id"] == playbook_id

    fetched = await _mcp_tools_call(
        client,
        token,
        tool_name="get_strategy_playbook",
        arguments={"playbook_id": playbook_id},
        message_id=81,
    )
    assignment_ids = {entry["taxonomy_id"] for entry in fetched["result"]["taxonomy_assignments"]}
    assert taxonomy_id in assignment_ids


@pytest.mark.integration
async def test_sync_playbook_metadata_rejects_foreign_taxonomy_atomically(
    client: AsyncClient,
) -> None:
    headers_1, token_1 = await _auth_and_pat(client)
    headers_2, _token_2 = await _auth_and_pat(client)

    created = await _mcp_tools_call(
        client,
        token_1,
        tool_name="create_strategy_playbook",
        arguments={"name": "PB Atomic Reject"},
        message_id=82,
    )
    playbook_id = created["result"]["playbook_id"]

    own_taxonomy = await client.post(
        "/api/v1/taxonomies",
        json={"name": "Own", "scope": "playbook", "color_hex": "#110022"},
        headers=headers_1,
    )
    assert own_taxonomy.status_code == 201, own_taxonomy.text
    own_taxonomy_id = own_taxonomy.json()["data"]["id"]

    foreign_taxonomy = await client.post(
        "/api/v1/taxonomies",
        json={"name": "Foreign", "scope": "playbook", "color_hex": "#220033"},
        headers=headers_2,
    )
    assert foreign_taxonomy.status_code == 201, foreign_taxonomy.text
    foreign_taxonomy_id = foreign_taxonomy.json()["data"]["id"]

    mixed_sync = await _mcp_tools_call(
        client,
        token_1,
        tool_name="sync_playbook_metadata",
        arguments={
            "playbook_id": playbook_id,
            "taxonomy_ids": [own_taxonomy_id, foreign_taxonomy_id],
        },
        message_id=83,
    )
    assert mixed_sync["error"]["code"] == -32602

    fetched = await _mcp_tools_call(
        client,
        token_1,
        tool_name="get_strategy_playbook",
        arguments={"playbook_id": playbook_id},
        message_id=84,
    )
    assert fetched["result"]["taxonomy_assignments"] == []


@pytest.mark.integration
async def test_mcp_streamable_tools_call_validates_params_shape(client: AsyncClient) -> None:
    _headers, token = await _auth_and_pat(client)
    response = await client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 90, "method": "tools/call", "params": "bad"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["error"]["code"] == -32602
    assert payload["error"]["message"] == "params must be an object"


@pytest.mark.integration
async def test_mcp_streamable_tools_call_requires_name_and_arguments_object(client: AsyncClient) -> None:
    _headers, token = await _auth_and_pat(client)

    missing_name = await client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 91, "method": "tools/call", "params": {}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert missing_name.status_code == 200, missing_name.text
    missing_name_payload = missing_name.json()
    assert missing_name_payload["error"]["code"] == -32602
    assert missing_name_payload["error"]["message"] == "Tool name is required"

    bad_arguments = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 92,
            "method": "tools/call",
            "params": {"name": "list_portfolios", "arguments": "bad"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert bad_arguments.status_code == 200, bad_arguments.text
    bad_arguments_payload = bad_arguments.json()
    assert bad_arguments_payload["error"]["code"] == -32602
    assert bad_arguments_payload["error"]["message"] == "arguments must be an object"


@pytest.mark.integration
async def test_mcp_streamable_unknown_method_and_notification_flow(client: AsyncClient) -> None:
    _headers, token = await _auth_and_pat(client)

    unknown = await client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 93, "method": "not_a_method"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert unknown.status_code == 200, unknown.text
    unknown_payload = unknown.json()
    assert unknown_payload["error"]["code"] == -32601
    assert "Unknown method" in unknown_payload["error"]["message"]

    notification = await client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert notification.status_code == 202, notification.text


@pytest.mark.integration
async def test_mcp_streamable_parse_error_and_sse_response(client: AsyncClient) -> None:
    _headers, token = await _auth_and_pat(client)

    parse_error = await client.post(
        "/mcp",
        content="{not-json",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    assert parse_error.status_code == 400, parse_error.text
    parse_payload = parse_error.json()
    assert parse_payload["error"]["code"] == -32700

    sse_response = await client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 94, "method": "ping"},
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "text/event-stream",
        },
    )
    assert sse_response.status_code == 200, sse_response.text
    assert sse_response.headers["content-type"].startswith("text/event-stream")
    assert "event: message" in sse_response.text


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
