## Context

The current `Trade` model is keyed to a single `symbol`/`asset_class` pair. The FIFO re-aggregation engine (`_re_aggregate_trade()`) computes VWAP `entry_price`, `exit_price`, and net `quantity` from all non-deleted `LogicalExecution` legs — a calculation that is only meaningful when all legs trade the same instrument. Execution legs already carry their own `symbol`, `asset_class`, `direction`, `price`, and `quantity`, so the data layer can already hold multi-instrument legs; what is missing is the trade-level flag that tells the aggregation engine to skip cross-instrument VWAP, and the UI plumbing to create and display such a trade.

The project follows strict layered architecture (models → repositories → services → routers) with async-only DB access, RLS on all user tables, and `Decimal` for all monetary values.

## Goals / Non-Goals

**Goals:**
- Allow a user to flag any trade as a COMBO position at creation time.
- For COMBO trades, compute only `SUM(pnl)`, `SUM(commission)`, `MIN(opened_at)`, `MAX(closed_at)` during re-aggregation — skip VWAP-based `entry_price`, `exit_price`, `quantity`.
- Show per-leg Symbol and Asset Class in `ExecutionLegsTable` for COMBO trades.
- Show a COMBO badge on the trade detail and trade list pages.
- Support manual creation of COMBO trades via `TradeForm`.

**Non-Goals:**
- Restricting which symbols or asset classes can be combined (any mix is valid).
- Cross-symbol FIFO aggregation or shared cost-basis tracking.
- Converting an existing non-COMBO trade to COMBO after creation (for v1).
- Automatic COMBO detection from imported leg data.
- Changes to the COMBO leg split/merge/reassign logic (existing operations remain).

## Decisions

### D1: Boolean `is_combo` flag, not a `position_type` enum

A simple `is_combo: bool DEFAULT false` column is the minimal additive change. An enum (`EQUITY`, `OPTION`, `COMBO`, …) would require migrating all existing rows, changing every switch-statement, and deciding where `FUTURES` or `FOREX` fit. The boolean can be promoted to an enum in a later migration without API breakage.

*Alternatives considered:* `position_type` enum — deferred; adds schema churn with no immediate benefit beyond COMBO.

### D2: Re-aggregation branch in `_re_aggregate_trade()`, not a separate function

Adding an `if trade.is_combo:` branch inside the existing `_re_aggregate_trade()` function keeps the single call-site contract intact. All callers (create leg, update leg, delete leg, split, merge, detach, reassign) remain unchanged. The COMBO branch sets `entry_price = None`, `exit_price = None`, `quantity = None` and only computes `commission`, `pnl`, `opened_at`, `closed_at`.

**P&L for COMBO trades:** Each instrument in a COMBO has its own contract multiplier (equity = 1, option = 100). Cross-instrument VWAP is meaningless, so the COMBO branch uses `SUM(ex.pnl)` when any leg carries broker-reported P&L. When no broker P&L is available, `trade.pnl` is left `null` — per-leg price-based P&L across different multipliers requires per-instrument entry/exit matching which is deferred to a future iteration.

*Alternatives considered:* separate `_re_aggregate_combo_trade()` — creates two code paths to maintain with no benefit over an in-function branch.

### D3: `is_combo` is set at trade creation, immutable after

Making `is_combo` immutable after creation avoids the state-transition problem: an existing aggregated trade with VWAP `entry_price` becoming a COMBO mid-life would leave stale price data. `TradeUpdate` does NOT expose `is_combo`. A new trade must be explicitly created as COMBO.

*Alternatives considered:* allow toggling — too risky in v1; would require re-aggregation mode switch + field nullification.

### D4: `TradeForm` COMBO toggle clears `asset_class` (not required for COMBO)

For a COMBO trade, the top-level `asset_class` field on `Trade` has no per-instrument meaning. In create mode, enabling the COMBO toggle disables/hides the `asset_class` field and sets `asset_class = null` (nullable after migration addition) OR keeps a sentinel value like `COMBO`. The backend accepts `asset_class = null` for COMBO trades. The trade list renders "COMBO" in the asset-class column.

*Decision:* store `asset_class = null` for COMBO trades; render "COMBO" in the UI wherever asset class is displayed.

### D5: ExecutionLegsTable adds Symbol + Asset Class columns only when `is_combo=true`

