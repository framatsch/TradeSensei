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

"""Models package — SQLAlchemy ORM definitions.

Importing all models here ensures that Alembic's autogenerate can
discover every table when it inspects ``Base.metadata``.
"""

from app.models.account import Account as Account
from app.models.account_property import AccountProperty as AccountProperty
from app.models.annotation_definition import AnnotationDefinition as AnnotationDefinition
from app.models.broker_raw_transaction import (
    BrokerRawTransaction as BrokerRawTransaction,
)
from app.models.checkin_annotation import CheckinAnnotation as CheckinAnnotation
from app.models.checkin_taxonomy import CheckinTaxonomy as CheckinTaxonomy
from app.models.corporate_action import CorporateAction as CorporateAction
from app.models.daily_checkin import DailyCheckin as DailyCheckin
from app.models.fx_rate import FxRate as FxRate
from app.models.logical_execution import (
    EXECUTION_ORIGIN_IMPORTED as EXECUTION_ORIGIN_IMPORTED,
)
from app.models.logical_execution import (
    EXECUTION_ORIGIN_MANUAL as EXECUTION_ORIGIN_MANUAL,
)
from app.models.logical_execution import (
    EXECUTION_ORIGIN_MERGED as EXECUTION_ORIGIN_MERGED,
)
from app.models.logical_execution import (
    EXECUTION_ORIGIN_SPLIT as EXECUTION_ORIGIN_SPLIT,
)
from app.models.logical_execution import LogicalExecution as LogicalExecution
from app.models.market_index import MarketIndexDefinition as MarketIndexDefinition
from app.models.ohlc_price import OhlcPrice as OhlcPrice
from app.models.pat import PersonalAccessToken as PersonalAccessToken
from app.models.playbook import Playbook as Playbook
from app.models.playbook_attachment import PlaybookAttachment as PlaybookAttachment
from app.models.playbook_link import PlaybookLink as PlaybookLink
from app.models.playbook_taxonomy import PlaybookTaxonomy as PlaybookTaxonomy
from app.models.portfolio import Portfolio as Portfolio
from app.models.saved_checkin_filter import SavedCheckinFilter as SavedCheckinFilter
from app.models.saved_dashboard_view import SavedDashboardView as SavedDashboardView
from app.models.saved_trade_filter import FilterScope as FilterScope
from app.models.saved_trade_filter import SavedTradeFilter as SavedTradeFilter
from app.models.taxonomy import Taxonomy as Taxonomy
from app.models.trade import Trade as Trade
from app.models.trade_annotation import TradeAnnotation as TradeAnnotation
from app.models.trade_note import TradeNote as TradeNote
from app.models.trade_taxonomy import TradeTaxonomy as TradeTaxonomy
from app.models.transaction_execution_mapping import (
    TransactionExecutionMapping as TransactionExecutionMapping,
)
from app.models.used_ott import UsedOtt as UsedOtt
from app.models.user import User as User
from app.models.user_setting import UserSetting as UserSetting
