## Context

Currently, the `fifoPnlRealized` field from the IBKR XML export is used to calculate the PnL of imported trades. When multiple open lots with varying entry prices are closed by a single batched execution, the broker reports an aggregated `fifoPnlRealized`. Our FIFO aggregator was attempting to proportionally distribute this value across the matched open lots. This logic is mathematically flawed because `fifoPnlRealized` aggregates PnL across different historical entry prices, causing the individual lot PnL and Net PnL (which deducts commissions) to become misaligned and inaccurate.

## Goals / Non-Goals

**Goals:**
- Eliminate the usage of `fifoPnlRealized` for calculating the PnL of aggregated `Trade` objects.
- Ensure Gross PnL is calculated dynamically during FIFO matching using the strict formula: `(Exit Price - Entry Price) * Quantity * Multiplier`.
- Ensure Net PnL is calculated by subtracting matched commissions from the dynamically calculated Gross PnL.
- Add the required `multiplier` column to the database models (`LogicalExecution`, `Trade`).

**Non-Goals:**
- Removing `fifoPnlRealized` from the `BrokerRawTransaction` table (it will remain as immutable metadata).
- Changing the basic FIFO matching queue logic (we are only changing the PnL calculation step within the match).
- Supporting manual override of `multiplier` via the UI in this specific change (the backend schema is enough for now).

## Decisions

**1. Add Multiplier to Database:**
Since options and futures require a multiplier to correctly calculate PnL from price differences, we must add a `multiplier` column to both `LogicalExecution` and `Trade`.
*Rationale:* Without it, Gross PnL for options (e.g. 1 contract * 100 multiplier) would be vastly under-calculated.

**2. Dynamic PnL Calculation:**
Instead of passing down `pnl` from `LogicalExecution` to `TradeCreate`, the aggregator will compute `matched_pnl` directly.
*Rationale:* This guarantees that every matched lot has a mathematically exact PnL reflecting its specific entry and exit price, completely immune to broker-side aggregation artifacts.

**3. Retain `pnl` in `LogicalExecution` as Optional:**
The `pnl` field in `LogicalExecution` will remain, but it will be ignored during the aggregation to `Trade`.
*Rationale:* This keeps the `LogicalExecution` relatively close to the `BrokerRawTransaction` without tightly coupling the final `Trade` PnL to it.

## Risks / Trade-offs

- **Risk:** Existing imported trades will have incorrect PnL values until a clean re-import is performed.
  **Mitigation:** Document that a clean re-import of the IBKR XML is required as part of the acceptance criteria to verify the fix.
- **Risk:** The EUR converted PnL values (`pnl_eur`, `net_pnl_eur`) might need recalculation based on the new dynamic PnL.
  **Mitigation:** The EUR values will be calculated proportionally based on the new dynamically calculated `matched_pnl` and `matched_net_pnl`.