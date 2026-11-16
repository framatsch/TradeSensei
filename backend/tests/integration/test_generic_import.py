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

"""End-to-end behaviour of generic execution imports into GENERIC accounts."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import GenericFormatValidationError
from app.models.account_property import AccountProperty
from app.models.broker_raw_transaction import BrokerRawTransaction
from app.models.corporate_action import CorporateAction
from app.models.logical_execution import LogicalExecution
from app.models.trade import Trade
from app.services.audit_service import AuditEventService
from app.services.brokers.contracts import BrokerType
from app.services.import_service import ImportService
from app.utils.parsers.ibkr_xml import IBKRXMLParser
from tests.utils.generic_import import ibkr_fixture_to_generic
from tests.utils.import_snapshot import capture_import_state

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

_IBKR_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "ibkr"
_IBKR_FIXTURES = sorted(_IBKR_DIR.glob("*.xml"))
_MANUAL_CSV_DIR = Path(__file__).resolve().parents[3] / "tests" / "test_data" / "generic"


# ─── Helpers ──────────────────────────────────────────────────────────────────


class _Ctx:
    """Authenticated user with one portfolio."""

    def __init__(self, client: AsyncClient, token: str, user_id: uuid.UUID, portfolio_id: uuid.UUID) -> None:
        self.client = client
        self.headers = {"Authorization": f"Bearer {token}"}
        self.user_id = user_id
        self.portfolio_id = portfolio_id

    async def account(self, account_type: str = "generic") -> uuid.UUID:
        resp = await self.client.post(
            f"/api/v1/portfolios/{self.portfolio_id}/accounts",
            headers=self.headers,
            json={"name": f"{account_type} account", "type": account_type, "currency": "USD"},
        )
        assert resp.status_code == 201, resp.text
        return uuid.UUID(resp.json()["data"]["id"])

    async def post_file(self, endpoint: str, account_id: uuid.UUID, filename: str, content: bytes) -> Any:
        return await self.client.post(
            f"/api/v1/portfolios/{self.portfolio_id}/imports/{endpoint}",
            headers=self.headers,
            data={"account_id": str(account_id)},
            files={"file": (filename, content, "application/octet-stream")},
        )


async def _new_user(client: AsyncClient) -> _Ctx:
    suffix = uuid.uuid4().hex[:8]
    email = f"gen_{suffix}@example.com"
    password = "GenericImport@99"
    reg = await client.post("/api/v1/auth/register", json={"username": f"gen_{suffix}", "email": email, "password": password})
    assert reg.status_code == 201, reg.text
    login = await client.post("/api/v1/auth/token", data={"username": email, "password": password})
    assert login.status_code == 200, login.text
    token = str(login.json()["access_token"])
    portfolio = await client.post(
        "/api/v1/portfolios", headers={"Authorization": f"Bearer {token}"}, json={"name": "Generic Portfolio", "base_currency": "USD"}
    )
    assert portfolio.status_code == 201, portfolio.text
    return _Ctx(client, token, uuid.UUID(reg.json()["data"]["id"]), uuid.UUID(portfolio.json()["data"]["id"]))


def _execution(**changes: object) -> dict[str, object]:
    row: dict[str, object] = {
        "executed_at": "2026-01-15T14:30:00Z",
        "symbol": "AAPL",
        "asset_class": "EQUITY",
        "side": "BUY",
        "quantity": "10",
        "price": "200",
        "commission": "1",
        "currency": "USD",
    }
    row.update(changes)
    return {key: value for key, value in row.items() if value is not None}


def _document(executions: list[dict[str, object]], splits: list[dict[str, object]] | None = None) -> bytes:
    body: dict[str, object] = {"format": "tradesensei.executions", "version": "1.0", "executions": executions}
    if splits is not None:
        body["corporate_actions"] = splits
    return json.dumps(body).encode()


_OPEN = _execution(external_id="F-1", position_effect="OPEN")
_CLOSE = _execution(external_id="F-2", executed_at="2026-01-20T15:00:00Z", side="SELL", price="210", position_effect="CLOSE")


async def _count(session: AsyncSession, model: Any, **filters: object) -> int:
    stmt = select(func.count()).select_from(model)
    for key, value in filters.items():
        stmt = stmt.where(getattr(model, key) == value)
    return int((await session.execute(stmt)).scalar_one())


async def _counts(session: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID) -> dict[str, int]:
    session.expire_all()
    return {
        "raw": await _count(session, BrokerRawTransaction, user_id=user_id),
        "executions": await _count(session, LogicalExecution, user_id=user_id),
        "trades": await _count(session, Trade, user_id=user_id),
        "splits": await _count(session, CorporateAction, user_id=user_id),
        "properties": await _count(session, AccountProperty, account_id=account_id),
    }


async def _import(session: AsyncSession, ctx: _Ctx, account_id: uuid.UUID, content: bytes, *, broker: BrokerType = BrokerType.GENERIC) -> Any:
    filename = "fixture.xml" if broker == BrokerType.IBKR else "fixture.json"
    result = await ImportService(session).import_trades(
        content=content, filename=filename, broker=broker, portfolio_id=ctx.portfolio_id, account_id=account_id, user_id=ctx.user_id
    )
    await session.commit()
    return result


@contextmanager
def _record_audit() -> Iterator[list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    original = AuditEventService.create_audit_event

    def _record(self: AuditEventService, **kwargs: Any) -> Any:
        events.append(kwargs)
        return original(self, **kwargs)

    with patch.object(AuditEventService, "create_audit_event", _record):
        yield events


# Trade and execution fields that legitimately differ between a native IBKR
# account and a GENERIC account fed the same fills: raw identities only.
_EXECUTION_IDENTITY_FIELDS = {"source_id"}


def _economic_state(state: dict[str, Any]) -> dict[str, Any]:
    """Project captured state onto broker-independent economic content."""
    executions = [{k: v for k, v in row.items() if k not in _EXECUTION_IDENTITY_FIELDS} for row in state["logical_executions"]]
    # IBKR reports an empty brokerageOrderID attribute; the public format only
    # knows an absent order_id.
    trades = [{**row, "broker_order_id": row["broker_order_id"] or None} for row in state["trades"]]
    return {"trades": trades, "logical_executions": executions}


# ─── Account type and ID strategy lock (3.2, 3.3, 3.4) ───────────────────────


async def test_generic_account_creation_needs_no_credentials_and_rejects_sync(client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _new_user(client)
    account_id = await ctx.account()
    sync = await client.post(f"/api/v1/broker/sync/{account_id}", headers=ctx.headers)
    assert sync.status_code == 400, sync.text
    assert "does not support API sync" in sync.json()["detail"]
    connection = await client.post(f"/api/v1/portfolios/{ctx.portfolio_id}/accounts/test-connection", headers=ctx.headers, json={"type": "generic"})
    assert connection.status_code == 422
    assert await _counts(db_session, ctx.user_id, account_id) == {"raw": 0, "executions": 0, "trades": 0, "splits": 0, "properties": 0}


async def test_first_import_records_strategy_and_audits_safe_metadata(client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _new_user(client)
    account_id = await ctx.account()
    with _record_audit() as events:
        await _import(db_session, ctx, account_id, _document([_OPEN]))
    strategy_events = [e for e in events if e.get("action") == "account.import_strategy_set"]
    assert len(strategy_events) == 1
    assert strategy_events[0]["metadata"] == {"account_id": str(account_id), "strategy": "external_id"}
    assert strategy_events[0]["resource_id"] == account_id
    serialized = json.dumps({k: v for k, v in strategy_events[0].items() if k != "status_code"}, default=str)
    for sensitive in ("AAPL", "200", "price", "quantity", "pnl"):
        assert sensitive not in serialized
    # The lock is set exactly once: a second import emits no further event.
    with _record_audit() as events:
        await _import(db_session, ctx, account_id, _document([_CLOSE]))
    assert not [e for e in events if e.get("action") == "account.import_strategy_set"]


async def test_strategy_switch_rejected_without_writes_then_reset_by_clear_all(client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _new_user(client)
    account_id = await ctx.account()
    fingerprint_file = _document([_execution(position_effect="OPEN")])
    external_file = _document([_CLOSE])
    first = await ctx.post_file("upload", account_id, "a.json", fingerprint_file)
    assert first.status_code == 200, first.text
    before = await _counts(db_session, ctx.user_id, account_id)

    rejected = await ctx.post_file("upload", account_id, "b.json", external_file)
    assert rejected.status_code == 422, rejected.text
    assert [issue["code"] for issue in rejected.json()["detail"]] == ["id_strategy_mismatch"]
    assert await _counts(db_session, ctx.user_id, account_id) == before

    preview = await ctx.post_file("preview", account_id, "b.json", external_file)
    assert preview.status_code == 200, preview.text
    assert preview.json()["data"]["strategy_conflict"] is True
    assert preview.json()["data"]["recorded_strategy"] == "fingerprint"

    cleared = await client.delete(f"/api/v1/portfolios/{ctx.portfolio_id}/accounts/{account_id}/trades?acknowledged=true", headers=ctx.headers)
    assert cleared.status_code == 200, cleared.text
    assert (await _counts(db_session, ctx.user_id, account_id))["properties"] == 0

    retried = await ctx.post_file("upload", account_id, "b.json", external_file)
    assert retried.status_code == 200, retried.text
    preview = await ctx.post_file("preview", account_id, "b.json", external_file)
    assert preview.json()["data"]["recorded_strategy"] == "external_id"


async def test_fresh_start_reports_row_issues_and_releases_the_strategy_lock(client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _new_user(client)
    account_id = await ctx.account()
    fingerprint_file = _document([_execution(position_effect="OPEN")])

    async def fresh_start(filename: str, content: bytes) -> Any:
        return await client.post(
            f"/api/v1/portfolios/{ctx.portfolio_id}/imports/{account_id}/fresh-start",
            headers=ctx.headers,
            data={"acknowledged": "true"},
            files={"file": (filename, content, "application/octet-stream")},
        )

    first = await ctx.post_file("upload", account_id, "a.json", _document([_OPEN]))
    assert first.status_code == 200, first.text

    # Fresh-start empties the account, so the other ID strategy is accepted
    # instead of being rejected against the strategy recorded above.
    switched = await fresh_start("b.json", fingerprint_file)
    assert switched.status_code == 200, switched.text
    preview = await ctx.post_file("preview", account_id, "b.json", fingerprint_file)
    assert preview.json()["data"]["recorded_strategy"] == "fingerprint"
    assert (await _counts(db_session, ctx.user_id, account_id))["properties"] == 1

    # An invalid generic file yields row-level issues, not an opaque 400.
    invalid = await fresh_start("bad.json", _document([_execution(external_id="F-9", quantity="0")]))
    assert invalid.status_code == 422, invalid.text
    assert [(issue["row"], issue["field"]) for issue in invalid.json()["detail"]] == [(0, "quantity")]


# ─── API (4.1, 4.2, 4.3) ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("broker", "source_name", "total"),
    [
        ("ibkr", "TraderJournal_anonymized_combined.xml", 339),
        ("ibkr", "combo_positions.xml", 16),
        ("schwab", "schwab_aggregation.json", 7),
        ("schwab", "schwab_short_roundtrip.json", 2),
        ("schwab", "schwab_transactions_real_trimmed.json", 5),
    ],
)
async def test_manual_csv_matches_native_import_and_reimport(broker: str, source_name: str, total: int, client: AsyncClient, db_session: AsyncSession) -> None:
    source = _MANUAL_CSV_DIR.parent / broker / source_name
    fixture = _MANUAL_CSV_DIR / broker / f"{source.stem}.csv"
    native_ctx = await _new_user(client)
    native_account = await native_ctx.account(broker)
    native_upload = await native_ctx.post_file("upload", native_account, source.name, source.read_bytes())
    assert native_upload.status_code == 200, native_upload.text
    native = await capture_import_state(db_session, user_id=native_ctx.user_id, account_id=native_account)

    ctx = await _new_user(client)
    account_id = await ctx.account()
    content = fixture.read_bytes()
    before = await _counts(db_session, ctx.user_id, account_id)
    preview = await ctx.post_file("preview", account_id, fixture.name, content)
    assert preview.status_code == 200, preview.text
    data = preview.json()["data"]
    assert (data["total"], data["new"], data["already_imported"], data["detected_strategy"]) == (total, total, 0, "external_id")
    assert data["recorded_strategy"] is None
    assert await _counts(db_session, ctx.user_id, account_id) == before

    uploaded = await ctx.post_file("upload", account_id, fixture.name, content)
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["data"]["raw_transactions_created"] == total
    after = await _counts(db_session, ctx.user_id, account_id)
    generic = await capture_import_state(db_session, user_id=ctx.user_id, account_id=account_id)
    assert native["trades"], "Native source must produce trades."
    assert _economic_state(generic) == _economic_state(native)
    assert generic["corporate_actions"] == native["corporate_actions"]

    preview = await ctx.post_file("preview", account_id, fixture.name, content)
    assert preview.status_code == 200, preview.text
    data = preview.json()["data"]
    assert (data["total"], data["new"], data["already_imported"], data["recorded_strategy"]) == (total, 0, total, "external_id")
    repeated = await ctx.post_file("upload", account_id, fixture.name, content)
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["data"]["raw_transactions_created"] == 0
    assert await _counts(db_session, ctx.user_id, account_id) == after
    reimported = await capture_import_state(db_session, user_id=ctx.user_id, account_id=account_id)
    assert _economic_state(reimported) == _economic_state(generic)


@pytest.mark.parametrize(("filename", "content"), [("trades.json", _document([_OPEN, _CLOSE])), ("trades.csv", None)])
async def test_upload_generic_file_imports_through_pipeline(filename: str, content: bytes | None, client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _new_user(client)
    account_id = await ctx.account()
    if content is None:
        content = (
            b"external_id,executed_at,symbol,asset_class,side,position_effect,quantity,price,commission,currency\n"
            b"F-1,2026-01-15T14:30:00Z,AAPL,EQUITY,BUY,OPEN,10,200,1,USD\n"
            b"F-2,2026-01-20T15:00:00Z,AAPL,EQUITY,SELL,CLOSE,10,210,1,USD\n"
        )
    response = await ctx.post_file("upload", account_id, filename, content)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["raw_transactions_created"] == 2
    assert data["trades_created"] == 1
    db_session.expire_all()
    trade = (await db_session.execute(select(Trade).where(Trade.user_id == ctx.user_id))).scalar_one()
    assert trade.closed_at is not None
    assert str(trade.pnl) == "100.00000000"


@pytest.mark.parametrize(("account_type", "filename"), [("ibkr", "trades.csv"), ("schwab", "trades.csv"), ("manual", "trades.json")])
async def test_generic_file_rejected_for_other_account_types(account_type: str, filename: str, client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _new_user(client)
    account_id = await ctx.account(account_type)
    response = await ctx.post_file("upload", account_id, filename, _document([_OPEN]))
    assert response.status_code == 422, response.text
    preview = await ctx.post_file("preview", account_id, filename, _document([_OPEN]))
    assert preview.status_code == 422, preview.text
    assert (await _counts(db_session, ctx.user_id, account_id))["raw"] == 0


async def test_native_file_rejected_for_generic_account(client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _new_user(client)
    account_id = await ctx.account()
    response = await ctx.post_file("upload", account_id, "native.xml", (_IBKR_DIR / "synthetic_year1.xml").read_bytes())
    assert response.status_code == 422, response.text
    assert (await _counts(db_session, ctx.user_id, account_id))["raw"] == 0


async def test_invalid_file_rejected_all_or_nothing_with_safe_errors(client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _new_user(client)
    account_id = await ctx.account()
    content = _document([_OPEN, _execution(external_id="F-9", executed_at="2026-01-15T14:30:00", price="987.65")])
    for endpoint in ("upload", "preview"):
        response = await ctx.post_file(endpoint, account_id, "bad.json", content)
        assert response.status_code == 422, response.text
        detail = response.json()["detail"]
        assert detail == [{"row": 1, "field": "executed_at", "code": detail[0]["code"], "message": detail[0]["message"]}]
        assert "987.65" not in response.text
    assert await _counts(db_session, ctx.user_id, account_id) == {"raw": 0, "executions": 0, "trades": 0, "splits": 0, "properties": 0}


async def test_preview_writes_nothing_and_reports_counts_after_partial_reimport(client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _new_user(client)
    account_id = await ctx.account()
    split = [{"type": "SPLIT", "symbol": "AAPL", "date": "2026-02-01", "ratio": "2"}]
    full = _document([_OPEN, _CLOSE, _execution(external_id="F-3", executed_at="2026-03-01T15:00:00Z")], split)

    before = await _counts(db_session, ctx.user_id, account_id)
    preview = await ctx.post_file("preview", account_id, "full.json", full)
    assert preview.status_code == 200, preview.text
    assert preview.json()["data"] == {
        "detected_strategy": "external_id",
        "recorded_strategy": None,
        "strategy_conflict": False,
        "total": 3,
        "new": 3,
        "already_imported": 0,
        "suppressed": 0,
        "new_splits": 1,
        "conflicting_splits": 0,
        "warnings": [],
        "errors": [],
    }
    assert await _counts(db_session, ctx.user_id, account_id) == before

    partial = await ctx.post_file("upload", account_id, "partial.json", _document([_OPEN, _CLOSE]))
    assert partial.status_code == 200, partial.text
    preview = await ctx.post_file("preview", account_id, "full.json", full)
    data = preview.json()["data"]
    assert (data["total"], data["new"], data["already_imported"], data["recorded_strategy"]) == (3, 1, 2, "external_id")

    complete = await ctx.post_file("upload", account_id, "full.json", full)
    assert complete.status_code == 200, complete.text
    data = (await ctx.post_file("preview", account_id, "full.json", full)).json()["data"]
    assert (data["new"], data["already_imported"], data["new_splits"]) == (0, 3, 0)


async def test_schema_and_template_endpoints(client: AsyncClient) -> None:
    ctx = await _new_user(client)
    unauthenticated = await client.get("/api/v1/imports/formats/generic")
    assert unauthenticated.status_code == 401

    schema = await client.get("/api/v1/imports/formats/generic", headers=ctx.headers)
    assert schema.status_code == 200
    body = schema.json()
    assert "data" not in body
    assert {"format", "version", "executions"} <= set(body["required"])
    assert body["additionalProperties"] is False

    template = await client.get("/api/v1/imports/formats/generic/template.csv", headers=ctx.headers)
    assert template.status_code == 200
    assert template.headers["content-type"].startswith("text/csv")
    assert "attachment" in template.headers["content-disposition"]
    lines = template.text.strip().splitlines()
    assert len(lines) == 3

    account_id = await ctx.account()
    preview = await ctx.post_file("preview", account_id, "template.csv", template.content)
    assert preview.status_code == 200, preview.text
    assert preview.json()["data"]["total"] == 2


# ─── Equivalence with native IBKR imports (5.2, 5.3) ─────────────────────────


def _has_simultaneous_fills(content: bytes, name: str) -> bool:
    """True if two fills share timestamp and contract (FIFO order then needs IDs)."""
    raws, _ = IBKRXMLParser().parse_raw(content, name)
    keys = [(raw.executed_at, raw.symbol, raw.conid) for raw in raws]
    return len(keys) != len(set(keys))


async def _native_and_generic(client: AsyncClient, session: AsyncSession, fixture: Path, external_ids: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    native_ctx = await _new_user(client)
    native_account = await native_ctx.account("ibkr")
    generic_ctx = await _new_user(client)
    generic_account = await generic_ctx.account()
    content = fixture.read_bytes()
    await _import(session, native_ctx, native_account, content, broker=BrokerType.IBKR)
    await _import(session, generic_ctx, generic_account, ibkr_fixture_to_generic(content, fixture.name, external_ids=external_ids))
    native = await capture_import_state(session, user_id=native_ctx.user_id, account_id=native_account)
    generic = await capture_import_state(session, user_id=generic_ctx.user_id, account_id=generic_account)
    return native, generic


@pytest.mark.parametrize("fixture", _IBKR_FIXTURES, ids=lambda path: path.name)
@pytest.mark.parametrize("external_ids", [True, False], ids=["external-id", "fingerprint"])
async def test_generic_import_matches_native_ibkr_import(fixture: Path, external_ids: bool, client: AsyncClient, db_session: AsyncSession) -> None:
    if not external_ids and _has_simultaneous_fills(fixture.read_bytes(), fixture.name):
        pytest.skip("Documented limitation: without IDs, simultaneous fills on one contract have no guaranteed FIFO order.")
    native, generic = await _native_and_generic(client, db_session, fixture, external_ids)
    assert native["trades"], "fixture must produce trades"
    assert _economic_state(generic) == _economic_state(native)
    assert generic["corporate_actions"] == native["corporate_actions"]


async def test_fingerprint_simultaneous_fills_import_every_fill_but_may_match_lots_differently(client: AsyncClient, db_session: AsyncSession) -> None:
    fixture = _IBKR_DIR / "synthetic_year1.xml"
    assert _has_simultaneous_fills(fixture.read_bytes(), fixture.name)
    native, generic = await _native_and_generic(client, db_session, fixture, external_ids=False)
    assert len(generic["raw_transactions"]) == len(native["raw_transactions"])

    def closed_quantity(state: dict[str, Any]) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = {}
        for trade in state["trades"]:
            if trade["closed_at"] is not None:
                totals[trade["symbol"]] = totals.get(trade["symbol"], Decimal(0)) + Decimal(trade["quantity"])
        return totals

    assert closed_quantity(generic) == closed_quantity(native)


# ─── Idempotency (5.4) ───────────────────────────────────────────────────────


@pytest.mark.parametrize("external_ids", [True, False], ids=["external-id", "fingerprint"])
async def test_reimport_and_overlapping_windows_insert_each_fill_once(external_ids: bool, client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _new_user(client)
    account_id = await ctx.account()

    def fill(day: int, fill_id: str, side: str = "BUY") -> dict[str, object]:
        return _execution(external_id=fill_id if external_ids else None, executed_at=f"2026-{day:02d}-10T15:00:00Z", side=side, quantity="1")

    jan_mar = _document([fill(1, "J"), fill(2, "F"), fill(3, "M")])
    mar_may = _document([fill(3, "M"), fill(4, "A"), fill(5, "Y", "SELL")])

    first = await _import(db_session, ctx, account_id, jan_mar)
    again = await _import(db_session, ctx, account_id, jan_mar)
    overlap = await _import(db_session, ctx, account_id, mar_may)
    assert (first.raw_transactions_created, again.raw_transactions_created, overlap.raw_transactions_created) == (3, 0, 2)
    assert (await _counts(db_session, ctx.user_id, account_id))["raw"] == 5


async def test_identical_partial_fills_without_ids_import_as_distinct_ordinals(client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _new_user(client)
    account_id = await ctx.account()
    content = _document([_execution(), _execution()])
    first = await _import(db_session, ctx, account_id, content)
    again = await _import(db_session, ctx, account_id, content)
    assert (first.raw_transactions_created, again.raw_transactions_created) == (2, 0)
    db_session.expire_all()
    ids = sorted((await db_session.execute(select(BrokerRawTransaction.id).where(BrokerRawTransaction.user_id == ctx.user_id))).scalars())
    assert [raw_id.rsplit(":", 1)[-1] for raw_id in ids] == ["1", "2"]
    assert all(f":generic:{account_id}:f:" in raw_id for raw_id in ids)


async def test_same_external_id_in_two_generic_accounts_both_persist(client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _new_user(client)
    account_a = await ctx.account()
    account_b = await ctx.account()
    await _import(db_session, ctx, account_a, _document([_execution(external_id="1001")]))
    result = await _import(db_session, ctx, account_b, _document([_execution(external_id="1001", symbol="MSFT")]))
    assert result.raw_transactions_created == 1
    db_session.expire_all()
    rows = (await db_session.execute(select(BrokerRawTransaction).where(BrokerRawTransaction.user_id == ctx.user_id))).scalars().all()
    assert {(row.account_id, row.symbol) for row in rows} == {(account_a, "AAPL"), (account_b, "MSFT")}
    assert {row.id for row in rows} == {f"{ctx.user_id}:generic:{account_a}:x:1001", f"{ctx.user_id}:generic:{account_b}:x:1001"}


# ─── Protected trades (5.5) ──────────────────────────────────────────────────


async def test_protected_open_trade_survives_reimport_and_is_closed_by_later_file(client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _new_user(client)
    account_id = await ctx.account()
    await _import(db_session, ctx, account_id, _document([_OPEN]))

    db_session.expire_all()
    trade = (await db_session.execute(select(Trade).where(Trade.user_id == ctx.user_id))).scalar_one()
    trade.journal = "protected journal"
    trade.is_manually_edited = True
    await db_session.commit()
    trade_id = trade.id

    reimport = await _import(db_session, ctx, account_id, _document([_OPEN]))
    assert reimport.raw_transactions_created == 0
    later = await _import(db_session, ctx, account_id, _document([_OPEN, _CLOSE]))
    assert later.raw_transactions_created == 1

    db_session.expire_all()
    trades = (await db_session.execute(select(Trade).where(Trade.user_id == ctx.user_id))).scalars().all()
    assert [t.id for t in trades] == [trade_id]
    assert trades[0].journal == "protected journal"
    assert trades[0].closed_at is not None


# ─── Splits are insert-only (2.4) ────────────────────────────────────────────


async def test_conflicting_split_ratio_is_preserved_and_warned(client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _new_user(client)
    account_id = await ctx.account()
    await _import(db_session, ctx, account_id, _document([_OPEN], [{"type": "SPLIT", "symbol": "XYZ", "date": "2026-05-01", "ratio": "0.1"}]))
    conflicting = _document([_CLOSE], [{"type": "SPLIT", "symbol": "XYZ", "date": "2026-05-01", "ratio": "0.2"}])

    preview = await ctx.post_file("preview", account_id, "c.json", conflicting)
    assert preview.json()["data"]["conflicting_splits"] == 1
    result = await _import(db_session, ctx, account_id, conflicting)
    assert any("split" in warning for warning in result.warnings)
    db_session.expire_all()
    ratios = (await db_session.execute(select(CorporateAction.ratio).where(CorporateAction.user_id == ctx.user_id))).scalars().all()
    assert [str(r.normalize()) for r in ratios] == ["0.1"]


async def test_service_rejects_invalid_generic_file_before_any_write(client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _new_user(client)
    account_id = await ctx.account()
    with pytest.raises(GenericFormatValidationError):
        await _import(db_session, ctx, account_id, _document([_OPEN, _OPEN]))
    await db_session.rollback()
    assert await _counts(db_session, ctx.user_id, account_id) == {"raw": 0, "executions": 0, "trades": 0, "splits": 0, "properties": 0}
