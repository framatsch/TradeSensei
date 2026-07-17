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

"""Integration tests for COMBO import through the public upload API."""

from __future__ import annotations

import uuid
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.logical_execution import LogicalExecution
from app.models.trade import Trade
from tests.integration.ground_truth_aggregator import aggregate_files_yearly

_REGISTER_URL = "/api/v1/auth/register"
_TOKEN_URL = "/api/v1/auth/token"
_PORTFOLIOS_URL = "/api/v1/portfolios"
_FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "test_data" / "ibkr" / "combo_positions.xml"


async def _register_and_login(client: AsyncClient) -> tuple[str, uuid.UUID]:
    suffix = uuid.uuid4().hex[:8]
    username = f"combo_{suffix}"
    email = f"combo_{suffix}@example.com"
    password = "ComboImport@99"

    reg = await client.post(
        _REGISTER_URL,
        json={"username": username, "email": email, "password": password},
    )
    assert reg.status_code == 201, reg.text
    user_id = uuid.UUID(reg.json()["data"]["id"])

    login = await client.post(_TOKEN_URL, data={"username": email, "password": password})
    assert login.status_code == 200, login.text
    return str(login.json()["access_token"]), user_id


async def _create_account(client: AsyncClient, token: str) -> tuple[uuid.UUID, uuid.UUID]:
    portfolio_resp = await client.post(
        _PORTFOLIOS_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Combo Portfolio", "base_currency": "USD"},
    )
    assert portfolio_resp.status_code == 201, portfolio_resp.text
    portfolio_id = uuid.UUID(portfolio_resp.json()["data"]["id"])

    account_resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "IBKR Combo", "type": "ibkr", "currency": "USD"},
    )
    assert account_resp.status_code == 201, account_resp.text
    account_id = uuid.UUID(account_resp.json()["data"]["id"])
    return portfolio_id, account_id


def _filtered_fixture_xml(order_ids: set[str]) -> bytes:
    root = ET.fromstring(_FIXTURE.read_text(encoding="utf-8"))
    trades_parent = root.find(".//Trades")
    if trades_parent is None:
        raise AssertionError("combo fixture does not contain <Trades> section")

    for trade_node in list(trades_parent.findall("Trade")):
        order_id = trade_node.attrib.get("brokerageOrderID")
        if order_id not in order_ids:
            trades_parent.remove(trade_node)

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


@pytest.mark.integration
async def test_import_combo_positions_file_creates_combo_trades_and_binds_legs(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    token, user_id = await _register_and_login(client)
    portfolio_id, account_id = await _create_account(client, token)

    with _FIXTURE.open("rb") as fixture_handle:
        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/imports/upload",
            headers={"Authorization": f"Bearer {token}"},
            data={"broker": "ibkr", "account_id": str(account_id)},
            files={"file": (_FIXTURE.name, fixture_handle, "application/xml")},
        )

    assert response.status_code == 200, response.text

    trades_result = await db_session.execute(
        select(Trade)
        .where(
            Trade.user_id == user_id,
            Trade.account_id == account_id,
        )
        .order_by(Trade.symbol.asc(), Trade.opened_at.asc())
    )
    trades = list(trades_result.scalars().all())

    assert len(trades) == 4
    assert all(trade.is_combo for trade in trades)

    qqq = next((trade for trade in trades if trade.symbol == "QQQ"), None)
    assert qqq is not None
    assert qqq.closed_at is not None
    assert qqq.pnl == Decimal("77")

    legs_result = await db_session.execute(
        select(LogicalExecution).where(LogicalExecution.trade_id.in_([trade.id for trade in trades]))
    )
    legs = list(legs_result.scalars().all())

    assert len(legs) == 16
    assert all(leg.trade_id is not None for leg in legs)


@pytest.mark.integration
async def test_combo_close_in_second_import_updates_existing_open_combo(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    token, user_id = await _register_and_login(client)
    portfolio_id, account_id = await _create_account(client, token)

    open_only_xml = _filtered_fixture_xml({"combo-qqq-open-1"})
    close_only_xml = _filtered_fixture_xml({"combo-qqq-close-1"})

    open_resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/imports/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"broker": "ibkr", "account_id": str(account_id)},
        files={"file": ("combo_open_only.xml", open_only_xml, "application/xml")},
    )
    assert open_resp.status_code == 200, open_resp.text

    open_trade_result = await db_session.execute(
        select(Trade).where(
            Trade.user_id == user_id,
            Trade.account_id == account_id,
            Trade.is_combo.is_(True),
            Trade.symbol == "QQQ",
        )
    )
    open_trade = open_trade_result.scalar_one()
    open_trade_id = open_trade.id
    assert open_trade.closed_at is None

    close_resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/imports/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"broker": "ibkr", "account_id": str(account_id)},
        files={"file": ("combo_close_only.xml", close_only_xml, "application/xml")},
    )
    assert close_resp.status_code == 200, close_resp.text

    qqq_trades_result = await db_session.execute(
        select(Trade)
        .where(
            Trade.user_id == user_id,
            Trade.account_id == account_id,
            Trade.is_combo.is_(True),
            Trade.symbol == "QQQ",
        )
        .order_by(Trade.opened_at.asc())
    )
    qqq_trades = list(qqq_trades_result.scalars().all())

    assert len(qqq_trades) == 1
    assert qqq_trades[0].id == open_trade_id
    assert qqq_trades[0].closed_at is not None

    qqq_legs_result = await db_session.execute(
        select(LogicalExecution).where(LogicalExecution.trade_id == open_trade_id)
    )
    qqq_legs = list(qqq_legs_result.scalars().all())
    assert len(qqq_legs) == 4
    assert sum(1 for leg in qqq_legs if leg.open_close == "O") == 2
    assert sum(1 for leg in qqq_legs if leg.open_close == "C") == 2


@pytest.mark.integration
async def test_combo_import_db_net_pnl_matches_combo_agnostic_ground_truth(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    token, user_id = await _register_and_login(client)
    portfolio_id, account_id = await _create_account(client, token)

    with _FIXTURE.open("rb") as fixture_handle:
        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/imports/upload",
            headers={"Authorization": f"Bearer {token}"},
            data={"broker": "ibkr", "account_id": str(account_id)},
            files={"file": (_FIXTURE.name, fixture_handle, "application/xml")},
        )
    assert response.status_code == 200, response.text

    db_trades_result = await db_session.execute(
        select(Trade).where(
            Trade.user_id == user_id,
            Trade.account_id == account_id,
            Trade.closed_at.is_not(None),
        )
    )
    db_trades = list(db_trades_result.scalars().all())

    db_yearly_net: dict[int, Decimal] = {}
    for trade in db_trades:
        if trade.closed_at is None:
            continue
        db_yearly_net.setdefault(trade.closed_at.year, Decimal("0"))
        db_yearly_net[trade.closed_at.year] += trade.net_pnl or Decimal("0")

    gt_yearly = aggregate_files_yearly([_FIXTURE])

    assert set(db_yearly_net.keys()) == set(gt_yearly.keys())
    for year, db_value in db_yearly_net.items():
        assert db_value.quantize(Decimal("0.00000001")) == gt_yearly[year]["pnl"]
