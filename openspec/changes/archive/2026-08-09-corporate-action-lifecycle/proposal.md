## Why

Corporate actions (stock splits and reverse splits) change the share count and price of positions held across their effective date. Three independent implementations of that arithmetic exist today and they disagree on the most basic question — which positions an action affects at all.

The FIFO aggregator adjusts only lots that were still open when the effective date was crossed. `ExecutionService._re_aggregate_trade` adjusts every execution before the effective date, regardless of whether the position was still open. Corporate action CRUD triggers the latter across the whole symbol, so editing a split's date would rewrite trades that were closed long before it: the production `OTLK` trades closed 2023-05-24 would go from `quantity=69, entry_price=1.44` to `3.45 / 28.80`. The data is currently intact because that trigger has never fired for those symbols.

A second inconsistency is already visible: `GET /trades/{id}/executions` returns split-adjusted leg values while the `Trade` header returns historical values, so in one response the legs no longer sum to the header, with nothing indicating why.

This change fixes the semantics, collapses the implementations into one, and makes the two legitimate value bases — historical and chart-adjusted — explicit and separately consistent.

## What Changes

- Define the holding-period rule as the single semantics for which positions a corporate action affects, and route every code path through one shared implementation.
- Stop scaling commission by split ratios; commission is a currency amount.
- Rebuild the trade projection from immutable `LogicalExecution` records only, removing the FIFO seed-lot path that would apply historical ratios a second time to already-adjusted lots.
- Expose trade values on both the historical and the chart-adjusted basis, each internally consistent, and mark trades affected by a corporate action.
- Invalidate cached `ohlc_prices` bars when a corporate action changes, so chart bars and execution markers rest on the same adjustment basis.
- Enforce one corporate action per symbol and effective date, so a duplicate cannot compound its ratio.
- Make corporate action changes atomic and recalculation idempotent, so a failed change leaves nothing half-applied and a retry is always safe.
- Delete the unreachable Schwab CSV parser, which is what keeps the seed-lot fallback alive.

## Capabilities

### New Capabilities
- `corporate-action-lifecycle`: Defines the complete lifecycle of a corporate action and its impact on trade matching, aggregation, and the immutable logical execution layer.

### Modified Capabilities

## Impact

- **Affected Code**: `backend/app/utils/split_adjust.py` (becomes the single implementation), `backend/app/utils/parsers/aggregator.py`, `backend/app/services/execution.py`, `backend/app/services/corporate_action_service.py`, `backend/app/services/import_service.py`, `frontend/components/trades/` (impact marker).
- **Deleted**: `backend/app/utils/parsers/schwab.py` and its unit tests — unreachable from production code, and the reason the seed-lot fallback still exists.
- **APIs**: `/corporate-actions` CRUD triggers symbol-wide trade recalculation and price-cache invalidation in one transaction, and returns a conflict on a duplicate symbol/date. The trade read model gains chart-adjusted counterparts and a corporate-action marker.
- **Data Model**: Unique constraint on `corporate_actions (user_id, symbol, date)`. No new `Trade` columns — the chart-adjusted basis is derived on read. `LogicalExecution` remains immutable and raw.
- **Behavioural change**: `net_pnl` changes for trades held across a split, because commission is no longer scaled by the ratio. Requires a before/after ground-truth diff.
- **Known approximation**: the effective-date boundary is exchange-local, but `LogicalExecution` stores no exchange, so USD instruments default to `America/New_York` at a single documented call site.
- **Deferred**: ratio precision, fractional shares, broken-boundary detection, conid-lineage scoping, and an exchange field on `LogicalExecution` are recorded as Open Questions in `design.md`.
