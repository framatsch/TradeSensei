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
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.pat_repository import PersonalAccessTokenRepository
from app.models.user import User

pytestmark = pytest.mark.asyncio

@pytest.mark.integration
async def test_pat_repository_mark_used(db_session: AsyncSession):
    repo = PersonalAccessTokenRepository(db_session)
    
    # Needs a real user in the DB for the foreign key constraint
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        username="testuser",
        email="pat_test@example.com",
        hashed_password="hash",
    )
    db_session.add(user)
    await db_session.flush()

    token = await repo.create(
        user_id=user_id,
        name="Test PAT",
        token_hash="testhash",
        expires_at=None
    )
    
    used_time = datetime.now(timezone.utc)
    await repo.mark_used(token=token, used_at=used_time)
    
    # Assert it was updated
    assert token.last_used_at == used_time
