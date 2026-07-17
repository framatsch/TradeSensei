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

"""Integration tests for Schwab JSON import pipeline and API behavior."""

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import AccountType
from app.models.broker_raw_transaction import BrokerRawTransaction
from app.models.trade import Trade
from app.services.import_service import ImportService
from app.utils.parsers.aggregator import (
    ExecutionLike,
    aggregate_executions_fifo,
    logical_executions_to_trade_creates,
)
from app.utils.parsers.factory import BrokerType
from app.utils.parsers.ibkr_xml import IBKRXMLParser
from app.utils.parsers.schwab_json import SchwabJSONParser

_REGISTER_URL = "/api/v1/auth/register"
_TOKEN_URL = "/api/v1/auth/token"
_PORTFOLIOS_URL = "/api/v1/portfolios"


def _fixture_path() -> Path:
    return Path(__file__).resolve().parents[2] / "tests" / "test_data" / "schwab" / "schwab_aggregation.json"


def _short_roundtrip_fixture_path() -> Path:
    return Path(__file__).resolve().parents[2] / "tests" / "test_data" / "schwab" / "schwab_short_roundtrip.json"


def _load_fixture() -> dict[str, object]:
    payload = cast(dict[str, object], json.loads(_fixture_path().read_text(encoding="utf-8")))
    assert isinstance(payload, dict)
    return payload


def _fixture_trade_count(payload: dict[str, object]) -> int:
    accounts = payload.get("accounts")
    if not isinstance(accounts, list):
        return 0
    count = 0
    for account in accounts:
        if not isinstance(account, dict):
            continue
        transactions = account.get("transactions")
        if not isinstance(transactions, list):
            continue
        count += sum(1 for item in transactions if isinstance(item, dict) and item.get("type") == "TRADE")
    return count


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _make_multi_account_fixture() -> dict[str, object]:
    base = _load_fixture()
    accounts = base.get("accounts")
    assert isinstance(accounts, list) and accounts and isinstance(accounts[0], dict)
    first = accounts[0]
    second = json.loads(json.dumps(first))
    first["accountNumber"] = "45302130"
    second["accountNumber"] = "99887766"
    second["accountHash"] = "test-account-hash-99887766"
    base["accounts"] = [first, second]
    return base


def _with_positions(payload: dict[str, object], include_positions: bool) -> dict[str, object]:
    cloned = cast(dict[str, object], json.loads(json.dumps(payload)))
    accounts = cloned.get("accounts")
    assert isinstance(accounts, list)
    for account in accounts:
        if not isinstance(account, dict):
            continue
        if include_positions:
            continue
        account["positions"] = []
    return cloned


async def _register_and_login(client: AsyncClient) -> tuple[str, uuid.UUID]:
    suffix = uuid.uuid4().hex[:8]
    username = f"schwab_{suffix}"
    email = f"schwab_{suffix}@example.com"
    password = "SchwabImport@99"

    reg = await client.post(
        _REGISTER_URL,
        json={"username": username, "email": email, "password": password},
    )
    assert reg.status_code == 201, reg.text
    user_id = uuid.UUID(reg.json()["data"]["id"])

    login = await client.post(
        _TOKEN_URL,
        data={"username": email, "password": password},
    )
    assert login.status_code == 200, login.text
    return str(login.json()["access_token"]), user_id


async def _create_account(
    client: AsyncClient,
    token: str,
    account_type: AccountType,
    account_number: str | None = None,
) -> tuple[uuid.UUID, uuid.UUID]:
    portfolio_resp = await client.post(
        _PORTFOLIOS_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={"name": f"{account_type.value.upper()} Portfolio", "base_currency": "USD"},
    )
    assert portfolio_resp.status_code == 201, portfolio_resp.text
    portfolio_id = uuid.UUID(portfolio_resp.json()["data"]["id"])

    body: dict[str, object] = {
        "name": f"{account_type.value.upper()} Import",
        "type": account_type.value,
        "currency": "USD",
    }
    if account_number is not None:
        body["account_number"] = account_number

    resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        headers={"Authorization": f"Bearer {token}"},
        json=body,
    )
    assert resp.status_code == 201, resp.text
    return portfolio_id, uuid.UUID(resp.json()["data"]["id"])


