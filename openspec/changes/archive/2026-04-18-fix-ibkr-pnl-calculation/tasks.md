## 1. Database Schema & Models

- [x] 1.1 Add `multiplier: Mapped[int]` (server_default="1", nullable=False) to the `LogicalExecution` model in `backend/app/models/logical_execution.py`
- [x] 1.2 Add `multiplier: Mapped[int]` (server_default="1", nullable=False) to the `Trade` model in `backend/app/models/trade.py`
- [x] 1.3 Add `multiplier: int = Field(default=1, ge=1)` to `TradeCreate`, `TradeUpdate`, and `TradeResponse` schemas in `backend/app/schemas/trade.py`
- [x] 1.4 Generate Alembic migration for adding `multiplier` columns and apply it (`alembic revision --autogenerate -m "Add multiplier to trade and logical execution"`)

## 2. API & Data Flow Updates

- [x] 2.1 Update `ExecutionLike` protocol in `backend/app/utils/parsers/aggregator.py` to include `multiplier: int`
- [x] 2.2 Update `logical_executions_to_trade_creates` bridge function to pass `multiplier` to `TradeCreate`
- [x] 2.3 Pass `multiplier=raw.multiplier` when creating a new `LogicalExecution` in `create_from_raw` inside `backend/app/services/logical_execution_service.py`
- [x] 2.4 Ensure the legacy `_parse_trade_element` in `backend/app/utils/parsers/ibkr_xml.py` assigns `multiplier` to the generated `TradeCreate` object

## 3. Aggregator PnL Logic Rewrite

- [x] 3.1 Strip out `fifoPnlRealized` distribution logic (`exec_pnl_remaining`, `matched_pnl = (exec_pnl_remaining * match_qty) / exec_qty_remaining`) from `aggregate_executions_fifo`
- [x] 3.2 Implement exact mathematical calculation for `matched_pnl` during a regular matching step: `(Exit Price - Entry Price) * match_qty * open_lot.multiplier` (adjusted for long/short direction)
- [x] 3.3 Ensure `matched_net_pnl` deducts the proportional commissions (`matched_pnl - (lot_comm + exec_comm)`)
- [x] 3.4 Apply the exact mathematical calculation for orphaned lots matching (`filled_orphaned_trade`)
- [x] 3.5 Ignore `pnl` field completely from `LogicalExecution` input within the aggregator, and enforce calculation solely on entry/exit prices and multiplier

## 4. Verification

- [x] 4.1 Wipe existing database records (or start fresh) and run a clean import of the IBKR XML file
- [x] 4.2 Verify that imported `Trade` records have the correct Gross PnL (mathematically exact) and Net PnL (Gross PnL minus commissions) without any proportional artifacts from batched execution PnL