Existing single-instrument trades do not need per-leg symbol/asset-class columns (all legs share the parent trade's values). Showing them always would add visual noise. Conditional rendering keyed on `trade.is_combo` keeps the standard view clean.

### D6: `LogicalExecutionCreate` gains `asset_class` and `multiplier` override fields for COMBO legs

Currently, when creating a manual execution leg, the service copies `symbol`, `asset_class`, and `multiplier` from the parent `Trade` (execution.py lines 103–106). For a COMBO trade this is wrong: an equity leg needs `multiplier=1`, an options leg needs `multiplier=100`, and their `asset_class` values differ.

`LogicalExecutionCreate` gains two optional fields:
- `asset_class: AssetClass | None = None` — when provided on a COMBO parent trade, overrides the trade-level value for this leg
- `multiplier: int | None = None` — when provided, overrides the trade-level multiplier for this leg

The service uses the override when the parent is a COMBO trade and the field is provided; otherwise it falls back to the trade value (preserving existing behaviour for all non-COMBO trades).

*Alternatives considered:* always use trade-level multiplier → option legs would carry `multiplier=1`, corrupting any price-based P&L computation. Rejected.

### D8: `ExecutionSummaryCard` switches to a per-instrument layout for COMBO trades

For COMBO trades, `entry_price`, `exit_price`, and `quantity` on the trade are always `null` — the standard flat grid becomes empty and useless. Instead, the card groups the executions prop by `(symbol, asset_class)` on the frontend and renders one row per instrument group:

```
AAPL EQUITY   LONG    100 shares    $150.00/share   Notional $15,000
AAPL OPTION   SHORT    2 contracts  $5.00/contract  Notional $1,000
────────────────────────────────────────────────────────────────────
Combined commission: $X.XX   Combined P&L: $XXX (if available)
```

Grouping logic (purely frontend, no new API):
1. Filter to non-deleted legs from the `executions` prop
2. Group by `(leg.symbol, leg.asset_class)`
3. For each group: compute VWAP entry price (`SUM(qty×price) / SUM(qty)` for entry-direction legs), sum quantities, derive notional = `VWAP × sumQty × leg.multiplier` (all legs in a single-instrument group share the same multiplier)
4. Totals row: `SUM(leg.commission)` across all groups, `SUM(leg.pnl)` when any leg has broker P&L

No new API endpoints. The card receives the `executions` prop already fetched by the trade detail page.

*Alternatives considered:* compute per-instrument summary on the backend — over-engineered; the data is already in the `executions` prop.

### D7: `LogicalExecutionRead` always exposes `multiplier` and `asset_class` per leg (already does)

`LogicalExecutionRead` already carries `multiplier` and `asset_class` from the DB row. No schema change needed on the read side — the ExecutionLegsTable simply displays these fields in the Symbol/Asset Class columns for COMBO trades.

## Risks / Trade-offs

- **Stale `entry_price`/`exit_price`/`quantity`** after toggling: Not possible — `is_combo` is immutable post-creation. On initial COMBO creation these fields are set to `null` immediately. → No mitigation needed.
- **Import compatibility**: Imported trades (broker CSV) will always have `is_combo=false`. A user wanting to mark an imported multi-leg trade as COMBO must create a new COMBO trade manually and detach/reassign legs. → Accepted for v1; documented in Non-Goals.
- **Trade list sorting/filtering by quantity or entry price**: For COMBO trades these are null. Sorting by `entry_price` will put COMBOs at the top or bottom depending on NULL ordering. → Accepted; NULL ordering is consistent and expected.
- **`net_pnl` for COMBO**: `net_pnl = pnl - commission` still applies (pure arithmetic on sums). → No issue.
- **COMBO P&L without broker data**: If no leg carries broker-reported P&L, `trade.pnl = null`. The user must enter P&L per leg (field already on `LogicalExecutionCreate`) to get a combined P&L. Price-based cross-instrument P&L computation (matching equity entries against option exits with different multipliers) is deferred. → Documented limitation; broker-imported data always carries leg P&L so the common import case is unaffected.
- **Reassign validation**: `reassign_execution()` currently checks `execution.symbol != target_trade.symbol` and rejects mismatches. For COMBO trades where symbol is the same but asset class differs (AAPL EQUITY leg → AAPL COMBO trade), this check passes. Cross-symbol reassign to COMBO (MSFT leg → AAPL COMBO trade) is blocked — correct behaviour.