@pytest.mark.integration
async def test_schwab_json_import_ground_truth(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    token, user_id = await _register_and_login(client)
    portfolio_id, account_id = await _create_account(client, token, AccountType.SCHWAB, account_number="45302130")

    fixture_bytes = _fixture_path().read_bytes()
    payload = _load_fixture()
    expected_trade_rows = _fixture_trade_count(payload)

    parser = SchwabJSONParser()
    expected_raw, _ = parser.parse_raw(fixture_bytes, "schwab_aggregation.json")
    expected_trades = aggregate_executions_fifo(logical_executions_to_trade_creates([cast(ExecutionLike, row) for row in expected_raw]))
    expected_closed = sum(1 for trade in expected_trades if trade.closed_at is not None)
    expected_leftovers = sum(1 for trade in expected_trades if trade.closed_at is None)

    service = ImportService(db_session)
    first = await service.import_file(
        content=fixture_bytes,
        filename="schwab_aggregation.json",
        broker=BrokerType.SCHWAB,
        portfolio_id=portfolio_id,
        account_id=account_id,
        user_id=user_id,
    )

    assert first.trades_parsed >= expected_closed
    assert first.trades_created >= expected_closed
    assert first.raw_transactions_created == expected_trade_rows

    brt_rows = await db_session.execute(
        select(BrokerRawTransaction).where(
            BrokerRawTransaction.user_id == user_id,
            BrokerRawTransaction.account_id == account_id,
        )
    )
    broker_raw = list(brt_rows.scalars().all())
    assert len(broker_raw) == expected_trade_rows

    trade_rows = await db_session.execute(
        select(Trade).where(
            Trade.user_id == user_id,
            Trade.account_id == account_id,
        )
    )
    trades = list(trade_rows.scalars().all())
    closed = [t for t in trades if t.closed_at is not None]
    open_lots = [t for t in trades if t.closed_at is None]
    assert len(closed) == expected_closed
    assert len(open_lots) == expected_leftovers

    second = await service.import_file(
        content=fixture_bytes,
        filename="schwab_aggregation.json",
        broker=BrokerType.SCHWAB,
        portfolio_id=portfolio_id,
        account_id=account_id,
        user_id=user_id,
    )
    assert second.raw_transactions_created == 0

    brt_rows_after = await db_session.execute(
        select(BrokerRawTransaction).where(
            BrokerRawTransaction.user_id == user_id,
            BrokerRawTransaction.account_id == account_id,
        )
    )
    broker_raw_after = list(brt_rows_after.scalars().all())
    assert len(broker_raw_after) == len(broker_raw)


@pytest.mark.integration
async def test_schwab_positions_are_ignored_for_import_ground_truth(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    token, user_id = await _register_and_login(client)
    portfolio_id, account_id = await _create_account(client, token, AccountType.SCHWAB, account_number="45302130")

    service = ImportService(db_session)
    payload = _load_fixture()

    with_positions = _with_positions(payload, include_positions=True)
    without_positions = _with_positions(payload, include_positions=False)

    first = await service.import_file(
        content=json.dumps(with_positions).encode("utf-8"),
        filename="schwab_aggregation.json",
        broker=BrokerType.SCHWAB,
        portfolio_id=portfolio_id,
        account_id=account_id,
        user_id=user_id,
    )
    assert first.raw_transactions_created == _fixture_trade_count(payload)

    second = await service.import_file(
        content=json.dumps(without_positions).encode("utf-8"),
        filename="schwab_aggregation_no_positions.json",
        broker=BrokerType.SCHWAB,
        portfolio_id=portfolio_id,
        account_id=account_id,
        user_id=user_id,
    )
    assert second.raw_transactions_created == 0


@pytest.mark.integration
async def test_schwab_json_rest_endpoint(client: AsyncClient) -> None:
    token, _ = await _register_and_login(client)
    portfolio_id, account_id = await _create_account(client, token, AccountType.SCHWAB, account_number="45302130")
    payload = _load_fixture()

    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/imports/schwab-json",
        params={"account_id": str(account_id)},
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["broker"] == "schwab"
    assert data["filename"] == "schwab_transactions.json"


@pytest.mark.integration
async def test_schwab_json_rest_endpoint_wrong_account_type(
    client: AsyncClient,
) -> None:
    token, _ = await _register_and_login(client)
    portfolio_id, account_id = await _create_account(client, token, AccountType.IBKR)

    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/imports/schwab-json",
        params={"account_id": str(account_id)},
        json={"accounts": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "Account type must be SCHWAB for this endpoint"


@pytest.mark.integration
def test_pipeline_parity_schwab_vs_ibkr() -> None:
    ibkr_xml = (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b"<FlexQueryResponse><FlexStatements><FlexStatement><Trades>"
        b'<Trade transactionID="1" assetCategory="STK" symbol="AAPL" '
        b'conid="265598" tradeDate="20240101" dateTime="20240101;100000" '
        b'quantity="10" tradePrice="100" ibCommission="0" currency="USD" />'
        b'<Trade transactionID="2" assetCategory="STK" symbol="AAPL" '
        b'conid="265598" tradeDate="20240101" dateTime="20240101;110000" '
        b'quantity="-10" tradePrice="110" ibCommission="0" '
        b'fifoPnlRealized="100" currency="USD" />'
        b"</Trades><CashTransactions /></FlexStatement></FlexStatements>"
        b"</FlexQueryResponse>"
    )

    schwab_json = {
        "fetchedAt": "2026-07-02T18:00:00Z",
        "dateRange": {
            "start": "2026-07-01T00:00:00.000Z",
            "end": "2026-07-02T23:59:59.000Z",
        },
        "accounts": [
            {
                "accountNumber": "45302130",
                "accountHash": "hash-1",
                "positions": [],
                "transactions": [
                    {
                        "activityId": "S1",
                        "type": "TRADE",
                        "status": "COMPLETED",
                        "time": "2026-07-02T10:00:00+0000",
                        "netAmount": -1000,
                        "transferItems": [
                            {
                                "instrument": {"symbol": "AAPL", "assetType": "EQUITY"},
                                "instruction": "BUY",
                                "price": 100,
                                "amount": 10,
                                "cost": -1000,
                                "positionEffect": "OPENING",
                            }
                        ],
                    },
                    {
                        "activityId": "S2",
                        "type": "TRADE",
                        "status": "COMPLETED",
                        "time": "2026-07-02T11:00:00+0000",
                        "netAmount": 1100,
                        "transferItems": [
                            {
                                "instrument": {"symbol": "AAPL", "assetType": "EQUITY"},
                                "instruction": "SELL",
                                "price": 110,
                                "amount": 10,
                                "cost": 1100,
                                "positionEffect": "CLOSING",
                            }
                        ],
                    },
                ],
            }
        ],
    }

    ibkr_raw, _ = IBKRXMLParser().parse_raw(ibkr_xml, "ibkr.xml")
    schwab_raw, _ = SchwabJSONParser().parse_raw(
        json.dumps(schwab_json).encode("utf-8"),
        "schwab.json",
    )

    ibkr_trades = aggregate_executions_fifo(logical_executions_to_trade_creates([cast(ExecutionLike, row) for row in ibkr_raw]))
    schwab_trades = aggregate_executions_fifo(logical_executions_to_trade_creates([cast(ExecutionLike, row) for row in schwab_raw]))

    ibkr_closed = [t for t in ibkr_trades if t.closed_at is not None]
    schwab_closed = [t for t in schwab_trades if t.closed_at is not None]
    assert len(ibkr_closed) == 1
    assert len(schwab_closed) == 1

    left = ibkr_closed[0]
    right = schwab_closed[0]
    assert left.symbol == right.symbol
    assert left.direction == right.direction
    assert left.quantity == right.quantity
    assert left.entry_price == right.entry_price
    assert left.exit_price == right.exit_price
    assert left.pnl == right.pnl


@pytest.mark.integration
async def test_schwab_csv_upload_rejected(client: AsyncClient) -> None:
    token, _ = await _register_and_login(client)
    portfolio_id, account_id = await _create_account(client, token, AccountType.SCHWAB)

    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/imports/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"account_id": str(account_id)},
        files={"file": ("schwab.csv", b"Date,Action\n", "text/csv")},
    )
    assert response.status_code == 422, response.text
    assert response.json()["detail"] == ("Schwab accounts require JSON format (.json). CSV import is no longer supported.")


@pytest.mark.integration
async def test_manual_account_upload_rejected(client: AsyncClient) -> None:
    token, _ = await _register_and_login(client)
    portfolio_id, account_id = await _create_account(client, token, AccountType.MANUAL)

    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/imports/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"account_id": str(account_id)},
        files={"file": ("anything.json", b"[]", "application/json")},
    )
    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "File import is not supported for manual accounts"


