"""Integration tests for Schwab JSON import pipeline and API behavior."""

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import AccountType
from app.models.broker_raw_transaction import BrokerRawTransaction
from app.models.trade import Trade
from app.services.import_service import ImportService
from app.utils.parsers.aggregator import (
    aggregate_executions_fifo,
    logical_executions_to_trade_creates,
)
from app.utils.parsers.factory import BrokerType
from app.utils.parsers.ibkr_xml import IBKRXMLParser
from app.utils.parsers.schwab_json import SchwabJSONParser

_REGISTER_URL = "/api/v1/auth/register"
_TOKEN_URL = "/api/v1/auth/token"
_ACCOUNTS_URL = "/api/v1/accounts"
_UPLOAD_URL = "/api/v1/imports/upload"
_SCHWAB_JSON_URL = "/api/v1/imports/schwab-json"


def _fixture_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "tests"
        / "test_data"
        / "schwab"
        / "schwab_aggregation.json"
    )


def _load_fixture() -> list[dict[str, object]]:
    return json.loads(_fixture_path().read_text(encoding="utf-8"))


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


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
) -> uuid.UUID:
    resp = await client.post(
        _ACCOUNTS_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": f"{account_type.value.upper()} Import",
            "type": account_type.value,
            "currency": "USD",
        },
    )
    assert resp.status_code == 201, resp.text
    return uuid.UUID(resp.json()["data"]["id"])


@pytest.mark.integration
async def test_schwab_json_import_ground_truth(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    token, user_id = await _register_and_login(client)
    account_id = await _create_account(client, token, AccountType.SCHWAB)

    fixture_bytes = _fixture_path().read_bytes()
    payload = _load_fixture()
    expected_trade_rows = sum(1 for item in payload if item.get("type") == "TRADE")

    parser = SchwabJSONParser()
    expected_raw, _, _ = parser.parse_raw(fixture_bytes, "schwab_aggregation.json")
    expected_trades = aggregate_executions_fifo(
        logical_executions_to_trade_creates(expected_raw)
    )
    expected_closed = sum(1 for trade in expected_trades if trade.closed_at is not None)
    expected_leftovers = sum(1 for trade in expected_trades if trade.closed_at is None)

    service = ImportService(db_session)
    first = await service.import_file(
        content=fixture_bytes,
        filename="schwab_aggregation.json",
        broker=BrokerType.SCHWAB,
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
async def test_schwab_json_rest_endpoint(client: AsyncClient) -> None:
    token, _ = await _register_and_login(client)
    account_id = await _create_account(client, token, AccountType.SCHWAB)
    payload = _load_fixture()

    response = await client.post(
        _SCHWAB_JSON_URL,
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
    account_id = await _create_account(client, token, AccountType.IBKR)

    response = await client.post(
        _SCHWAB_JSON_URL,
        params={"account_id": str(account_id)},
        json=[],
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422, response.text
    assert (
        response.json()["detail"]
        == "Account type must be SCHWAB for this endpoint"
    )


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

    schwab_json = [
        {
            "activityId": "S1",
            "type": "TRADE",
            "status": "COMPLETED",
                "transactionDate": "2024-01-01T10:00:00.000Z",
                "transactionItem": {
                    "instrument": {"symbol": "AAPL", "assetType": "EQUITY"},
                    "instruction": "BUY",
                    "price": 100,
                    "amount": 10,
                },
            },
        {
            "activityId": "S2",
            "type": "TRADE",
            "status": "COMPLETED",
                "transactionDate": "2024-01-01T11:00:00.000Z",
                "transactionItem": {
                    "instrument": {"symbol": "AAPL", "assetType": "EQUITY"},
                    "instruction": "SELL",
                    "price": 110,
                    "amount": 10,
                },
            },
    ]

    ibkr_raw, _, _ = IBKRXMLParser().parse_raw(ibkr_xml, "ibkr.xml")
    schwab_raw, _, _ = SchwabJSONParser().parse_raw(
        json.dumps(schwab_json).encode("utf-8"),
        "schwab.json",
    )

    ibkr_trades = aggregate_executions_fifo(
        logical_executions_to_trade_creates(ibkr_raw)
    )
    schwab_trades = aggregate_executions_fifo(
        logical_executions_to_trade_creates(schwab_raw)
    )

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
    account_id = await _create_account(client, token, AccountType.SCHWAB)

    response = await client.post(
        _UPLOAD_URL,
        headers={"Authorization": f"Bearer {token}"},
        data={"account_id": str(account_id)},
        files={"file": ("schwab.csv", b"Date,Action\n", "text/csv")},
    )
    assert response.status_code == 422, response.text
    assert response.json()["detail"] == (
        "Schwab accounts require JSON format (.json). "
        "CSV import is no longer supported."
    )


@pytest.mark.integration
async def test_manual_account_upload_rejected(client: AsyncClient) -> None:
    token, _ = await _register_and_login(client)
    account_id = await _create_account(client, token, AccountType.MANUAL)

    response = await client.post(
        _UPLOAD_URL,
        headers={"Authorization": f"Bearer {token}"},
        data={"account_id": str(account_id)},
        files={"file": ("anything.json", b"[]", "application/json")},
    )
    assert response.status_code == 422, response.text
    assert (
        response.json()["detail"]
        == "File import is not supported for manual accounts"
    )
