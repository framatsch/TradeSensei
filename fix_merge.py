import sys

with open("backend/app/services/trade_service.py", "r") as f:
    content = f.read()

# I will replace the generated stub
import re
new_code = """
    async def merge_trades(self, trade_ids: list[uuid.UUID], user_id: uuid.UUID) -> TradeRead:
        \"\"\"Merge multiple trades into a single trade.
        
        Args:
            trade_ids: The UUIDs of the trades to merge.
            user_id: The authenticated user's ID.
            
        Returns:
            The surviving TradeRead.
            
        Raises:
            HTTPException: If trades do not belong to the user, mismatch in symbol/account/asset_class.
        \"\"\"
        trades = []
        for tid in set(trade_ids):
            t = await self._repo.get_by_id(tid)
            if not t or t.user_id != user_id:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail=f"Trade {tid} not found or not owned.")
            trades.append(t)
            
        if len(trades) < 2:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Must provide at least two unique trades to merge.")
            
        ref_trade = trades[0]
        for t in trades[1:]:
            if t.symbol != ref_trade.symbol or t.account_id != ref_trade.account_id or t.asset_class != ref_trade.asset_class:
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail="Trades must have the same symbol, account, and asset class to be merged.")
                
        # Sort trades by opened_at
        trades.sort(key=lambda t: t.opened_at)
        survivor = trades[0]
        non_survivors = trades[1:]
        
        from app.repositories.execution import ExecutionRepository
        exec_repo = ExecutionRepository(self._repo.session)
        
        # Merge logic
        for t in non_survivors:
            # Reassign logical executions
            executions = await exec_repo.list_by_trade_id(t.id)
            for ex in executions:
                ex.trade_id = survivor.id
                await self._repo.session.flush()
                
            # Append notes
            if t.notes:
                if survivor.notes:
                    survivor.notes += f"\\n\\n[Merged from {t.id}]:\\n{t.notes}"
                else:
                    survivor.notes = t.notes
                    
            # Move tags
            for tag in t.tags:
                if tag not in survivor.tags:
                    survivor.tags.append(tag)
                    
            # Delete empty trades
            await self._repo.delete(t)
            
        # Re-aggregate survivor
        await self._re_aggregate_trade(survivor.id)
        await self._repo.session.commit()
        
        # Reload survivor
        survivor_reloaded = await self._repo.get_by_id(survivor.id)
        from app.schemas.trade import TradeRead
        return TradeRead.model_validate(survivor_reloaded)
"""

content = re.sub(r'    async def merge_trades.*?return TradeRead\.model_validate\(survivor\)\n', new_code, content, flags=re.DOTALL)

with open("backend/app/services/trade_service.py", "w") as f:
    f.write(content)