@pytest.mark.integration
async def test_schwab_account_number_match_imports(client: AsyncClient) -> None:
    token, _ = await _register_and_login(client)
    portfolio_id, account_id = await _create_account(client, token, AccountType.SCHWAB, account_number="45302130")
    payload = _load_fixture()

    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/imports/schwab-json",
        params={"account_id": str(account_id)},
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text


@pytest.mark.integration
async def test_schwab_account_number_mismatch_returns_422(client: AsyncClient) -> None:
    token, _ = await _register_and_login(client)
    portfolio_id, account_id = await _create_account(client, token, AccountType.SCHWAB, account_number="11112222")
    payload = _load_fixture()

    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/imports/schwab-json",
        params={"account_id": str(account_id)},
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert "configured account number '11112222'" in detail
    assert "45302130" in detail


@pytest.mark.integration
async def test_schwab_unset_account_number_single_account_persists_number(
    client: AsyncClient,
) -> None:
    token, _ = await _register_and_login(client)
    portfolio_id, account_id = await _create_account(client, token, AccountType.SCHWAB)
    payload = _load_fixture()

    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/imports/schwab-json",
        params={"account_id": str(account_id)},
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text

    account_response = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/accounts/{account_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert account_response.status_code == 200, account_response.text
    assert account_response.json()["data"]["account_number"] == "45302130"


@pytest.mark.integration
async def test_schwab_unset_account_number_multi_account_returns_422(client: AsyncClient) -> None:
    token, _ = await _register_and_login(client)
    portfolio_id, account_id = await _create_account(client, token, AccountType.SCHWAB)
    payload = _make_multi_account_fixture()

    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/imports/schwab-json",
        params={"account_id": str(account_id)},
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert "file is ambiguous" in detail
    assert "45302130" in detail
    assert "99887766" in detail


@pytest.mark.integration
async def test_schwab_short_roundtrip_lifecycle_matches_ground_truth(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    token, user_id = await _register_and_login(client)
    portfolio_id, account_id = await _create_account(
        client,
        token,
        AccountType.SCHWAB,
        account_number="45302130",
    )

    fixture_bytes = _short_roundtrip_fixture_path().read_bytes()

    parser = SchwabJSONParser()
    expected_raw, _ = parser.parse_raw(fixture_bytes, "schwab_short_roundtrip.json")
    expected_trades = aggregate_executions_fifo(
        logical_executions_to_trade_creates([cast(ExecutionLike, row) for row in expected_raw])
    )
    expected_closed = [trade for trade in expected_trades if trade.closed_at is not None]
    assert len(expected_closed) == 1
    expected = expected_closed[0]

    service = ImportService(db_session)
    imported = await service.import_file(
        content=fixture_bytes,
        filename="schwab_short_roundtrip.json",
        broker=BrokerType.SCHWAB,
        portfolio_id=portfolio_id,
        account_id=account_id,
        user_id=user_id,
    )
    assert imported.trades_created >= 1

    trade_rows = await db_session.execute(
        select(Trade).where(
            Trade.user_id == user_id,
            Trade.account_id == account_id,
            Trade.symbol == "TSHORT",
        )
    )
    trades = list(trade_rows.scalars().all())
    closed = [trade for trade in trades if trade.closed_at is not None]
    assert len(closed) == 1

    trade = closed[0]
    assert trade.direction.value == "SHORT"
    assert trade.opened_at == _parse_ts("2026-07-11T14:00:00+0000")
    assert trade.closed_at == _parse_ts("2026-07-12T14:00:00+0000")
    assert trade.entry_price == expected.entry_price
    assert trade.exit_price == expected.exit_price
    assert trade.pnl is not None and trade.pnl > Decimal("0")
    assert trade.pnl == expected.pnl
