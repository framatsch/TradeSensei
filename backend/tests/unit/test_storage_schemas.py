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

"""Unit tests for schema presigned URL generation."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.schemas.daily_checkin import DailyCheckinRead
from app.schemas.playbook_attachment import PlaybookImageResponse
from app.schemas.trade import TradeRead


@pytest.fixture
def mock_storage_service():
    class MockStorageService:
        def generate_presigned_get_url(self, storage_ref: str, expires_in: int = 3600) -> str:
            if not storage_ref or "://" in storage_ref:
                return storage_ref
            bucket, key = storage_ref.split("/", 1)
            return f"https://s3.mock/{bucket}/{key}?signed=true&expires={expires_in}"
    return MockStorageService()

@pytest.mark.unit
def test_trade_read_schema_generates_presigned_urls(mock_storage_service):
    trade_data = {
        "id": uuid4(),
        "portfolio_id": uuid4(),
        "account_id": uuid4(),
        "status": "OPEN",
        "side": "LONG",
        "direction": "LONG",
        "symbol": "AAPL",
        "asset_class": "EQUITY",
        "quantity": Decimal("100"),
        "entry_price": Decimal("150.0"),
        "exit_price": None,
        "stop_loss": None,
        "take_profit": None,
        "opened_at": datetime.now(UTC),
        "closed_at": None,
        "pnl": None,
        "commission": Decimal("0"),
        "journal": "",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "image_urls": ["test-bucket/trades/user1/image1.png", "other-bucket/trades/image2.png"],
        "playbook_id": None,
        "is_combo": False,
        "strategy": None,
        "legs": []
    }
    
    context = {"storage_service": mock_storage_service}
    validated = TradeRead.model_validate(trade_data, context=context)
    
    assert validated.image_urls == [
        "https://s3.mock/test-bucket/trades/user1/image1.png?signed=true&expires=3600",
        "https://s3.mock/other-bucket/trades/image2.png?signed=true&expires=3600"
    ]

@pytest.mark.unit
def test_daily_checkin_read_schema_generates_presigned_urls(mock_storage_service):
    checkin_data = {
        "id": uuid4(),
        "portfolio_id": uuid4(),
        "user_id": uuid4(),
        "date": datetime.now(UTC).date(),
        "market_phase": "BULL",
        "notes": "",
        "news_links": [],
        "custom_metrics": {},
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "screenshot_urls": ["test-bucket/checkins/user1/sc1.png"]
    }
    
    context = {"storage_service": mock_storage_service}
    validated = DailyCheckinRead.model_validate(checkin_data, context=context)
    
    assert validated.screenshot_urls == [
        "https://s3.mock/test-bucket/checkins/user1/sc1.png?signed=true&expires=3600"
    ]

@pytest.mark.unit
def test_playbook_attachment_read_schema_generates_presigned_urls(mock_storage_service):
    attachment_data = {
        "id": uuid4(),
        "playbook_id": uuid4(),
        "filename": "rules.pdf",
        "content_type": "application/pdf",
        "storage_url": "test-bucket/playbooks/rules.pdf",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC)
    }
    
    context = {"storage_service": mock_storage_service}
    validated = PlaybookImageResponse.model_validate(attachment_data, context=context)
    
    assert validated.storage_url == "https://s3.mock/test-bucket/playbooks/rules.pdf?signed=true&expires=14400"
