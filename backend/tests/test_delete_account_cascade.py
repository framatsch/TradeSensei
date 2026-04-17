import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade import AssetClass, Direction, Trade


async def _register_and_get_token(client: AsyncClient, email: str) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "username": email[:40], "password": "password123!"},
    )
    res = await client.post(
        "/api/v1/auth/token",
        data={"username": email[:40], "password": "password123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return res.json()["access_token"]

@pytest.mark.asyncio
async def test_delete_account_cascade(client: AsyncClient, db_session: AsyncSession) -> None:
    uid = str(uuid.uuid4())[:8]
    token = await _register_and_get_token(client, f"testcascade_{uid}@example.com")
    
    # 1. Create account
    res = await client.post(
        "/api/v1/accounts",
        json={"name": "Cascade Acc", "type": "manual", "currency": "USD"},
        headers={"Authorization": f"Bearer {token}"},
    )
    account_id = res.json()["data"]["id"]
    
    # 2. Insert a Trade referencing this account via db_session directly
    res_me = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    user_id = res_me.json()["data"]["id"]
    
    trade = Trade(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id),
        account_id=uuid.UUID(account_id),
        symbol="AAPL",
        direction=Direction.LONG,
        asset_class=AssetClass.EQUITY,
        quantity=Decimal("100"),
        entry_price=Decimal("150"),
        commission=Decimal("0"),
        opened_at=datetime.now(UTC)
    )
    db_session.add(trade)
    await db_session.flush()

    from app.models.broker_raw_transaction import BrokerRawTransaction
    from app.models.logical_execution import LogicalExecution
    
    raw = BrokerRawTransaction(
        id="user:123",
        user_id=uuid.UUID(user_id),
        account_id=uuid.UUID(account_id),
        broker_type="ibkr",
        symbol="AAPL",
        direction=Direction.LONG,
        quantity=Decimal("100"),
        price=Decimal("150"),
        commission=Decimal("0"),
        executed_at=datetime.now(UTC),
        asset_class=AssetClass.EQUITY,
        raw_data={"foo": "bar"}
    )
    db_session.add(raw)
    await db_session.flush()

    lexec = LogicalExecution(
        id=uuid.uuid4(),
        trade_id=trade.id,
        user_id=uuid.UUID(user_id),
        account_id=uuid.UUID(account_id),
        symbol="AAPL",
        direction=Direction.LONG,
        quantity=Decimal("100"),
        price=Decimal("150"),
        executed_at=datetime.now(UTC),
        asset_class=AssetClass.EQUITY,
        origin="imported",
    )
    # Add mapping!
    lexec.raw_transactions.append(raw)
    db_session.add(lexec)
    await db_session.flush()
    await db_session.commit()
    
    # Try delete again
    del_res = await client.delete(
        f"/api/v1/accounts/{account_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    print("Delete response:", del_res.status_code, del_res.text)
    assert del_res.status_code == 204
