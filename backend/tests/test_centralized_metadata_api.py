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

"""Integration tests for centralized taxonomy/annotation metadata endpoints."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.checkin_annotation import CheckinAnnotation
from app.models.checkin_taxonomy import CheckinTaxonomy
from app.models.trade_annotation import TradeAnnotation
from app.models.trade_taxonomy import TradeTaxonomy


async def _auth_headers(client: AsyncClient, suffix: str) -> dict[str, str]:
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "username": f"meta_{suffix}",
            "email": f"meta_{suffix}@example.com",
            "password": "MetaTest@99",
        },
    )
    assert register.status_code == 201, register.text

    token = await client.post(
        "/api/v1/auth/token",
        data={"username": f"meta_{suffix}", "password": "MetaTest@99"},
    )
    assert token.status_code == 200, token.text
    return {"Authorization": f"Bearer {token.json()['access_token']}"}


async def _create_portfolio_and_account(
    client: AsyncClient,
    headers: dict[str, str],
    suffix: str,
) -> tuple[str, str]:
    portfolio = await client.post(
        "/api/v1/portfolios",
        json={"name": f"Meta Portfolio {suffix}", "base_currency": "USD"},
        headers=headers,
    )
    assert portfolio.status_code == 201, portfolio.text
    portfolio_id = portfolio.json()["data"]["id"]

    account = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        json={"name": f"Meta Account {suffix}", "type": "manual", "currency": "USD"},
        headers=headers,
    )
    assert account.status_code == 201, account.text
    return portfolio_id, account.json()["data"]["id"]


async def _create_trade(
    client: AsyncClient,
    headers: dict[str, str],
    portfolio_id: str,
    account_id: str,
) -> str:
    create = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        json={
            "account_id": account_id,
            "symbol": "AAPL",
            "direction": "LONG",
            "asset_class": "EQUITY",
            "quantity": "10",
            "entry_price": "150",
            "opened_at": datetime(2026, 1, 5, 10, 0, tzinfo=UTC).isoformat(),
        },
        headers=headers,
    )
    assert create.status_code == 201, create.text
    return create.json()["data"]["id"]


@pytest.mark.integration
async def test_taxonomy_endpoints_archive_and_visibility(client: AsyncClient) -> None:
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_portfolio_and_account(
        client, headers, uuid.uuid4().hex[:6]
    )
    trade_id = await _create_trade(client, headers, portfolio_id, account_id)

    create = await client.post(
        "/api/v1/taxonomies",
        json={"name": "Setup", "scope": "trades", "color_hex": "#A1B2C3"},
        headers=headers,
    )
    assert create.status_code == 201, create.text
    taxonomy_id = create.json()["data"]["id"]

    assign = await client.post(
        f"/api/v1/trades/{trade_id}/taxonomies",
        json={"taxonomy_id": taxonomy_id},
        headers=headers,
    )
    assert assign.status_code == 201, assign.text

    soft_delete = await client.delete(f"/api/v1/taxonomies/{taxonomy_id}", headers=headers)
    assert soft_delete.status_code == 200, soft_delete.text
    assert soft_delete.json()["data"]["is_archived"] is True

    list_resp = await client.get("/api/v1/taxonomies", headers=headers)
    assert list_resp.status_code == 200, list_resp.text
    listed_ids = {item["id"] for item in list_resp.json()["data"]}
    assert taxonomy_id not in listed_ids

    get_resp = await client.get(f"/api/v1/taxonomies/{taxonomy_id}", headers=headers)
    assert get_resp.status_code == 200, get_resp.text
    assert get_resp.json()["data"]["is_archived"] is True


@pytest.mark.integration
async def test_annotation_definition_endpoints_validation_and_visibility(
    client: AsyncClient,
) -> None:
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_portfolio_and_account(
        client, headers, uuid.uuid4().hex[:6]
    )
    trade_id = await _create_trade(client, headers, portfolio_id, account_id)

    create = await client.post(
        "/api/v1/annotation-definitions",
        json={
            "name": "Confidence",
            "type": "int",
            "scope": "trades",
            "scale_labels": {"min": 1, "max": 10},
        },
        headers=headers,
    )
    assert create.status_code == 201, create.text
    definition_id = create.json()["data"]["id"]

    type_change = await client.put(
        f"/api/v1/annotation-definitions/{definition_id}",
        json={"type": "float"},
        headers=headers,
    )
    assert type_change.status_code == 422, type_change.text

    assign = await client.post(
        f"/api/v1/trades/{trade_id}/annotations/{definition_id}",
        json={"value": 7},
        headers=headers,
    )
    assert assign.status_code == 201, assign.text

    soft_delete = await client.delete(
        f"/api/v1/annotation-definitions/{definition_id}",
        headers=headers,
    )
    assert soft_delete.status_code == 200, soft_delete.text
    assert soft_delete.json()["data"]["is_archived"] is True

    list_resp = await client.get("/api/v1/annotation-definitions", headers=headers)
    assert list_resp.status_code == 200, list_resp.text
    listed_ids = {item["id"] for item in list_resp.json()["data"]}
    assert definition_id not in listed_ids

    get_resp = await client.get(
        f"/api/v1/annotation-definitions/{definition_id}", headers=headers
    )
    assert get_resp.status_code == 200, get_resp.text
    assert get_resp.json()["data"]["is_archived"] is True


@pytest.mark.integration
async def test_trade_metadata_assignment_validation_and_detail_response(
    client: AsyncClient,
) -> None:
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_portfolio_and_account(
        client, headers, uuid.uuid4().hex[:6]
    )
    trade_id = await _create_trade(client, headers, portfolio_id, account_id)

    taxonomy = await client.post(
        "/api/v1/taxonomies",
        json={"name": "Volatility", "scope": "checkins", "color_hex": "#334455"},
        headers=headers,
    )
    taxonomy_id = taxonomy.json()["data"]["id"]
    mismatch = await client.post(
        f"/api/v1/trades/{trade_id}/taxonomies",
        json={"taxonomy_id": taxonomy_id},
        headers=headers,
    )
    assert mismatch.status_code == 422, mismatch.text

    trades_taxonomy = await client.post(
        "/api/v1/taxonomies",
        json={"name": "Setup", "scope": "trades", "color_hex": "#223344"},
        headers=headers,
    )
    trades_taxonomy_id = trades_taxonomy.json()["data"]["id"]
    ok_assign = await client.post(
        f"/api/v1/trades/{trade_id}/taxonomies",
        json={"taxonomy_id": trades_taxonomy_id},
        headers=headers,
    )
    assert ok_assign.status_code == 201, ok_assign.text
    duplicate = await client.post(
        f"/api/v1/trades/{trade_id}/taxonomies",
        json={"taxonomy_id": trades_taxonomy_id},
        headers=headers,
    )
    assert duplicate.status_code == 409, duplicate.text

    archived_delete = await client.delete(
        f"/api/v1/taxonomies/{trades_taxonomy_id}", headers=headers
    )
    assert archived_delete.status_code == 200, archived_delete.text
    archived_assign = await client.post(
        f"/api/v1/trades/{trade_id}/taxonomies",
        json={"taxonomy_id": trades_taxonomy_id},
        headers=headers,
    )
    assert archived_assign.status_code == 422, archived_assign.text

    checkin_only_definition = await client.post(
        "/api/v1/annotation-definitions",
        json={"name": "Mood", "type": "int", "scope": "checkins"},
        headers=headers,
    )
    checkin_only_definition_id = checkin_only_definition.json()["data"]["id"]
    scope_mismatch = await client.post(
        f"/api/v1/trades/{trade_id}/annotations/{checkin_only_definition_id}",
        json={"value": 1},
        headers=headers,
    )
    assert scope_mismatch.status_code == 422, scope_mismatch.text

    int_definition = await client.post(
        "/api/v1/annotation-definitions",
        json={
            "name": "Confidence",
            "type": "int",
            "scope": "trades",
            "scale_labels": {"min": 1, "max": 10},
        },
        headers=headers,
    )
    int_definition_id = int_definition.json()["data"]["id"]

    wrong_type = await client.post(
        f"/api/v1/trades/{trade_id}/annotations/{int_definition_id}",
        json={"value": "bad"},
        headers=headers,
    )
    assert wrong_type.status_code == 422, wrong_type.text

    out_of_range = await client.post(
        f"/api/v1/trades/{trade_id}/annotations/{int_definition_id}",
        json={"value": 11},
        headers=headers,
    )
    assert out_of_range.status_code == 422, out_of_range.text

    ok_int = await client.post(
        f"/api/v1/trades/{trade_id}/annotations/{int_definition_id}",
        json={"value": 5},
        headers=headers,
    )
    assert ok_int.status_code == 201, ok_int.text

    enum_definition = await client.post(
        "/api/v1/annotation-definitions",
        json={
            "name": "Regime",
            "type": "string_enum",
            "scope": "trades",
            "scale_labels": {"options": ["Low", "Medium", "High"]},
        },
        headers=headers,
    )
    enum_definition_id = enum_definition.json()["data"]["id"]
    invalid_enum = await client.post(
        f"/api/v1/trades/{trade_id}/annotations/{enum_definition_id}",
        json={"value": "Critical"},
        headers=headers,
    )
    assert invalid_enum.status_code == 422, invalid_enum.text

    ok_enum = await client.post(
        f"/api/v1/trades/{trade_id}/annotations/{enum_definition_id}",
        json={"value": "Medium"},
        headers=headers,
    )
    assert ok_enum.status_code == 201, ok_enum.text

    archived_definition_delete = await client.delete(
        f"/api/v1/annotation-definitions/{int_definition_id}",
        headers=headers,
    )
    assert archived_definition_delete.status_code == 200, archived_definition_delete.text

    detail = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}", headers=headers
    )
    assert detail.status_code == 200, detail.text
    data = detail.json()["data"]
    assert len(data["taxonomies"]) >= 1
    assert any(item["id"] == trades_taxonomy_id for item in data["taxonomies"])
    assert any(item["annotation_definition_id"] == int_definition_id for item in data["annotations"])
    int_values = [
        item["value"]
        for item in data["annotations"]
        if item["annotation_definition_id"] == int_definition_id
    ]
    assert int_values and int_values[0] == 5


@pytest.mark.integration
async def test_checkin_metadata_assignment_and_cascade(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])

    checkin_create = await client.post(
        "/api/v1/checkins",
        json={"date": "2026-01-20"},
        headers=headers,
    )
    assert checkin_create.status_code == 201, checkin_create.text
    checkin_id = checkin_create.json()["data"]["id"]

    taxonomy = await client.post(
        "/api/v1/taxonomies",
        json={"name": "Emotion", "scope": "checkins", "color_hex": "#112233"},
        headers=headers,
    )
    taxonomy_id = taxonomy.json()["data"]["id"]

    duplicate_taxonomy = await client.post(
        f"/api/v1/checkins/{checkin_id}/taxonomies",
        json={"taxonomy_id": taxonomy_id},
        headers=headers,
    )
    assert duplicate_taxonomy.status_code == 201, duplicate_taxonomy.text

    duplicate_taxonomy_conflict = await client.post(
        f"/api/v1/checkins/{checkin_id}/taxonomies",
        json={"taxonomy_id": taxonomy_id},
        headers=headers,
    )
    assert duplicate_taxonomy_conflict.status_code == 409, duplicate_taxonomy_conflict.text

    trades_scope_taxonomy = await client.post(
        "/api/v1/taxonomies",
        json={"name": "ExecutionOnly", "scope": "trades", "color_hex": "#556677"},
        headers=headers,
    )
    trades_scope_taxonomy_id = trades_scope_taxonomy.json()["data"]["id"]
    taxonomy_scope_mismatch = await client.post(
        f"/api/v1/checkins/{checkin_id}/taxonomies",
        json={"taxonomy_id": trades_scope_taxonomy_id},
        headers=headers,
    )
    assert taxonomy_scope_mismatch.status_code == 422, taxonomy_scope_mismatch.text

    archived_taxonomy = await client.post(
        "/api/v1/taxonomies",
        json={"name": "ArchivedCheckinTaxonomy", "scope": "checkins", "color_hex": "#778899"},
        headers=headers,
    )
    archived_taxonomy_id = archived_taxonomy.json()["data"]["id"]
    archive_taxonomy_resp = await client.delete(
        f"/api/v1/taxonomies/{archived_taxonomy_id}",
        headers=headers,
    )
    assert archive_taxonomy_resp.status_code == 204, archive_taxonomy_resp.text
    archived_taxonomy_assign = await client.post(
        f"/api/v1/checkins/{checkin_id}/taxonomies",
        json={"taxonomy_id": archived_taxonomy_id},
        headers=headers,
    )
    assert archived_taxonomy_assign.status_code == 404, archived_taxonomy_assign.text

    taxonomy_assign = await client.post(
        f"/api/v1/checkins/{checkin_id}/taxonomies",
        json={"taxonomy_id": taxonomy_id},
        headers=headers,
    )
    assert taxonomy_assign.status_code == 409, taxonomy_assign.text

    definition = await client.post(
        "/api/v1/annotation-definitions",
        json={"name": "Stress", "type": "bool", "scope": "checkins"},
        headers=headers,
    )
    definition_id = definition.json()["data"]["id"]

    annotation_assign = await client.post(
        f"/api/v1/checkins/{checkin_id}/annotations/{definition_id}",
        json={"value": True},
        headers=headers,
    )
    assert annotation_assign.status_code == 201, annotation_assign.text

    duplicate_annotation = await client.post(
        f"/api/v1/checkins/{checkin_id}/annotations/{definition_id}",
        json={"value": True},
        headers=headers,
    )
    assert duplicate_annotation.status_code == 409, duplicate_annotation.text

    checkin_int_definition = await client.post(
        "/api/v1/annotation-definitions",
        json={
            "name": "CheckinIntensity",
            "type": "int",
            "scope": "checkins",
            "scale_labels": {"min": 1, "max": 10},
        },
        headers=headers,
    )
    checkin_int_definition_id = checkin_int_definition.json()["data"]["id"]

    checkin_int_wrong_type = await client.post(
        f"/api/v1/checkins/{checkin_id}/annotations/{checkin_int_definition_id}",
        json={"value": "bad"},
        headers=headers,
    )
    assert checkin_int_wrong_type.status_code == 422, checkin_int_wrong_type.text

    checkin_int_out_of_range = await client.post(
        f"/api/v1/checkins/{checkin_id}/annotations/{checkin_int_definition_id}",
        json={"value": 11},
        headers=headers,
    )
    assert checkin_int_out_of_range.status_code == 422, checkin_int_out_of_range.text

    checkin_int_ok = await client.post(
        f"/api/v1/checkins/{checkin_id}/annotations/{checkin_int_definition_id}",
        json={"value": 6},
        headers=headers,
    )
    assert checkin_int_ok.status_code == 201, checkin_int_ok.text

    checkin_float_definition = await client.post(
        "/api/v1/annotation-definitions",
        json={
            "name": "CheckinVariance",
            "type": "float",
            "scope": "checkins",
            "scale_labels": {"min": 0, "max": 1},
        },
        headers=headers,
    )
    checkin_float_definition_id = checkin_float_definition.json()["data"]["id"]
    checkin_float_ok = await client.post(
        f"/api/v1/checkins/{checkin_id}/annotations/{checkin_float_definition_id}",
        json={"value": 0.75},
        headers=headers,
    )
    assert checkin_float_ok.status_code == 201, checkin_float_ok.text

    checkin_enum_definition = await client.post(
        "/api/v1/annotation-definitions",
        json={
            "name": "CheckinRegime",
            "type": "string_enum",
            "scope": "checkins",
            "scale_labels": {"options": ["Low", "Medium", "High"]},
        },
        headers=headers,
    )
    checkin_enum_definition_id = checkin_enum_definition.json()["data"]["id"]
    checkin_enum_invalid = await client.post(
        f"/api/v1/checkins/{checkin_id}/annotations/{checkin_enum_definition_id}",
        json={"value": "Critical"},
        headers=headers,
    )
    assert checkin_enum_invalid.status_code == 422, checkin_enum_invalid.text
    checkin_enum_ok = await client.post(
        f"/api/v1/checkins/{checkin_id}/annotations/{checkin_enum_definition_id}",
        json={"value": "Medium"},
        headers=headers,
    )
    assert checkin_enum_ok.status_code == 201, checkin_enum_ok.text

    trades_scope_definition = await client.post(
        "/api/v1/annotation-definitions",
        json={"name": "TradeOnlyDefinition", "type": "bool", "scope": "trades"},
        headers=headers,
    )
    trades_scope_definition_id = trades_scope_definition.json()["data"]["id"]
    definition_scope_mismatch = await client.post(
        f"/api/v1/checkins/{checkin_id}/annotations/{trades_scope_definition_id}",
        json={"value": True},
        headers=headers,
    )
    assert definition_scope_mismatch.status_code == 422, definition_scope_mismatch.text

    archived_definition = await client.post(
        "/api/v1/annotation-definitions",
        json={"name": "ArchivedCheckinDefinition", "type": "bool", "scope": "checkins"},
        headers=headers,
    )
    archived_definition_id = archived_definition.json()["data"]["id"]
    archive_definition_resp = await client.delete(
        f"/api/v1/annotation-definitions/{archived_definition_id}",
        headers=headers,
    )
    assert archive_definition_resp.status_code == 204, archive_definition_resp.text
    archived_definition_assign = await client.post(
        f"/api/v1/checkins/{checkin_id}/annotations/{archived_definition_id}",
        json={"value": True},
        headers=headers,
    )
    assert archived_definition_assign.status_code == 422, archived_definition_assign.text

    archive_assigned_definition_resp = await client.delete(
        f"/api/v1/annotation-definitions/{checkin_int_definition_id}",
        headers=headers,
    )
    assert archive_assigned_definition_resp.status_code == 200, archive_assigned_definition_resp.text

    detail_before_delete = await client.get("/api/v1/checkins/2026-01-20", headers=headers)
    assert detail_before_delete.status_code == 200, detail_before_delete.text
    detail_data = detail_before_delete.json()["data"]
    assert len(detail_data["taxonomies"]) == 1
    assert len(detail_data["annotations"]) >= 4
    assert any(item["id"] == taxonomy_id for item in detail_data["taxonomies"])
    assert any(
        item["annotation_definition_id"] == checkin_int_definition_id and item["value"] == 6
        for item in detail_data["annotations"]
    )
    assert any(
        item["annotation_definition_id"] == checkin_float_definition_id
        and Decimal(str(item["value"])) == Decimal("0.75")
        for item in detail_data["annotations"]
    )
    assert any(
        item["annotation_definition_id"] == checkin_enum_definition_id and item["value"] == "Medium"
        for item in detail_data["annotations"]
    )

    delete = await client.delete("/api/v1/checkins/2026-01-20", headers=headers)
    assert delete.status_code == 204, delete.text

    taxonomy_count_stmt = select(func.count()).select_from(CheckinTaxonomy)
    taxonomy_count = await db_session.execute(taxonomy_count_stmt)
    assert int(taxonomy_count.scalar_one()) == 0

    annotation_count_stmt = select(func.count()).select_from(CheckinAnnotation)
    annotation_count = await db_session.execute(annotation_count_stmt)
    assert int(annotation_count.scalar_one()) == 0


@pytest.mark.integration
async def test_trade_delete_cascades_metadata(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])
    portfolio_id, account_id = await _create_portfolio_and_account(
        client, headers, uuid.uuid4().hex[:6]
    )
    trade_id = await _create_trade(client, headers, portfolio_id, account_id)

    taxonomy = await client.post(
        "/api/v1/taxonomies",
        json={"name": "Execution", "scope": "trades", "color_hex": "#445566"},
        headers=headers,
    )
    taxonomy_id = taxonomy.json()["data"]["id"]
    await client.post(
        f"/api/v1/trades/{trade_id}/taxonomies",
        json={"taxonomy_id": taxonomy_id},
        headers=headers,
    )

    definition = await client.post(
        "/api/v1/annotation-definitions",
        json={"name": "FollowedPlan", "type": "bool", "scope": "trades"},
        headers=headers,
    )
    definition_id = definition.json()["data"]["id"]
    await client.post(
        f"/api/v1/trades/{trade_id}/annotations/{definition_id}",
        json={"value": True},
        headers=headers,
    )

    delete_trade = await client.delete(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}", headers=headers
    )
    assert delete_trade.status_code == 204, delete_trade.text

    trade_taxonomy_count = await db_session.execute(
        select(func.count()).select_from(TradeTaxonomy)
    )
    assert int(trade_taxonomy_count.scalar_one()) == 0

    trade_annotation_count = await db_session.execute(
        select(func.count()).select_from(TradeAnnotation)
    )
    assert int(trade_annotation_count.scalar_one()) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_taxonomy_hard_delete_when_unused_returns_204(client: AsyncClient) -> None:
    """Taxonomy with no assignments is permanently removed (hard delete, 204)."""
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])

    create = await client.post(
        "/api/v1/taxonomies",
        json={"name": "UnusedTag", "scope": "trades", "color_hex": "#aabbcc"},
        headers=headers,
    )
    assert create.status_code == 201, create.text
    taxonomy_id = create.json()["data"]["id"]

    delete = await client.delete(f"/api/v1/taxonomies/{taxonomy_id}", headers=headers)
    assert delete.status_code == 204, delete.text

    get = await client.get(f"/api/v1/taxonomies/{taxonomy_id}", headers=headers)
    assert get.status_code == 404, get.text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_annotation_definition_hard_delete_when_unused_returns_204(
    client: AsyncClient,
) -> None:
    """Annotation definition with no assignments is permanently removed (hard delete, 204)."""
    headers = await _auth_headers(client, uuid.uuid4().hex[:8])

    create = await client.post(
        "/api/v1/annotation-definitions",
        json={"name": "UnusedMetric", "type": "int", "scope": "trades"},
        headers=headers,
    )
    assert create.status_code == 201, create.text
    definition_id = create.json()["data"]["id"]

    delete = await client.delete(
        f"/api/v1/annotation-definitions/{definition_id}", headers=headers
    )
    assert delete.status_code == 204, delete.text

    get = await client.get(
        f"/api/v1/annotation-definitions/{definition_id}", headers=headers
    )
    assert get.status_code == 404, get.text
