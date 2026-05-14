import re

with open("backend/app/repositories/trade_repository.py", "r") as f:
    content = f.read()

method = """
    async def update_modelbook_flag(self, session: AsyncSession, trade_id: UUID, is_modelbook: bool) -> Trade | None:
        trade = await self.get(session, trade_id)
        if trade:
            trade.is_modelbook = is_modelbook
            await session.commit()
            await session.refresh(trade)
        return trade
"""

content = content + method
with open("backend/app/repositories/trade_repository.py", "w") as f:
    f.write(content)
