import re
with open('backend/app/services/trade_service.py', 'r') as f:
    content = f.read()

method = """
    async def update_modelbook_flag(
        self,
        trade_id: uuid.UUID,
        is_modelbook: bool,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> TradeRead:
        trade = await self.repo.update_modelbook_flag(trade_id, is_modelbook, user_id)
        if not trade:
            raise TradeNotFoundError()
        return TradeRead.model_validate(trade)
"""

if "update_modelbook_flag" not in content:
    content += method
    with open('backend/app/services/trade_service.py', 'w') as f:
        f.write(content)
