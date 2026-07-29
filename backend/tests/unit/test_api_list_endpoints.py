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

"""Unit tests for list endpoints."""
import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture(autouse=True)
def mock_storage(monkeypatch):
    def mock_generate(*args, **kwargs):
        return "https://s3.mock/bucket/key?signed=true"
    monkeypatch.setattr("app.services.storage_service.StorageService.generate_presigned_get_url", mock_generate)

from app.models.daily_checkin import DailyCheckin
from app.models.trade import Trade


@pytest.mark.asyncio
async def test_get_trades_list_presigned_urls(client: AsyncClient, db_session: AsyncSession, primary_user: dict):
    # Setup trade with image_url as key
    
    # Create portfolio
    import uuid

    from app.models.account import Account
    from app.models.portfolio import Portfolio
    portfolio_id = uuid.uuid4()
    portfolio = Portfolio(id=portfolio_id, user_id=primary_user["user_id"], name="Test Portfolio", base_currency="USD")
    db_session.add(portfolio)
    await db_session.flush()

    
    account_id = uuid.uuid4()
    account = Account(id=account_id, portfolio_id=portfolio_id, user_id=primary_user["user_id"], name="Test Account")
    db_session.add(account)
    await db_session.flush()

    
    trade = Trade(
        
        account_id=account_id,
            user_id=primary_user["user_id"],
            position_id=uuid.uuid4(),
        
        
        direction="LONG",
        symbol="TEST",
        asset_class="EQUITY",
        quantity=10,
        entry_price=100,
        opened_at=datetime.datetime.now(datetime.UTC),
        commission=0,
        image_urls=["test-bucket/trades/test.png"],
        is_combo=False,
        
    )
    db_session.add(trade)
    await db_session.flush()
    
    response = await client.get(f"/api/v1/portfolios/{portfolio_id}/trades", headers=primary_user["headers"])
    assert response.status_code == 200, response.text
    data = response.json()["data"]["items"]
    assert len(data) > 0
    trade_data = next(t for t in data if t["id"] == str(trade.id))
    assert len(trade_data["image_urls"]) == 1
    assert "signed=true" in trade_data["image_urls"][0] or "X-Amz-Signature" in trade_data["image_urls"][0]
    assert trade_data["image_urls"][0].startswith("http")

@pytest.mark.asyncio
async def test_get_checkins_list_presigned_urls(client: AsyncClient, db_session: AsyncSession, primary_user: dict):
    
    # Create portfolio
    import uuid

    from app.models.portfolio import Portfolio
    portfolio_id = uuid.uuid4()
    portfolio = Portfolio(id=portfolio_id, user_id=primary_user["user_id"], name="Test Portfolio", base_currency="USD")
    db_session.add(portfolio)
    await db_session.flush()

    user_id = primary_user["user_id"]
    
    checkin = DailyCheckin(
        
        user_id=user_id,
        date=datetime.datetime.now(datetime.UTC).date(),
        market_phase="BULL",
        notes="Test notes",
        screenshot_urls=["test-bucket/checkins/test.png"]
    )
    db_session.add(checkin)
    await db_session.flush()
    
    response = await client.get("/api/v1/checkins", headers=primary_user["headers"])
    assert response.status_code == 200, response.text
    data = response.json()["data"]["items"]
    assert len(data) > 0
    checkin_data = next(c for c in data if c["id"] == str(checkin.id))
    assert len(checkin_data["screenshot_urls"]) == 1
    assert "signed=true" in checkin_data["screenshot_urls"][0] or "X-Amz-Signature" in checkin_data["screenshot_urls"][0]
    assert checkin_data["screenshot_urls"][0].startswith("http")
