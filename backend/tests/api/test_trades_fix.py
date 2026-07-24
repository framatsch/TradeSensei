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

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from app.schemas.trade import TradeRead
from app.models.trade import AssetClass, Direction

def get_mock_trade(portfolio_id, user_id, trade_id):
    return TradeRead(
        id=trade_id,
        account_id=None,
        portfolio_id=portfolio_id,
        symbol="AAPL",
        direction=Direction.LONG,
        asset_class=AssetClass.EQUITY,
        is_combo=False,
        quantity=Decimal("1"),
        entry_price=Decimal("100.0"),
        exit_price=None,
        stop_loss=None,
        take_profit=None,
        opened_at=datetime.now(timezone.utc),
        closed_at=None,
        pnl=None,
        net_pnl=None,
        commission=Decimal("0.0"),
        journal=None,
        user_rating=None,
        tradingview_link=None,
        image_urls=[],
        currency="USD",
        pnl_eur=None,
        net_pnl_eur=None,
        playbook_id=None,
        playbook_name=None,
        account_name=None,
        account_type=None,
        taxonomies=[],
        annotations=[],
        trade_notes=[],
        legs=[],
        is_manually_edited=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
