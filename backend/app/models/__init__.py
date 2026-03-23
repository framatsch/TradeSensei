"""Models package — SQLAlchemy ORM definitions.

Importing all models here ensures that Alembic's autogenerate can
discover every table when it inspects ``Base.metadata``.
"""

from app.models.account import Account as Account
from app.models.account_property import AccountProperty as AccountProperty
from app.models.cash_transaction import CashTransaction as CashTransaction
from app.models.corporate_action import CorporateAction as CorporateAction
from app.models.fx_rate import FxRate as FxRate
from app.models.playbook import Playbook as Playbook
from app.models.tag import Tag as Tag
from app.models.trade import Trade as Trade
from app.models.trade_note import TradeNote as TradeNote
from app.models.trade_tag import TradeTag as TradeTag
from app.models.user import User as User
from app.models.user_setting import UserSetting as UserSetting
