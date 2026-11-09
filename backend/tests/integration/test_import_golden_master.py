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

"""Golden-master characterization suite for every broker ingestion path.

Each scenario imports a fixture into a fresh user/account and compares the
normalized persisted state (raw transactions, logical executions, trades incl.
combo legs and metadata) plus the returned result against a committed JSON
snapshot under ``tests/integration/golden/import/``.

Snapshots were captured on the code *before* the broker-adapter refactor and
must not drift. Any difference is a behavior change to investigate — not to
re-snapshot. Regenerate deliberately with ``UPDATE_GOLDEN=1``.
"""

from __future__ import annotations

import difflib
import json
import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import SCHWAB_ACCESS_TOKEN, SCHWAB_REFRESH_TOKEN, SCHWAB_TOKEN_EXPIRES_AT
from app.core.exceptions import FlexAPIError, RateLimitError
from app.models.account_property import AccountProperty
from app.models.playbook import Playbook
from app.models.taxonomy import Taxonomy
from app.models.trade import Trade
from app.models.trade_note import TradeNote
from app.models.trade_taxonomy import TradeTaxonomy
from app.services.audit_service import AuditEventService
from app.services.broker_service import BrokerService
from app.services.import_service import ImportService
from app.utils.encryption import encrypt_token
from app.services.brokers.contracts import BrokerType
from tests.utils.import_snapshot import (
    capture_import_state,
    dump_snapshot,
    normalize_error,
    normalize_import_result,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

_BACKEND_TESTS = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND_TESTS.parents[1]
_GOLDEN_DIR = Path(__file__).resolve().parent / "golden" / "import"
_IBKR_DIR = _BACKEND_TESTS / "fixtures" / "ibkr"
_SCHWAB_FIXTURE = _BACKEND_TESTS / "fixtures" / "schwab" / "schwab_golden_multi_account.json"
_SCHWAB_ACCOUNT = "10000001"
_SCHWAB_PART1_CUTOFF = "2026-09-09T00:00:00+0000"

_IBKR_FIXTURES: list[Path] = [
    *sorted(_IBKR_DIR.glob("*.xml")),
    _REPO_ROOT / "tests" / "test_data" / "ibkr" / "combo_positions.xml",
    _REPO_ROOT / "tests" / "test_data" / "ibkr" / "TraderJournal_anonymized_combined.xml",
]
_IBKR_SEQUENCES: list[tuple[str, str]] = [
    ("synthetic_year1.xml", "synthetic_year2.xml"),
    ("seed_open_year1.xml", "seed_close_year2.xml"),
]


# ─── Snapshot comparison ──────────────────────────────────────────────────────


def _assert_golden(name: str, snapshot: Any) -> None:
    path = _GOLDEN_DIR / f"{name}.json"
    actual = dump_snapshot(snapshot)
    if os.environ.get("UPDATE_GOLDEN") == "1":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8")
        return
    assert path.exists(), f"Missing golden snapshot {path.name}; generate it with UPDATE_GOLDEN=1."
    expected = path.read_text(encoding="utf-8")
    if expected != actual:
        diff = "".join(
            difflib.unified_diff(
                expected.splitlines(keepends=True),
                actual.splitlines(keepends=True),
                fromfile=f"golden/{path.name}",
                tofile="actual",
                n=2,
            )
        )
        pytest.fail(f"Golden master drift in {path.name}:\n{diff[:20000]}")


# ─── Setup helpers ────────────────────────────────────────────────────────────


async def _new_account(
    client: AsyncClient,
    account_type: str,
    account_number: str | None = None,
) -> tuple[str, uuid.UUID, uuid.UUID, uuid.UUID]:
    suffix = uuid.uuid4().hex[:8]
    email = f"gm_{suffix}@example.com"
    password = "GoldenMaster@99"
    reg = await client.post("/api/v1/auth/register", json={"username": f"gm_{suffix}", "email": email, "password": password})
    assert reg.status_code == 201, reg.text
    user_id = uuid.UUID(reg.json()["data"]["id"])
    login = await client.post("/api/v1/auth/token", data={"username": email, "password": password})
    assert login.status_code == 200, login.text
    token = str(login.json()["access_token"])
    headers = {"Authorization": f"Bearer {token}"}

    portfolio = await client.post("/api/v1/portfolios", headers=headers, json={"name": "Golden Portfolio", "base_currency": "USD"})
    assert portfolio.status_code == 201, portfolio.text
    portfolio_id = uuid.UUID(portfolio.json()["data"]["id"])

    body: dict[str, object] = {"name": "Golden Account", "type": account_type, "currency": "USD"}
    if account_number is not None:
        body["account_number"] = account_number
    account = await client.post(f"/api/v1/portfolios/{portfolio_id}/accounts", headers=headers, json=body)
    assert account.status_code == 201, account.text
    return token, user_id, portfolio_id, uuid.UUID(account.json()["data"]["id"])


@contextmanager
def _record_system_audit() -> Iterator[list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    original = AuditEventService.create_audit_event

    def _record(self: AuditEventService, **kwargs: Any) -> dict[str, Any]:
        if kwargs.get("method") == "SYSTEM":
            events.append(
                {
                    "action": kwargs.get("action"),
                    "resource_type": kwargs.get("resource_type"),
                    "parent_resource_type": kwargs.get("parent_resource_type"),
                    "path": kwargs.get("path"),
                    "status_code": kwargs.get("status_code"),
                    "metadata": kwargs.get("metadata"),
                }
            )
        return original(self, **kwargs)

    with patch.object(AuditEventService, "create_audit_event", _record):
        yield events


async def _run_import(
    session: AsyncSession,
    *,
    content: bytes,
    filename: str,
    broker: BrokerType,
    portfolio_id: uuid.UUID,
    account_id: uuid.UUID,
    user_id: uuid.UUID,
    overwrite_manually_edited: bool = False,
) -> dict[str, Any]:
    with _record_system_audit() as audit:
        try:
            result = await ImportService(session).import_trades(
                content=content,
                filename=filename,
                broker=broker,
                portfolio_id=portfolio_id,
                account_id=account_id,
                user_id=user_id,
                overwrite_manually_edited=overwrite_manually_edited,
            )
        except Exception as exc:  # noqa: BLE001 — expected errors are part of the snapshot
            await session.rollback()
            outcome: dict[str, Any] = {"error": normalize_error(exc, user_id, account_id)}
        else:
            await session.commit()
            outcome = {"result": normalize_import_result(result, user_id, account_id)}
    outcome["audit"] = audit
    outcome["state"] = await capture_import_state(session, user_id=user_id, account_id=account_id)
    return outcome


async def _protect_trades(session: AsyncSession, *, user_id: uuid.UUID, account_id: uuid.UUID) -> dict[str, Any]:
    """Attach notes/tags/playbook to the first open and first closed trade."""
    session.expire_all()
    trades = list((await session.execute(select(Trade).where(Trade.user_id == user_id, Trade.account_id == account_id))).scalars().all())

    def _key(t: Trade) -> tuple[str, str, str, str]:
        return (t.symbol, t.opened_at.isoformat(), t.closed_at.isoformat() if t.closed_at else "", str(t.quantity))

    closed = sorted((t for t in trades if t.closed_at is not None), key=_key)
    open_ = sorted((t for t in trades if t.closed_at is None), key=_key)
    picked = [group[0] for group in (closed, open_) if group]

    playbook = Playbook(user_id=user_id, name="Golden Playbook")
    taxonomy = Taxonomy(user_id=user_id, name="golden-tag", scope="trades", color_hex="#00AA00")
    session.add_all([playbook, taxonomy])
    await session.flush()
    for trade in picked:
        trade.is_manually_edited = True
        trade.journal = f"golden journal {trade.symbol}"
        trade.playbook_id = playbook.id
        session.add(TradeNote(trade_id=trade.id, user_id=user_id, content=f"golden note {trade.symbol}"))
        session.add(TradeTaxonomy(trade_id=trade.id, taxonomy_id=taxonomy.id))
    await session.commit()
    return {
        "protected": [{"symbol": t.symbol, "open": t.closed_at is None} for t in picked],
        "state": await capture_import_state(session, user_id=user_id, account_id=account_id),
    }


def _compact(steps: dict[str, Any]) -> dict[str, Any]:
    """Replace each step's state by a marker when it equals the previous step's state."""
    previous: Any = None
    for step in steps.values():
        state = step.get("state")
        if state is not None and state == previous:
            step["state"] = "<unchanged from previous step>"
        else:
            previous = state
    return steps


async def _single_fixture_scenario(
    session: AsyncSession,
    *,
    content: bytes,
    filename: str,
    broker: BrokerType,
    portfolio_id: uuid.UUID,
    account_id: uuid.UUID,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    args = {"content": content, "filename": filename, "broker": broker, "portfolio_id": portfolio_id, "account_id": account_id, "user_id": user_id}
    first = await _run_import(session, **args)
    second = await _run_import(session, **args)
    protection = await _protect_trades(session, user_id=user_id, account_id=account_id)
    protected = await _run_import(session, **args)
    reset = await _run_import(session, **args, overwrite_manually_edited=True)
    return _compact(
        {
            "first_import": first,
            "second_import": second,
            "protection": protection,
            "protected_reimport": protected,
            "reset_reimport": reset,
        }
    )


def _schwab_payload() -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(_SCHWAB_FIXTURE.read_text(encoding="utf-8"))
    return payload


def _schwab_single_account_payload() -> dict[str, Any]:
    payload = _schwab_payload()
    payload["accounts"] = [payload["accounts"][0]]
    return payload


def _schwab_part1_payload() -> dict[str, Any]:
    payload = _schwab_payload()
    cutoff = datetime.fromisoformat(_SCHWAB_PART1_CUTOFF.replace("+0000", "+00:00"))
    for entry in payload["accounts"]:
        entry["transactions"] = [
            txn
            for txn in entry["transactions"]
            if isinstance(txn, dict) and "time" in txn and datetime.fromisoformat(str(txn["time"]).replace("+0000", "+00:00")) < cutoff
        ]
    return payload


def _encode(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload).encode("utf-8")


# ─── IBKR file import ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("fixture", _IBKR_FIXTURES, ids=lambda p: p.stem)
async def test_ibkr_fixture_golden_master(fixture: Path, client: AsyncClient, db_session: AsyncSession) -> None:
    _, user_id, portfolio_id, account_id = await _new_account(client, "ibkr")
    snapshot = await _single_fixture_scenario(
        db_session,
        content=fixture.read_bytes(),
        filename=fixture.name,
        broker=BrokerType.IBKR,
        portfolio_id=portfolio_id,
        account_id=account_id,
        user_id=user_id,
    )
    _assert_golden(f"ibkr__{fixture.stem}", snapshot)


@pytest.mark.parametrize(("first", "second"), _IBKR_SEQUENCES, ids=lambda name: Path(name).stem)
async def test_ibkr_cross_file_protection_golden_master(first: str, second: str, client: AsyncClient, db_session: AsyncSession) -> None:
    _, user_id, portfolio_id, account_id = await _new_account(client, "ibkr")
    common = {"broker": BrokerType.IBKR, "portfolio_id": portfolio_id, "account_id": account_id, "user_id": user_id}
    snapshot = _compact(
        {
            "first_file": await _run_import(db_session, content=(_IBKR_DIR / first).read_bytes(), filename=first, **common),
            "protection": await _protect_trades(db_session, user_id=user_id, account_id=account_id),
            "second_file": await _run_import(db_session, content=(_IBKR_DIR / second).read_bytes(), filename=second, **common),
        }
    )
    _assert_golden(f"ibkr_sequence__{Path(first).stem}__{Path(second).stem}", snapshot)


# ─── Schwab file import ───────────────────────────────────────────────────────


async def test_schwab_multi_account_golden_master(client: AsyncClient, db_session: AsyncSession) -> None:
    _, user_id, portfolio_id, account_id = await _new_account(client, "schwab", account_number=_SCHWAB_ACCOUNT)
    snapshot = await _single_fixture_scenario(
        db_session,
        content=_SCHWAB_FIXTURE.read_bytes(),
        filename=_SCHWAB_FIXTURE.name,
        broker=BrokerType.SCHWAB,
        portfolio_id=portfolio_id,
        account_id=account_id,
        user_id=user_id,
    )
    _assert_golden("schwab__multi_account", snapshot)


async def test_schwab_cross_file_protection_golden_master(client: AsyncClient, db_session: AsyncSession) -> None:
    _, user_id, portfolio_id, account_id = await _new_account(client, "schwab", account_number=_SCHWAB_ACCOUNT)
    common = {"broker": BrokerType.SCHWAB, "portfolio_id": portfolio_id, "account_id": account_id, "user_id": user_id}
    snapshot = _compact(
        {
            "first_file": await _run_import(db_session, content=_encode(_schwab_part1_payload()), filename="part1.json", **common),
            "protection": await _protect_trades(db_session, user_id=user_id, account_id=account_id),
            "second_file": await _run_import(db_session, content=_SCHWAB_FIXTURE.read_bytes(), filename="full.json", **common),
        }
    )
    _assert_golden("schwab_sequence__part1__full", snapshot)


@pytest.mark.parametrize(
    ("case", "account_number", "single_account"),
    [
        ("auto_bind_single_account", None, True),
        ("mismatch", "99999999", False),
        ("ambiguous_unset_number", None, False),
    ],
)
async def test_schwab_account_binding_golden_master(
    case: str,
    account_number: str | None,
    single_account: bool,
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    _, user_id, portfolio_id, account_id = await _new_account(client, "schwab", account_number=account_number)
    payload = _schwab_single_account_payload() if single_account else _schwab_payload()
    snapshot = await _run_import(
        db_session,
        content=_encode(payload),
        filename="binding.json",
        broker=BrokerType.SCHWAB,
        portfolio_id=portfolio_id,
        account_id=account_id,
        user_id=user_id,
    )
    _assert_golden(f"schwab_binding__{case}", snapshot)


# ─── HTTP entry points ────────────────────────────────────────────────────────


async def test_schwab_json_endpoint_golden_master(client: AsyncClient, db_session: AsyncSession) -> None:
    token, user_id, portfolio_id, account_id = await _new_account(client, "schwab", account_number=_SCHWAB_ACCOUNT)
    with _record_system_audit() as audit:
        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/imports/schwab-json",
            params={"account_id": str(account_id)},
            json=_schwab_payload(),
            headers={"Authorization": f"Bearer {token}"},
        )
    snapshot = {
        "status_code": response.status_code,
        "body": normalize_import_result(response.json(), user_id, account_id),
        "audit": audit,
        "state": await capture_import_state(db_session, user_id=user_id, account_id=account_id),
    }
    _assert_golden("endpoint__schwab_json", snapshot)


@pytest.mark.parametrize(
    ("case", "account_type", "filename", "fixture"),
    [
        ("ibkr_xml", "ibkr", "combo_flip_edge_cases.xml", _IBKR_DIR / "combo_flip_edge_cases.xml"),
        ("schwab_json", "schwab", "schwab.json", _SCHWAB_FIXTURE),
        ("ibkr_rejects_json", "ibkr", "wrong.json", _SCHWAB_FIXTURE),
        ("ibkr_rejects_no_extension", "ibkr", "noext", _IBKR_DIR / "combo_flip_edge_cases.xml"),
        ("schwab_rejects_csv", "schwab", "schwab.csv", None),
        ("schwab_rejects_xml", "schwab", "schwab.xml", _IBKR_DIR / "combo_flip_edge_cases.xml"),
        ("manual_rejected", "manual", "anything.json", _SCHWAB_FIXTURE),
    ],
)
async def test_upload_endpoint_golden_master(
    case: str,
    account_type: str,
    filename: str,
    fixture: Path | None,
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    account_number = _SCHWAB_ACCOUNT if account_type == "schwab" else None
    token, user_id, portfolio_id, account_id = await _new_account(client, account_type, account_number=account_number)
    content = fixture.read_bytes() if fixture is not None else b"Date,Action\n"
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/imports/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"account_id": str(account_id)},
        files={"file": (filename, content, "application/octet-stream")},
    )
    snapshot = {
        "status_code": response.status_code,
        "body": normalize_import_result(response.json(), user_id, account_id),
        "state": await capture_import_state(db_session, user_id=user_id, account_id=account_id),
    }
    _assert_golden(f"endpoint__upload__{case}", snapshot)


# ─── Remote sync ──────────────────────────────────────────────────────────────


async def _add_properties(session: AsyncSession, account_id: uuid.UUID, properties: dict[str, str]) -> None:
    for key, value in properties.items():
        session.add(AccountProperty(account_id=account_id, key=key, value=encrypt_token(value)))
    await session.commit()


async def _run_sync(session: AsyncSession, *, user_id: uuid.UUID, account_id: uuid.UUID, **kwargs: Any) -> dict[str, Any]:
    with _record_system_audit() as audit:
        try:
            result = await BrokerService(session).sync_account(account_id=account_id, user_id=user_id, **kwargs)
        except Exception as exc:  # noqa: BLE001 — expected errors are part of the snapshot
            await session.rollback()
            outcome: dict[str, Any] = {"error": normalize_error(exc, user_id, account_id)}
        else:
            await session.commit()
            outcome = {"result": normalize_import_result(result, user_id, account_id)}
    outcome["audit"] = audit
    outcome["state"] = await capture_import_state(session, user_id=user_id, account_id=account_id)
    return outcome


async def test_ibkr_flex_sync_golden_master(client: AsyncClient, db_session: AsyncSession) -> None:
    _, user_id, _, account_id = await _new_account(client, "ibkr")
    await _add_properties(db_session, account_id, {"ibkr_flex_token": "tok", "ibkr_flex_query_id": "4242"})
    xml = (_IBKR_DIR / "combo_flip_edge_cases.xml").read_bytes()
    fetch = AsyncMock(return_value=xml)
    with patch("app.services.flex_import_service.FlexImportService.fetch_flex_report", fetch):
        first = await _run_sync(db_session, user_id=user_id, account_id=account_id, from_date="20260901")
        second = await _run_sync(db_session, user_id=user_id, account_id=account_id, from_date="20260901")
    snapshot = {"fetch_calls": [dict(call.kwargs) for call in fetch.await_args_list], **_compact({"first_sync": first, "second_sync": second})}
    _assert_golden("sync__ibkr_flex", snapshot)


@pytest.mark.parametrize(
    ("case", "error"),
    [
        ("rate_limit", RateLimitError("Too many requests. Please try again in 10 minutes", 600)),
        ("transient", FlexAPIError("Flex SendRequest failed: Statement could not be generated at this time. Please try again shortly.")),
        ("permanent", FlexAPIError("Flex SendRequest failed: Invalid token")),
    ],
)
async def test_ibkr_flex_sync_error_mapping_golden_master(case: str, error: Exception, client: AsyncClient, db_session: AsyncSession) -> None:
    _, user_id, _, account_id = await _new_account(client, "ibkr")
    await _add_properties(db_session, account_id, {"ibkr_flex_token": "tok", "ibkr_flex_query_id": "4242"})
    with patch("app.services.flex_import_service.FlexImportService.fetch_flex_report", AsyncMock(side_effect=error)):
        outcome = await _run_sync(db_session, user_id=user_id, account_id=account_id, from_date="20260901")
    _assert_golden(f"sync__ibkr_flex_error__{case}", outcome)


@pytest.mark.parametrize(("case", "account_type"), [("ibkr_missing_token", "ibkr"), ("manual", "manual"), ("schwab_not_connected", "schwab")])
async def test_sync_configuration_errors_golden_master(case: str, account_type: str, client: AsyncClient, db_session: AsyncSession) -> None:
    _, user_id, _, account_id = await _new_account(client, account_type)
    outcome = await _run_sync(db_session, user_id=user_id, account_id=account_id)
    _assert_golden(f"sync__config_error__{case}", outcome)


async def test_schwab_sync_golden_master(client: AsyncClient, db_session: AsyncSession) -> None:
    _, user_id, _, account_id = await _new_account(client, "schwab")
    expires_at = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    await _add_properties(
        db_session,
        account_id,
        {
            "schwab_app_key": "app-key",
            "schwab_app_secret": "app-secret",
            SCHWAB_ACCESS_TOKEN: "access",
            SCHWAB_REFRESH_TOKEN: "refresh",
            SCHWAB_TOKEN_EXPIRES_AT: expires_at,
        },
    )
    transactions = _schwab_payload()["accounts"][0]["transactions"]
    account_numbers = AsyncMock(return_value=[{"accountNumber": _SCHWAB_ACCOUNT, "hashValue": "hash-10000001"}])
    get_transactions = AsyncMock(return_value=transactions)
    refresh = AsyncMock(side_effect=AssertionError("token refresh must not be called"))
    with (
        patch("app.utils.schwab_client.SchwabClient.get_account_numbers", account_numbers),
        patch("app.utils.schwab_client.SchwabClient.get_transactions", get_transactions),
        patch("app.utils.schwab_client.SchwabClient.refresh_access_token", refresh),
    ):
        first = await _run_sync(db_session, user_id=user_id, account_id=account_id, days=30)
        second = await _run_sync(db_session, user_id=user_id, account_id=account_id, days=30)
    snapshot = {
        "account_numbers_calls": [dict(call.kwargs) for call in account_numbers.await_args_list],
        "transactions_calls": [
            {
                "access_token": call.kwargs["access_token"],
                "account_hash": call.kwargs["account_hash"],
                "window_days": (call.kwargs["to_date"] - call.kwargs["from_date"]).days,
            }
            for call in get_transactions.await_args_list
        ],
        **_compact({"first_sync": first, "second_sync": second}),
    }
    _assert_golden("sync__schwab", snapshot)
