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
async def test_checkin_filtering_metadata_integration(client: AsyncClient):
    suffix = str(uuid.uuid4())[:8]
    headers = await _register_and_auth_headers(
        client, 
        username=f"filtertest_{suffix}", 
        email=f"filter_{suffix}@test.com", 
        password="password123"
    )
    
    # Setup Taxonomy
    t1 = await client.post("/api/v1/taxonomies", headers=headers, json={
        "name": f"Tag1_{suffix}", "scope": "checkins", "color_hex": "#FF0000"
    })
    t1_id = t1.json()["data"]["id"]
    
    # Setup Annotation Def
    ann = await client.post("/api/v1/annotation-definitions", headers=headers, json={
        "name": f"Score_{suffix}", "type": "int", "scope": "checkins"
    })
    ann_id = ann.json()["data"]["id"]
    
    # Create Check-ins
    c1 = await client.post("/api/v1/checkins", headers=headers, json={"date": "2024-06-01", "notes": "Low"})
    c1_id = c1.json()["data"]["id"]
    c2 = await client.post("/api/v1/checkins", headers=headers, json={"date": "2024-06-02", "notes": "High"})
    c2_id = c2.json()["data"]["id"]
    
    # Assign metadata
    await client.post(f"/api/v1/checkins/{c1_id}/taxonomies", headers=headers, json={"taxonomy_id": t1_id})
    await client.post(f"/api/v1/checkins/{c1_id}/annotations/{ann_id}", headers=headers, json={"value": 10})
    await client.post(f"/api/v1/checkins/{c2_id}/annotations/{ann_id}", headers=headers, json={"value": 90})
    
    # Filter by Taxonomy
    resp = await client.get(f"/api/v1/checkins?taxonomy_ids={t1_id}", headers=headers)
    items = resp.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["id"] == c1_id
    
    # Filter by Annotation (Score > 50)
    filters = [{"annotation_definition_id": ann_id, "operator": "gt", "value": 50}]
    resp = await client.get(f"/api/v1/checkins?annotation_filters={json.dumps(filters)}", headers=headers)
    items = resp.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["id"] == c2_id
