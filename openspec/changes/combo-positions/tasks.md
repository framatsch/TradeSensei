## 1. Backend — Data Model

- [x] 1.1 Add `is_combo: bool` column (default `False`, server_default `false`) to `app/models/trade.py`; no nullable — always has a value
- [x] 1.2 Make `asset_class` nullable on `Trade` model (already nullable or make it so); document that COMBO trades store `null` here

## 2. Backend — Alembic Migration

- [x] 2.1 Generate migration: `ALTER TABLE trades ADD COLUMN is_combo BOOLEAN NOT NULL DEFAULT false`
- [x] 2.2 In same migration: ensure `asset_class` column is nullable (add `ALTER COLUMN asset_class DROP NOT NULL` if currently NOT NULL)
- [x] 2.3 Run `alembic upgrade head` locally and verify schema

## 3. Backend — Schemas

- [x] 3.1 Add `is_combo: bool = False` to `TradeCreate` in `app/schemas/trade.py`
- [x] 3.2 Add `is_combo: bool` (read-only) to `TradeRead` in `app/schemas/trade.py`
- [x] 3.3 Ensure `is_combo` is **absent** from `TradeUpdate` (verify it cannot be patched)
- [x] 3.4 Make `asset_class` optional (`AssetClass | None = None`) in `TradeCreate` to support COMBO creation without an asset class
- [x] 3.5 Run `mypy --strict` on `app/schemas/trade.py` — zero errors

## 4. Backend — Per-leg `asset_class` and `multiplier` Override

- [x] 4.1 In `app/schemas/execution.py` (`LogicalExecutionCreate`): add optional fields `asset_class: AssetClass | None = None` and `multiplier: int | None = None`
- [x] 4.2 In `app/services/execution.py`, `create_execution()`: when creating a leg on a COMBO parent trade, use `data.asset_class` and `data.multiplier` if provided; fall back to `trade.asset_class` and `trade.multiplier` otherwise; for non-COMBO trades, preserve existing behaviour (always inherit from trade)
- [x] 4.3 Run `mypy --strict` on `app/schemas/execution.py` and `app/services/execution.py` — zero errors

## 5. Backend — Re-aggregation Branch

- [x] 5.1 In `app/services/execution.py`, inside `_re_aggregate_trade()`: add an `if trade.is_combo:` branch that sets `entry_price = None`, `exit_price = None`, `quantity = None`; computes `SUM(commission)`, `MIN(opened_at)`, `MAX(closed_at)` from all non-deleted legs
- [x] 5.2 COMBO P&L: if any leg has broker `pnl` → `trade.pnl = SUM(ex.pnl WHERE ex.pnl IS NOT NULL)`; if no leg has broker P&L → `trade.pnl = None` (price-based cross-instrument computation deferred)
- [x] 5.3 `trade.net_pnl = trade.pnl - total_commission` when `trade.pnl` is not None; else `None`
- [x] 5.4 Run `mypy --strict` on `app/services/execution.py` — zero errors

## 6. Backend — API Router

- [x] 6.1 Verify `POST /api/v1/trades` passes `is_combo` from `TradeCreate` through to the model (no router change needed if service already uses `**create_data.model_dump()`); confirm with a manual test
- [x] 6.2 Verify `PATCH /api/v1/trades/{id}` does NOT accept or apply `is_combo` (already absent from `TradeUpdate` — confirm no bypass)
- [x] 6.3 Run `ruff check` on all modified backend files

## 7. Frontend — Types

- [x] 7.1 Add `is_combo: boolean` to the `Trade` interface in `frontend/lib/types.ts`
- [x] 7.2 Add `is_combo?: boolean` to `TradeCreate` type (or equivalent create payload type)
- [x] 7.3 Add `asset_class?: AssetClass | null` and `multiplier?: number` to `ExecutionCreate` type in `frontend/lib/types.ts`
- [x] 7.4 Run `bunx tsc --noEmit` — zero errors

## 8. Frontend — ExecutionSummaryCard COMBO Layout

- [x] 8.1 In `ExecutionSummaryCard.tsx`: when `trade.is_combo === true`, render a per-instrument table instead of the flat grid
- [x] 8.2 Group the `executions` prop by `(symbol, asset_class)` (filter to non-deleted legs only)
- [x] 8.3 For each group: compute VWAP entry price (`SUM(qty×price) / SUM(qty)` for entry-direction legs), sum entry quantities, compute notional = `VWAP × sumQty × leg.multiplier`; render one row per group with: direction badge, `symbol + asset_class`, quantity with unit label ("shares" when multiplier=1; "contracts" when multiplier>1), multiplier value when >1 (shown as `×50`, `×100`, etc.), per-unit price, notional value — the multiplier is taken from `leg.multiplier` (never hardcoded)
- [x] 8.4 Render a totals row below the instrument rows: `Total Commission = SUM(leg.commission)` across all legs; `Combined P&L = SUM(leg.pnl)` when at least one leg has broker P&L, else `—`
- [x] 8.5 For COMBO trades: hide the standard `VWAP Entry`, `VWAP Exit`, `Total Quantity` tiles
- [x] 8.6 When `trade.is_combo === false`: render the existing flat grid unchanged
- [x] 8.7 Use semantic tokens only (`text-foreground`, `text-muted-foreground`, `bg-muted`, etc.) — no `dark:` modifier

