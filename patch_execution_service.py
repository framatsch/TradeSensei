import re

with open("backend/app/services/execution.py", "r") as f:
    content = f.read()

new_method = """    async def _re_aggregate_trade(
        self, trade_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        \"\"\"Re-aggregate a trade's values from its logical executions using VWAP logic.
        
        Args:
            trade_id: Target trade ID to re-aggregate.
            user_id: For permissions check.
        \"\"\"
        trade = await self.trade_repo.get_by_id(trade_id)
        if not trade or trade.user_id != user_id:
            return

        executions = await self.execution_repo.list_by_trade_id(trade_id)
        if not executions:
            return

        from decimal import Decimal
        from app.models.trade import Direction

        # Determine if trade is long or short
        # For simplicity, we assume trade.direction doesn't change, or we infer it
        # from the first execution. Let's infer from the first execution if possible,
        # but trade.direction is fine.
        is_long = trade.direction == Direction.LONG

        entry_qty = Decimal(0)
        entry_cost = Decimal(0)
        exit_qty = Decimal(0)
        exit_cost = Decimal(0)
        total_commission = Decimal(0)
        
        first_executed_at = executions[0].executed_at
        last_executed_at = executions[0].executed_at

        for ex in executions:
            total_commission += ex.commission
            if ex.executed_at < first_executed_at:
                first_executed_at = ex.executed_at
            if ex.executed_at > last_executed_at:
                last_executed_at = ex.executed_at

            if (is_long and ex.direction == Direction.LONG) or (not is_long and ex.direction == Direction.SHORT):
                # Entry execution
                entry_qty += ex.quantity
                entry_cost += ex.quantity * ex.price
            else:
                # Exit execution
                exit_qty += ex.quantity
                exit_cost += ex.quantity * ex.price

        trade.quantity = entry_qty
        trade.entry_price = entry_cost / entry_qty if entry_qty > 0 else Decimal(0)
        trade.exit_price = exit_cost / exit_qty if exit_qty > 0 else None
        trade.commission = total_commission
        trade.opened_at = first_executed_at
        
        if exit_qty >= entry_qty and entry_qty > 0:
            trade.closed_at = last_executed_at
        else:
            trade.closed_at = None

        if exit_qty > 0:
            multiplier = Decimal(trade.multiplier)
            if is_long:
                trade.pnl = (trade.exit_price - trade.entry_price) * exit_qty * multiplier
            else:
                trade.pnl = (trade.entry_price - trade.exit_price) * exit_qty * multiplier
                
            trade.net_pnl = trade.pnl - total_commission
        else:
            trade.pnl = None
            trade.net_pnl = None

        if entry_qty == exit_qty:
            trade.has_conflict = False

        trade.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
"""

content = re.sub(
    r'    async def _re_aggregate_trade\(\n        self, trade_id: uuid.UUID, user_id: uuid.UUID\n    \) -> None:.*?(?=\Z)',
    new_method,
    content,
    flags=re.DOTALL
)

with open("backend/app/services/execution.py", "w") as f:
    f.write(content)
