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
