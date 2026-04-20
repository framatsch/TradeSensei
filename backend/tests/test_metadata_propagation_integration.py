"""Integration tests for metadata propagation and last-write-wins conflict handling.

These tests require a live database and are skipped in environments where the
database is unavailable (e.g. CI without a DB service or local runs without
Docker).  They correspond to OpenSpec phase-8 tasks 8.4.6, 8.4.7, and 8.4.8.

To run these tests locally, start the full stack first:

    docker compose up -d backend db

Then run:

    uv run pytest tests/test_metadata_propagation_integration.py -v
"""

import os
import uuid

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DB_INTEGRATION_TESTS") != "1",
    reason=(
        "requires live database; set RUN_DB_INTEGRATION_TESTS=1 and run "
        "with docker compose stack active"
    ),
)

_REGISTER_URL = "/api/v1/auth/register"
_TOKEN_URL = "/api/v1/auth/token"
_TRADES_URL = "/api/v1/trades"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user_payload() -> dict[str, str]:
    uid = uuid.uuid4().hex[:8]
    return {
        "email": f"test_{uid}@example.com",
        "password": "Test1234!",
        "full_name": "Test User",
    }


def _trade_payload(
    *,
    symbol: str = "AAPL",
    opened_at: str = "2026-01-01T09:30:00Z",
    closed_at: str | None = None,
    position_id: str | None = None,
    playbook_id: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "symbol": symbol,
        "direction": "LONG",
        "asset_class": "EQUITY",
        "quantity": "100",
        "entry_price": "150.00",
        "opened_at": opened_at,
        "commission": "1.00",
    }
    if closed_at:
        payload["closed_at"] = closed_at
        payload["exit_price"] = "155.00"
        payload["pnl"] = "500.00"
    if position_id:
        payload["position_id"] = position_id
    if playbook_id:
        payload["playbook_id"] = playbook_id
    return payload


async def _register_and_login(client: AsyncClient) -> str:
    """Register a fresh user and return the Bearer token."""
    user = _user_payload()
    await client.post(_REGISTER_URL, json=user)
    resp = await client.post(
        _TOKEN_URL,
        data={"username": user["email"], "password": user["password"]},
    )
    resp.raise_for_status()
    return str(resp.json()["access_token"])


