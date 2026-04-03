## Why

The current PnL calculation for imported IBKR trades uses the `fifoPnlRealized` field from the broker's XML export. However, this field represents an aggregated mixed value for batched closures, which breaks our proportional FIFO distribution logic. When a closing execution matches against multiple open lots with different historical entry prices, proportionally splitting `fifoPnlRealized` leads to incorrect gross and net PnL values. We need to calculate Gross PnL strictly from the underlying math: `(Exit Price - Entry Price) * Quantity * Multiplier`.

## What Changes

- Add a `multiplier` field to the `Trade` and `LogicalExecution` database models and Pydantic schemas (defaulting to 1).
- Parse the `multiplier` from the IBKR XML export and persist it through to the `LogicalExecution`.
- Completely remove the logic in the FIFO aggregator (`backend/app/utils/parsers/aggregator.py`) that distributes `fifoPnlRealized`.
- Implement dynamic, isolated PnL calculation per FIFO match using the formula `(Exit Price - Entry Price) * Quantity * Multiplier`.
- Calculate Net PnL strictly as `Gross PnL - (Lot Commission + Execution Commission)`.
- Retain `fifoPnlRealized` only as immutable metadata in the `BrokerRawTransaction` table.

## Capabilities

### New Capabilities
- `pnl-calculation`: The ability to calculate Gross and Net PnL accurately using exact execution prices, quantities, and multipliers, without relying on aggregated broker PnL fields.

### Modified Capabilities
- `trade-import`: The process of importing trades from brokers is modified to calculate PnL dynamically rather than relying on broker-provided PnL values.

## Impact

- **Database**: Requires an Alembic migration to add the `multiplier` column to `trades` and `logical_executions`.
- **API**: The `TradeCreate`, `TradeUpdate`, and `TradeResponse` schemas will now include a `multiplier` field.
- **Aggregator**: The core FIFO matching logic in `backend/app/utils/parsers/aggregator.py` will be rewritten to calculate PnL dynamically.
- **Parsers**: The IBKR XML parser will need to extract and pass the `multiplier` to the `LogicalExecution`.
- **Data Integrity**: Existing imported trades will need to be re-imported or their PnL values will remain based on the old logic. A clean re-import will be required to verify the fix.