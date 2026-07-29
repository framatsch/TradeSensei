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

import json
import uuid

import pytest
from httpx import AsyncClient


async def _register_and_get_pat(client: AsyncClient) -> tuple[str, dict[str, str]]:
    suffix = str(uuid.uuid4())[:8]
    username = f"mcp_user_{suffix}"
    email = f"mcp_{suffix}@example.com"
    password = "S3cureP@ss99"

    await client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    login = await client.post(
        "/api/v1/auth/token",
        data={"username": username, "password": password},
    )
    bearer_token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {bearer_token}"}
    
    pat_resp = await client.post(
        "/api/v1/settings/tokens",
        json={"name": "MCP Test"},
        headers=headers,
    )
    return pat_resp.json()["data"]["token"], headers

@pytest.mark.integration
async def test_mcp_checkin_metadata_workflow_full(client: AsyncClient):
    pat, headers = await _register_and_get_pat(client)
    mcp_headers = {"Authorization": f"Bearer {pat}"}

    # 1. Setup Data via regular API
    t1 = await client.post("/api/v1/taxonomies", headers=headers, json={"name": "MCP Tag", "scope": "checkins", "color_hex": "#0000FF"})
    t1_id = t1.json()["data"]["id"]
    
    ann = await client.post("/api/v1/annotation-definitions", headers=headers, json={"name": "MCP Score", "type": "int", "scope": "checkins"})
    ann_id = ann.json()["data"]["id"]
    
    c1 = await client.post("/api/v1/checkins", headers=headers, json={"date": "2024-06-01", "note": "MCP Test"})
    c1_id = c1.json()["data"]["id"]

    # 2. Sync Metadata via MCP
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "sync_checkin_metadata",
            "arguments": {
                "checkin_ids": [c1_id],
                "taxonomy_ids": [t1_id],
                "annotations": [{"annotation_definition_id": ann_id, "value": 77}]
            }
        }
    }
    resp = await client.post("/mcp", json=payload, headers=mcp_headers)
    assert resp.status_code == 200, resp.text
    result = resp.json()["result"]
    content = json.loads(result["content"][0]["text"])
    assert content["updated_count"] == 1

    # 3. List Checkins via MCP with filter
    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "list_checkins",
            "arguments": {
                "annotation_filters": [{"annotation_definition_id": ann_id, "operator": "eq", "value": 77}]
            }
        }
    }
    resp = await client.post("/mcp", json=payload, headers=mcp_headers)
    assert resp.status_code == 200
    result = resp.json()["result"]
    content = json.loads(result["content"][0]["text"])
    assert len(content["checkins"]) == 1
    assert content["checkins"][0]["id"] == c1_id
    assert content["checkins"][0]["annotation_assignments"][0]["value"] == 77
    assert content["checkins"][0]["taxonomy_assignments"][0]["taxonomy_id"] == t1_id

@pytest.mark.integration
async def test_mcp_search_trades_advanced(client: AsyncClient):
    pat, headers = await _register_and_get_pat(client)
    mcp_headers = {"Authorization": f"Bearer {pat}"}

    # Setup Trade
    port = await client.post("/api/v1/portfolios", headers=headers, json={"name": "MCP Port", "base_currency": "USD"})
    port_id = port.json()["data"]["id"]
    acc = await client.post(f"/api/v1/portfolios/{port_id}/accounts", headers=headers, json={"name": "MCP Acc", "broker": "MANUAL", "currency": "USD"})
    acc_id = acc.json()["data"]["id"]
    
    ann = await client.post("/api/v1/annotation-definitions", headers=headers, json={"name": "MCP Grade", "type": "int", "scope": "trades"})
    ann_id = ann.json()["data"]["id"]
    
    t1 = await client.post(f"/api/v1/portfolios/{port_id}/trades", headers=headers, json={
        "account_id": acc_id, "symbol": "MCP", "direction": "LONG", "asset_class": "EQUITY", "quantity": 1, "entry_price": 100.0, "opened_at": "2024-06-01T12:00:00Z"
    })
    t1_id = t1.json()["data"]["id"]
    
    # Sync via MCP
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "sync_trade_metadata",
            "arguments": {
                "trade_ids": [t1_id],
                "annotations": [{"annotation_definition_id": ann_id, "value": 5}]
            }
        }
    }
    await client.post("/mcp", json=payload, headers=mcp_headers)
    
    # Search via MCP
    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "search_trades_advanced",
            "arguments": {
                "symbol": "MCP",
                "annotation_filters": [{"annotation_definition_id": ann_id, "operator": "eq", "value": 5}]
            }
        }
    }
    resp = await client.post("/mcp", json=payload, headers=mcp_headers)
    assert resp.status_code == 200
    result = resp.json()["result"]
    content = json.loads(result["content"][0]["text"])
    assert len(content["trades"]) == 1
    assert content["trades"][0]["id"] == t1_id
