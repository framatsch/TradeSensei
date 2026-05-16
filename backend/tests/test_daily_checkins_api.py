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

"""Integration tests for daily check-in and legacy endpoint removal."""

import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient


async def _register_and_auth_headers(
    client: AsyncClient,
    *,
    username: str,
    email: str,
    password: str,
) -> dict[str, str]:
    register = await client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    assert register.status_code == 201, register.text

    token = await client.post(
        "/api/v1/auth/token",
        data={"username": username, "password": password},
    )
    assert token.status_code == 200, token.text
    access_token = token.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


@pytest.mark.integration
async def test_legacy_checkin_fields_endpoint_returns_404(
    client: AsyncClient,
) -> None:
    headers = await _register_and_auth_headers(
        client,
        username=f"legacy_fields_{uuid.uuid4().hex[:8]}",
        email=f"legacy_fields_{uuid.uuid4().hex[:8]}@example.com",
        password="S3cureP@ss99",
    )

    fields = await client.get("/api/v1/checkin-fields", headers=headers)
    assert fields.status_code == 404, fields.text


@pytest.mark.integration
async def test_legacy_market_phases_endpoint_returns_404(
    client: AsyncClient,
) -> None:
    headers = await _register_and_auth_headers(
        client,
        username=f"legacy_phase_{uuid.uuid4().hex[:8]}",
        email=f"legacy_phase_{uuid.uuid4().hex[:8]}@example.com",
        password="S3cureP@ss99",
    )

    phases = await client.get("/api/v1/market-phases", headers=headers)
    assert phases.status_code == 404, phases.text


@pytest.mark.integration
async def test_legacy_checkin_field_crud_endpoints_return_404(
    client: AsyncClient,
) -> None:
    headers = await _register_and_auth_headers(
        client,
        username=f"fields_{uuid.uuid4().hex[:8]}",
        email=f"fields_{uuid.uuid4().hex[:8]}@example.com",
        password="S3cureP@ss99",
    )

    create = await client.post(
        "/api/v1/checkin-fields",
        json={"field_name": "energy", "field_type": "integer"},
        headers=headers,
    )
    assert create.status_code == 404, create.text

    duplicate = await client.post(
        "/api/v1/checkin-fields",
        json={"field_name": "energy", "field_type": "integer"},
        headers=headers,
    )
    assert duplicate.status_code == 404, duplicate.text

    update = await client.patch(
        f"/api/v1/checkin-fields/{uuid.uuid4()}",
        json={"is_active": False},
        headers=headers,
    )
    assert update.status_code == 404, update.text

    list_active = await client.get(
        "/api/v1/checkin-fields?is_active=true",
        headers=headers,
    )
    assert list_active.status_code == 404, list_active.text

    duplicate_inactive = await client.post(
        "/api/v1/checkin-fields",
        json={"field_name": "energy", "field_type": "integer"},
        headers=headers,
    )
    assert duplicate_inactive.status_code == 404, duplicate_inactive.text

    immutable = await client.patch(
        f"/api/v1/checkin-fields/{uuid.uuid4()}",
        json={"field_type": "boolean"},
        headers=headers,
    )
    assert immutable.status_code == 404, immutable.text


@pytest.mark.integration
async def test_legacy_market_phase_crud_endpoints_return_404(
    client: AsyncClient,
) -> None:
    headers = await _register_and_auth_headers(
        client,
        username=f"phase_{uuid.uuid4().hex[:8]}",
        email=f"phase_{uuid.uuid4().hex[:8]}@example.com",
        password="S3cureP@ss99",
    )

    create = await client.post(
        "/api/v1/market-phases",
        json={"name": "trending", "label": "Trending", "color_hex": "#22c55e"},
        headers=headers,
    )
    assert create.status_code == 404, create.text

    duplicate = await client.post(
        "/api/v1/market-phases",
        json={"name": "trending", "label": "Another"},
        headers=headers,
    )
    assert duplicate.status_code == 404, duplicate.text

    update = await client.patch(
        f"/api/v1/market-phases/{uuid.uuid4()}",
        json={"label": "Strong Trend", "is_active": False},
        headers=headers,
    )
    assert update.status_code == 404, update.text

    recolor = await client.patch(
        f"/api/v1/market-phases/{uuid.uuid4()}",
        json={"color_hex": "#ef4444"},
        headers=headers,
    )
    assert recolor.status_code == 404, recolor.text

    list_active = await client.get(
        "/api/v1/market-phases?is_active=true",
        headers=headers,
    )
    assert list_active.status_code == 404, list_active.text

    duplicate_inactive = await client.post(
        "/api/v1/market-phases",
        json={"name": "trending", "label": "Duplicate inactive"},
        headers=headers,
    )
    assert duplicate_inactive.status_code == 404, duplicate_inactive.text

    immutable = await client.patch(
        f"/api/v1/market-phases/{uuid.uuid4()}",
        json={"name": "new-name"},
        headers=headers,
    )
    assert immutable.status_code == 404, immutable.text


