import re

with open("backend/app/services/trade_service.py", "r") as f:
    content = f.read()

new_method = """    async def create_trade(self, data: TradeCreate) -> TradeRead:
        \"\"\"Create a new trade record.

        Args:
            data: Validated creation payload.

        Returns:
            A :class:`TradeRead` DTO representing the created trade.
        \"\"\"
        trade: Trade = await self._repo.create(data)

        from app.models.logical_execution import ExecutionStatus
        from app.repositories.execution import ExecutionRepository
        
        exec_repo = ExecutionRepository(self._repo.session)
        await exec_repo.create(
            user_id=trade.user_id,
            account_id=trade.account_id,
            symbol=trade.symbol,
            asset_class=trade.asset_class,
            direction=trade.direction,
            quantity=trade.quantity,
            price=trade.entry_price,
            commission=trade.commission,
            executed_at=trade.opened_at,
            multiplier=trade.multiplier,
            currency=trade.currency,
            status=ExecutionStatus.MANUAL,
            trade_id=trade.id,
        )
        
        await self._repo.session.commit()
        trade_reloaded = await self._repo.get_by_id(trade.id)

        return TradeRead.model_validate(trade_reloaded)"""

content = re.sub(
    r'    async def create_trade\(self, data: TradeCreate\) -> TradeRead:\n(.*?)(?=    async def get_trade)',
    new_method + '\n\n',
    content,
    flags=re.DOTALL
)

with open("backend/app/services/trade_service.py", "w") as f:
    f.write(content)
