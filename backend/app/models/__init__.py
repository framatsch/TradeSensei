"""Models package — SQLAlchemy ORM definitions.

Importing all models here ensures that Alembic's autogenerate can
discover every table when it inspects ``Base.metadata``.
"""

from app.models.account import Account as Account
from app.models.trade import Trade as Trade
from app.models.user import User as User
