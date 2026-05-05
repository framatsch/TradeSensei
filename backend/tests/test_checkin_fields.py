"""Integration tests for check-in fields and market phases APIs."""

import uuid

import pytest
from httpx import AsyncClient


async def _auth_headers(client: AsyncClient, *, prefix: str) -> dict[str, str]:
    suffix = uuid.uuid4().hex[:8]
    username = f"{prefix}_{suffix}"
    email = f"{prefix}_{suffix}@example.com"
    password = "CheckinP@ss99"

    register = await client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    assert register.status_code == 201, register.text

    login = await client.post(
        "/api/v1/auth/token",
        data={"username": username, "password": password},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.integration
async def test_checkin_fields_get_post_delete(client: AsyncClient) -> None:
    headers = await _auth_headers(client, prefix="fields")

    get_fields = await client.get("/api/v1/checkin-fields", headers=headers)
    assert get_fields.status_code == 200, get_fields.text

    created = await client.post(
        "/api/v1/checkin-fields",
        headers=headers,
        json={"field_name": "discipline", "field_type": "integer"},
    )
    assert created.status_code == 201, created.text
    field_id = str(created.json()["data"]["id"])

    deleted = await client.delete(f"/api/v1/checkin-fields/{field_id}", headers=headers)
    assert deleted.status_code == 204, deleted.text

    missing = await client.delete(
        f"/api/v1/checkin-fields/{uuid.uuid4()}", headers=headers
    )
    assert missing.status_code == 404, missing.text