## 9. Frontend — ExecutionLegsTable COMBO Columns

- [x] 9.1 In `frontend/components/trades/ExecutionLegsTable.tsx`: pass `trade` prop into the table; add `Symbol` and `Asset Class` column headers — rendered only when `trade.is_combo === true`
- [x] 9.2 In each `ExecutionRow`: show `execution.symbol` and `execution.asset_class` in the new columns when in COMBO context
- [x] 9.3 Ensure columns are hidden (not just empty) for non-COMBO trades — use conditional rendering, not CSS visibility

## 10. Frontend — Trade Detail COMBO Badge

- [x] 10.1 In `frontend/app/dashboard/trades/[id]/page.tsx`: when `trade.is_combo === true`, render a "COMBO" badge near the trade title in place of the LONG/SHORT directional badge
- [x] 10.2 Badge style: neutral/purple pill using semantic tokens only (no `dark:` modifier)

## 11. Frontend — Trade List COMBO Indicator

- [x] 11.1 In the trades list table component: when a row has `is_combo === true`, render "COMBO" in the asset-class/direction column instead of the normal `asset_class` + direction badge

## 12. Frontend — TradeForm COMBO Toggle

- [x] 12.1 In `frontend/components/trades/TradeForm.tsx` (create mode only): add a "COMBO position" toggle/checkbox above the `asset_class` field
- [x] 12.2 When the toggle is enabled: hide the `asset_class` dropdown, set `is_combo: true` in the form state
- [x] 12.3 When the toggle is disabled (default): show `asset_class` dropdown, set `is_combo: false`
- [x] 12.4 On form submit: include `is_combo` in the POST payload; omit `asset_class` when `is_combo` is true
- [x] 12.5 Do not show the COMBO toggle in edit mode (consistent with D3: `is_combo` immutable post-creation)

## 13. Playwright E2E Tests — Global Setup

- [x] 13.1 In `frontend/tests/global-setup.ts`: seed a dedicated `comboTestTradeId` COMBO trade (AAPL, `is_combo: true`) via the REST API; add one EQUITY leg (`asset_class: EQUITY`, `multiplier: 1`, direction LONG, broker `pnl: 500`) and one OPTION leg (`asset_class: OPTION`, `multiplier: 100`, direction SHORT, broker `pnl: 100`); write the ID to `seed-state.json`
- [x] 13.2 Add `comboTestTradeId: string` to the `SeedState` type in `global-setup.ts`

## 14. Playwright E2E Tests — Spec File

- [x] 14.1 Create `frontend/tests/specs/combo-positions.spec.ts` with `import seedState from '../.auth/seed-state.json'`
- [x] 14.2 **TC-101** — navigate to `comboTestTradeId` detail page; assert "COMBO" badge visible; assert no LONG/SHORT directional badge
- [x] 14.3 **TC-102** — assert ExecutionSummaryCard shows two instrument rows (AAPL EQUITY and AAPL OPTION); assert totals row shows combined P&L = 600; assert no `VWAP Entry` or `VWAP Exit` labels visible
- [x] 14.4 **TC-103** — assert execution legs table has "Symbol" and "Asset Class" column headers; rows show "AAPL + EQUITY" and "AAPL + OPTION"
- [x] 14.5 **TC-104** — navigate to a standard (non-COMBO) trade detail; assert no "Symbol" or "Asset Class" column header; assert `VWAP Entry` label visible in ExecutionSummaryCard
- [x] 14.6 **TC-105** — navigate to the trades list; find the COMBO trade row; assert asset-class cell shows "COMBO"
- [x] 14.7 **TC-106** — open trade creation form; enable the COMBO toggle; assert `asset_class` dropdown not visible; fill symbol + direction; submit; assert redirect to new trade detail and "COMBO" badge present

## 15. Verification

- [x] 15.1 Create a COMBO trade via the API; add one EQUITY leg (`multiplier=1`, broker `pnl=500`) and one OPTION leg (`multiplier=100`, broker `pnl=-200`); verify `entry_price`, `exit_price`, `quantity` are `null`; verify `trade.pnl = 300`
- [x] 15.2 Add legs with no broker P&L to a COMBO trade; verify `trade.pnl` remains `null`
- [x] 15.3 Open the COMBO trade detail; confirm ExecutionSummaryCard shows two instrument rows with correct notional values; confirm combined P&L in totals row
- [x] 15.4 Confirm no `VWAP Entry` / `VWAP Exit` / `Total Quantity` tiles in the COMBO card
- [x] 15.5 Open a standard trade; confirm ExecutionSummaryCard flat grid unchanged
- [x] 15.6 Attempt `PATCH /trades/{id}` with `{"is_combo": false}`; confirm `is_combo` remains `true`
- [x] 15.7 Run `npx playwright test combo-positions` — all TC-101 through TC-106 pass
- [x] 15.8 Run `bunx tsc --noEmit` — zero errors
- [x] 15.9 Run `mypy --strict` on modified backend files — zero errors
- [x] 15.10 Run `pytest` — all existing tests pass; add at minimum: create COMBO trade, add EQUITY + OPTION legs with broker P&L, verify trade.pnl = sum, verify entry_price/exit_price/quantity null
