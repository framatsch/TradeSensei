import asyncio
from app.core.database import SessionLocal
from sqlalchemy import select
from app.models.trade import Trade
from app.models.logical_execution import LogicalExecution
import json

async def main():
    async with SessionLocal() as session:
        result = await session.execute(
            select(Trade).where(Trade.symbol == 'ATOS')
        )
        trades = result.scalars().all()
        for t in trades:
            print(f"Trade ID: {t.id}")
            print(f"  Qty: {t.quantity}")
            print(f"  Entry Price: {t.entry_price}")
            print(f"  Exit Price: {t.exit_price}")
            
            execs = await session.execute(
                select(LogicalExecution).where(LogicalExecution.trade_id == t.id)
            )
            for ex in execs.scalars().all():
                print(f"    Exec: {ex.id}, origin: {ex.origin}, dir: {ex.direction}, qty: {ex.quantity}, price: {ex.price}")

asyncio.run(main())
