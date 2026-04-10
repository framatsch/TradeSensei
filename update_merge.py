import re
import sys

with open("backend/app/services/trade_service.py", "r") as f:
    content = f.read()

stub = """
    async def _re_aggregate_trade(self, trade_id: uuid.UUID) -> None:
        pass
"""

if "_re_aggregate_trade" not in content:
    content = content.replace("class TradeService:", "class TradeService:\n" + stub)

with open("backend/app/services/trade_service.py", "w") as f:
    f.write(content)