# ---------------------------------------------------------------------------
# 8.4.6 — Day-1 entry + day-10 partial close propagation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_day1_entry_day10_partial_close_propagation(
    async_client: AsyncClient,
) -> None:
    """Updating metadata on a day-1 entry does not overwrite a closed sibling.

    Scenario:
      - User opens a 100-share AAPL position on day 1 (trade A).
      - On day 10 a partial close creates a linked 40-share closed trade (trade B),
        both sharing the same position_id.
      - User edits the playbook_id on trade A.
      - Trade B remains unchanged because propagation only applies to open siblings.

    OpenSpec task: 8.4.6
    """
    token = await _register_and_login(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    # Create a shared position_id for the two related trades.
    position_id = str(uuid.uuid4())
    playbook_resp = await async_client.post(
        "/api/v1/playbooks",
        json={"name": "Breakout Strategy", "description": ""},
        headers=headers,
    )
    playbook_id = playbook_resp.json()["data"]["id"]

    # Trade A: day-1 entry (still open).
    trade_a_resp = await async_client.post(
        _TRADES_URL,
        json=_trade_payload(
            symbol="AAPL",
            opened_at="2026-01-01T09:30:00Z",
            position_id=position_id,
        ),
        headers=headers,
    )
    trade_a_resp.raise_for_status()
    trade_a_id = trade_a_resp.json()["data"]["id"]

    # Trade B: day-10 partial close (closed), same position_id.
    trade_b_resp = await async_client.post(
        _TRADES_URL,
        json=_trade_payload(
            symbol="AAPL",
            opened_at="2026-01-10T09:30:00Z",
            closed_at="2026-01-10T15:00:00Z",
            position_id=position_id,
        ),
        headers=headers,
    )
    trade_b_resp.raise_for_status()
    trade_b_id = trade_b_resp.json()["data"]["id"]

    # Update trade A's playbook — propagation should NOT reach trade B because
    # trade B is already closed (propagation applies to open siblings only).
    patch_resp = await async_client.patch(
        f"{_TRADES_URL}/{trade_a_id}",
        json={"playbook_id": playbook_id},
        headers=headers,
    )
    patch_resp.raise_for_status()

    # Trade A should have the playbook.
    trade_a = (
        await async_client.get(f"{_TRADES_URL}/{trade_a_id}", headers=headers)
    ).json()["data"]
    assert trade_a["playbook_id"] == playbook_id

    # Trade B is closed — propagation must NOT overwrite it.
    trade_b = (
        await async_client.get(f"{_TRADES_URL}/{trade_b_id}", headers=headers)
    ).json()["data"]
    assert trade_b["playbook_id"] is None, (
        "Propagation must not overwrite a closed sibling trade"
    )


# ---------------------------------------------------------------------------
# 8.4.7 — No cross-position propagation for same symbol
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_cross_position_propagation_same_symbol(
    async_client: AsyncClient,
) -> None:
    """Propagation is strictly bounded to the same position_id.

    Two open AAPL trades with different position_ids must not share metadata
    even though they have the same underlying symbol.

    OpenSpec task: 8.4.7
    """
    token = await _register_and_login(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    position_a = str(uuid.uuid4())
    position_b = str(uuid.uuid4())

    playbook_resp = await async_client.post(
        "/api/v1/playbooks",
        json={"name": "Strategy A", "description": ""},
        headers=headers,
    )
    playbook_a_id = playbook_resp.json()["data"]["id"]

    # Trade in position A.
    trade_a_resp = await async_client.post(
        _TRADES_URL,
        json=_trade_payload(
            symbol="AAPL",
            opened_at="2026-02-01T09:30:00Z",
            position_id=position_a,
        ),
        headers=headers,
    )
    trade_a_resp.raise_for_status()
    trade_a_id = trade_a_resp.json()["data"]["id"]

    # Trade in position B — same symbol, different position.
    trade_b_resp = await async_client.post(
        _TRADES_URL,
        json=_trade_payload(
            symbol="AAPL",
            opened_at="2026-02-02T09:30:00Z",
            position_id=position_b,
        ),
        headers=headers,
    )
    trade_b_resp.raise_for_status()
    trade_b_id = trade_b_resp.json()["data"]["id"]

    # Patch playbook on trade A.
    patch_resp = await async_client.patch(
        f"{_TRADES_URL}/{trade_a_id}",
        json={"playbook_id": playbook_a_id},
        headers=headers,
    )
    patch_resp.raise_for_status()

    # Trade B in position B must NOT be affected.
    trade_b = (
        await async_client.get(f"{_TRADES_URL}/{trade_b_id}", headers=headers)
    ).json()["data"]
    assert trade_b["playbook_id"] is None, (
        f"Propagation leaked into a different position "
        f"({position_b}) for the same symbol"
    )


# ---------------------------------------------------------------------------
# 8.4.8 — Last-write-wins concurrency test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_last_write_wins_concurrent_metadata_conflict(
    async_client: AsyncClient,
) -> None:
    """Concurrent metadata edits resolve via last-write-wins.

    Scenario:
      - Two open AAPL trades share the same position_id (trade A and trade C).
      - Trade A is updated first with playbook P1 → propagates to trade C.
      - Trade C is then independently updated with playbook P2.
      - The propagation guard (updated_at <= source.updated_at) prevents
        trade C from being overwritten when trade A is edited again.

    Specifically, after trade C is edited independently, editing trade A again
    must NOT overwrite trade C's independently chosen playbook_id.

    OpenSpec task: 8.4.8
    """
    token = await _register_and_login(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    position_id = str(uuid.uuid4())

    playbook_p1_resp = await async_client.post(
        "/api/v1/playbooks",
        json={"name": "Playbook P1", "description": ""},
        headers=headers,
    )
    playbook_p1_id = playbook_p1_resp.json()["data"]["id"]

    playbook_p2_resp = await async_client.post(
        "/api/v1/playbooks",
        json={"name": "Playbook P2", "description": ""},
        headers=headers,
    )
    playbook_p2_id = playbook_p2_resp.json()["data"]["id"]

    # Both trades start without a playbook.
    trade_a_resp = await async_client.post(
        _TRADES_URL,
        json=_trade_payload(
            symbol="AAPL",
            opened_at="2026-03-01T09:30:00Z",
            position_id=position_id,
        ),
        headers=headers,
    )
    trade_a_resp.raise_for_status()
    trade_a_id = trade_a_resp.json()["data"]["id"]

    trade_c_resp = await async_client.post(
        _TRADES_URL,
        json=_trade_payload(
            symbol="AAPL",
            opened_at="2026-03-02T09:30:00Z",
            position_id=position_id,
        ),
        headers=headers,
    )
    trade_c_resp.raise_for_status()
    trade_c_id = trade_c_resp.json()["data"]["id"]

    # Step 1: Edit trade A with P1 → propagates to trade C (C's updated_at is older).
    await async_client.patch(
        f"{_TRADES_URL}/{trade_a_id}",
        json={"playbook_id": playbook_p1_id},
        headers=headers,
    )

    # Verify propagation happened.
    trade_c_v1 = (
        await async_client.get(f"{_TRADES_URL}/{trade_c_id}", headers=headers)
    ).json()["data"]
    assert trade_c_v1["playbook_id"] == playbook_p1_id

    # Step 2: Trade C is independently edited with P2 (now C.updated_at > A.updated_at).
    await async_client.patch(
        f"{_TRADES_URL}/{trade_c_id}",
        json={"playbook_id": playbook_p2_id},
        headers=headers,
    )

    # Step 3: Edit trade A with P1 again — propagation guard must NOT overwrite C.
    await async_client.patch(
        f"{_TRADES_URL}/{trade_a_id}",
        json={"playbook_id": playbook_p1_id},
        headers=headers,
    )

    # Trade C's independently-chosen P2 must survive.
    trade_c_v2 = (
        await async_client.get(f"{_TRADES_URL}/{trade_c_id}", headers=headers)
    ).json()["data"]
    assert trade_c_v2["playbook_id"] == playbook_p2_id, (
        "Last-write-wins guard failed: propagation overwrote "
        "a more-recently-edited sibling's playbook"
    )
