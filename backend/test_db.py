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

import asyncio

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.logical_execution import LogicalExecution


async def run():
    async with async_session_factory() as s:
        stmt = select(LogicalExecution).where(LogicalExecution.symbol == 'VST').order_by(LogicalExecution.executed_at)
        result = await s.execute(stmt)
        for e in result.scalars().all():
            print(f"{e.executed_at} {e.quantity} {e.price} mixed={e.is_mixed_execution}")

asyncio.run(run())
