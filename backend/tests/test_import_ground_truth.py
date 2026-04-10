"""Integration tests for historical XML import vs ground-truth aggregation.

These tests validate the isolated raw-layer architecture end-to-end by:

1. Importing the historical IBKR XML files through the public API.
2. Computing yearly ground-truth PnL via ``flex_query_aggregation.py``.
3. Verifying DB yearly totals exactly match the ground truth.
"""

import uuid
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cash_transaction import CashTransaction, CashTransactionType
from app.models.trade import Trade
from tests.integration.ground_truth_aggregator import aggregate_files_yearly

_REGISTER_URL = "/api/v1/auth/register"
_TOKEN_URL = "/api/v1/auth/token"
_ACCOUNTS_URL = "/api/v1/accounts"
_IMPORT_URL = "/api/v1/imports/upload"


def _historical_xml_paths() -> list[Path]:
    """Return all historical TraderJournal XML files in import order."""
    base = Path(__file__).resolve().parents[1]
    legacy_split_files = [
        base / "TraderJournal_2023.xml",
        base / "TraderJournal_2024.xml",
        base / "TraderJournal_2025.xml",
        base / "TraderJournal_Q1_2026.xml",
    ]
    if all(path.exists() for path in legacy_split_files):
        return legacy_split_files

    repo_root = base.parent
    fixture_candidates = [
        base / "tests" / "test_data" / "ibkr" / "TraderJournal_anonymized_combined.xml",
        repo_root
        / "tests"
        / "test_data"
        / "ibkr"
        / "TraderJournal_anonymized_combined.xml",
    ]
    for candidate in fixture_candidates:
        if candidate.exists():
            return [candidate]

    return [fixture_candidates[0]]


async def _register_and_login(client: AsyncClient) -> tuple[str, uuid.UUID]:
    """Create a test user and return bearer token + user ID."""
    suffix = uuid.uuid4().hex[:8]
    username = f"gt_{suffix}"
    email = f"gt_{suffix}@example.com"
    password = "GroundTruth@99"

    reg = await client.post(
        _REGISTER_URL,
        json={"username": username, "email": email, "password": password},
    )
    assert reg.status_code == 201, reg.text
    user_id = uuid.UUID(reg.json()["data"]["id"])

    login = await client.post(
        _TOKEN_URL,
        data={"username": username, "password": password},
    )
    assert login.status_code == 200, login.text
    token = str(login.json()["access_token"])
    return token, user_id


async def _create_account(client: AsyncClient, token: str) -> uuid.UUID:
    """Create an IBKR account for imports and return account UUID."""
    resp = await client.post(
        _ACCOUNTS_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "IBKR Ground Truth", "type": "ibkr", "currency": "USD"},
    )
    assert resp.status_code == 201, resp.text
    return uuid.UUID(resp.json()["data"]["id"])


async def _import_xml_files(
    client: AsyncClient,
    token: str,
    account_id: uuid.UUID,
    xml_paths: list[Path],
) -> None:
    """Import all XML files via the public /imports/upload endpoint."""
    headers = {"Authorization": f"Bearer {token}"}

    for xml_path in xml_paths:
        assert xml_path.exists(), f"Missing historical XML file: {xml_path}"
        with xml_path.open("rb") as f:
            files = {"file": (xml_path.name, f, "application/xml")}
            data = {
                "broker": "ibkr",
                "account_id": str(account_id),
            }
            resp = await client.post(
                _IMPORT_URL, headers=headers, data=data, files=files
            )
            assert resp.status_code == 200, (
                f"Import failed for {xml_path.name}: {resp.status_code} {resp.text}"
            )


async def _db_yearly_totals(
    db_session: AsyncSession,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
) -> dict[int, dict]:
    """Compute yearly DB totals: closed trade net PnL + fee cash transactions."""
    totals: dict[int, dict] = defaultdict(lambda: {"pnl": Decimal("0"), "trades": 0})

    # Closed trades: prefer net_pnl, fallback to pnl.
    trade_rows = await db_session.execute(
        select(Trade.closed_at, Trade.net_pnl, Trade.pnl).where(
            Trade.user_id == user_id,
            Trade.account_id == account_id,
            Trade.closed_at.is_not(None),
        )
    )
    for closed_at, net_pnl, pnl in trade_rows.all():
        assert isinstance(closed_at, datetime)
        value = net_pnl if net_pnl is not None else pnl
        if value is not None:
            totals[closed_at.year]["pnl"] += value
            totals[closed_at.year]["trades"] += 1

    # Fee cash flows (TransactionTax + CASH-trade commissions are persisted as FEE).
    fee_rows = await db_session.execute(
        select(CashTransaction.date, CashTransaction.amount).where(
            CashTransaction.account_id == account_id,
            CashTransaction.type == CashTransactionType.FEE,
        )
    )
    for date_value, amount in fee_rows.all():
        totals[date_value.year]["pnl"] += amount

    return dict(sorted(totals.items(), key=lambda kv: kv[0]))


@pytest.mark.integration
async def test_historical_xml_import_matches_ground_truth(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """DB yearly PnL must exactly match standalone ground-truth output."""
    xml_paths = _historical_xml_paths()
    token, user_id = await _register_and_login(client)
    account_id = await _create_account(client, token)

    await _import_xml_files(client, token, account_id, xml_paths)

    db_yearly = await _db_yearly_totals(db_session, user_id, account_id)
    gt_yearly = aggregate_files_yearly(xml_paths)

    assert db_yearly == gt_yearly