@pytest.mark.integration
async def test_market_index_definition_crud_and_constraints(
    client: AsyncClient,
) -> None:
    headers = await _register_and_auth_headers(
        client,
        username=f"index_{uuid.uuid4().hex[:8]}",
        email=f"index_{uuid.uuid4().hex[:8]}@example.com",
        password="S3cureP@ss99",
    )

    seeded = await client.get("/api/v1/market-indexes", headers=headers)
    assert seeded.status_code == 200, seeded.text
    seeded_symbols = {item["symbol"] for item in seeded.json()["data"]}
    assert {"SPX", "NDX", "DAX"}.issubset(seeded_symbols)

    create = await client.post(
        "/api/v1/market-indexes",
        json={
            "symbol": "RTY",
            "name": "Russell 2000",
            "tradingview_url": "https://www.tradingview.com/symbols/TVC-RUT/",
            "is_active": True,
        },
        headers=headers,
    )
    assert create.status_code == 201, create.text
    index_id = create.json()["data"]["id"]

    duplicate = await client.post(
        "/api/v1/market-indexes",
        json={"symbol": "RTY", "name": "Duplicate"},
        headers=headers,
    )
    assert duplicate.status_code == 409, duplicate.text

    update = await client.put(
        f"/api/v1/market-indexes/{index_id}",
        json={"name": "Russell 2000 Index", "is_active": False},
        headers=headers,
    )
    assert update.status_code == 200, update.text
    assert update.json()["data"]["name"] == "Russell 2000 Index"
    assert update.json()["data"]["is_active"] is False

    list_active = await client.get("/api/v1/market-indexes?is_active=true", headers=headers)
    assert list_active.status_code == 200, list_active.text
    active_symbols = {item["symbol"] for item in list_active.json()["data"]}
    assert "RTY" not in active_symbols

    delete = await client.delete(f"/api/v1/market-indexes/{index_id}", headers=headers)
    assert delete.status_code == 204, delete.text


@pytest.mark.integration
async def test_daily_checkin_crud_and_validation(client: AsyncClient) -> None:
    headers = await _register_and_auth_headers(
        client,
        username=f"checkin_{uuid.uuid4().hex[:8]}",
        email=f"checkin_{uuid.uuid4().hex[:8]}@example.com",
        password="S3cureP@ss99",
    )
    other_headers = await _register_and_auth_headers(
        client,
        username=f"other_{uuid.uuid4().hex[:8]}",
        email=f"other_{uuid.uuid4().hex[:8]}@example.com",
        password="S3cureP@ss99",
    )

    create_without_phase = await client.post(
        "/api/v1/checkins",
        json={"date": "2026-01-10", "notes": "before market open"},
        headers=headers,
    )
    assert create_without_phase.status_code == 201, create_without_phase.text
    assert create_without_phase.json()["data"]["market_phase"] is None

    duplicate = await client.post(
        "/api/v1/checkins",
        json={"date": "2026-01-10"},
        headers=headers,
    )
    assert duplicate.status_code == 409, duplicate.text

    unknown_phase = await client.post(
        "/api/v1/checkins",
        json={"date": "2026-01-11", "market_phase": "unknown-phase"},
        headers=headers,
    )
    assert unknown_phase.status_code == 422, unknown_phase.text

    create_with_phase = await client.post(
        "/api/v1/checkins",
        json={"date": "2026-01-12", "market_phase": "bullish"},
        headers=headers,
    )
    assert create_with_phase.status_code == 201, create_with_phase.text

    indexes = await client.get("/api/v1/market-indexes", headers=headers)
    assert indexes.status_code == 200, indexes.text
    index_ids = [item["id"] for item in indexes.json()["data"][:2]]

    create_with_indices = await client.post(
        "/api/v1/checkins",
        json={
            "date": "2026-01-13",
            "market_phase": "bullish",
            "target_index_ids": index_ids,
        },
        headers=headers,
    )
    assert create_with_indices.status_code == 201, create_with_indices.text
    assert len(create_with_indices.json()["data"]["target_indices"]) == 2

    invalid_indices = await client.post(
        "/api/v1/checkins",
        json={
            "date": "2026-01-14",
            "target_index_ids": [str(uuid.uuid4())],
        },
        headers=headers,
    )
    assert invalid_indices.status_code == 422, invalid_indices.text

    patch_set_phase = await client.patch(
        "/api/v1/checkins/2026-01-10",
        json={
            "market_phase": "bullish",
            "custom_metrics": {"mood-level": 7},
            "target_index_ids": index_ids,
        },
        headers=headers,
    )
    assert patch_set_phase.status_code == 200, patch_set_phase.text
    assert patch_set_phase.json()["data"]["market_phase"] == "bullish"
    assert len(patch_set_phase.json()["data"]["target_indices"]) == 2

    read = await client.get("/api/v1/checkins/2026-01-10", headers=headers)
    assert read.status_code == 200, read.text

    cross_user = await client.get("/api/v1/checkins/2026-01-10", headers=other_headers)
    assert cross_user.status_code == 404, cross_user.text

    delete = await client.delete("/api/v1/checkins/2026-01-10", headers=headers)
    assert delete.status_code == 204, delete.text


