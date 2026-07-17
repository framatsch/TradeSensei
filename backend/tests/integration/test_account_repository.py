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
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.account_repository import AccountRepository
from app.schemas.account import AccountCreate

pytestmark = pytest.mark.asyncio

@pytest.mark.integration
async def test_account_repository_create_missing_portfolio(db_session: AsyncSession):
    repo = AccountRepository(db_session)
    user_id = uuid.uuid4()
    portfolio_id = uuid.uuid4()

    data = AccountCreate(
        name="Test Account",
        portfolio_id=portfolio_id,
        account_number="123",
        type="manual"
    )

    with pytest.raises(ValueError, match="Portfolio not found."):
        await repo.create(data=data, user_id=user_id)


@pytest.mark.integration
async def test_account_repository_get_metrics(db_session: AsyncSession):
    repo = AccountRepository(db_session)
    user_id = uuid.uuid4()
    account_id = uuid.uuid4()

    metrics = await repo.get_metrics(account_id=account_id, user_id=user_id)
    assert metrics is not None