@pytest.mark.integration
async def test_daily_checkin_list_pagination(client: AsyncClient) -> None:
    headers = await _register_and_auth_headers(
        client,
        username=f"list_{uuid.uuid4().hex[:8]}",
        email=f"list_{uuid.uuid4().hex[:8]}@example.com",
        password="S3cureP@ss99",
    )

    for day in ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"]:
        resp = await client.post(
            "/api/v1/checkins",
            json={"date": day},
            headers=headers,
        )
        assert resp.status_code == 201, resp.text

    first_page = await client.get("/api/v1/checkins?limit=2", headers=headers)
    assert first_page.status_code == 200, first_page.text
    first_data = first_page.json()["data"]
    assert len(first_data["items"]) == 2
    assert first_data["next_cursor"] == "2026-01-03"
    assert first_data["total"] == 4

    second_page = await client.get(
        f"/api/v1/checkins?limit=2&cursor={first_data['next_cursor']}",
        headers=headers,
    )
    assert second_page.status_code == 200, second_page.text
    second_data = second_page.json()["data"]
    assert len(second_data["items"]) == 2
    assert second_data["next_cursor"] is None

    range_page = await client.get(
        "/api/v1/checkins?from_date=2026-01-02&to_date=2026-01-03",
        headers=headers,
    )
    assert range_page.status_code == 200, range_page.text
    assert range_page.json()["data"]["total"] == 2

    empty_page = await client.get(
        "/api/v1/checkins?from_date=2027-01-01&to_date=2027-01-31",
        headers=headers,
    )
    assert empty_page.status_code == 200, empty_page.text
    empty_data = empty_page.json()["data"]
    assert empty_data["items"] == []
    assert empty_data["next_cursor"] is None
    assert empty_data["total"] == 0


@pytest.mark.integration
async def test_checkin_screenshot_upload_url_endpoint(client: AsyncClient) -> None:
    headers = await _register_and_auth_headers(
        client,
        username=f"upload_{uuid.uuid4().hex[:8]}",
        email=f"upload_{uuid.uuid4().hex[:8]}@example.com",
        password="S3cureP@ss99",
    )

    from app.core.config import settings

    original_backend = settings.storage_backend
    original_bucket = settings.storage_bucket
    original_public = settings.storage_public_url
    settings.storage_backend = "s3"
    settings.storage_bucket = "bucket"
    settings.storage_public_url = "https://storage.example.com"
    try:
        with patch("app.services.storage_service.boto3.client") as mock_client_factory:
            mock_client = mock_client_factory.return_value
            mock_client.generate_presigned_url.return_value = "https://signed.example.com/put"

            ok = await client.post(
                "/api/v1/checkins/screenshot-upload-url",
                json={"filename": "screen.png", "content_type": "image/png"},
                headers=headers,
            )
            assert ok.status_code == 200, ok.text
            body = ok.json()["data"]
            assert body["presigned_url"] == "https://signed.example.com/put"
            assert body["public_url"].startswith("https://storage.example.com/")
    finally:
        settings.storage_backend = original_backend
        settings.storage_bucket = original_bucket
        settings.storage_public_url = original_public

    unsupported = await client.post(
        "/api/v1/checkins/screenshot-upload-url",
        json={"filename": "screen.txt", "content_type": "text/plain"},
        headers=headers,
    )
    assert unsupported.status_code == 422, unsupported.text

    original_backend = settings.storage_backend
    settings.storage_backend = None
    try:
        not_configured = await client.post(
            "/api/v1/checkins/screenshot-upload-url",
            json={"filename": "screen.png", "content_type": "image/png"},
            headers=headers,
        )
        assert not_configured.status_code == 503, not_configured.text
    finally:
        settings.storage_backend = original_backend
