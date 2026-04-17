## 1. Backend — Startup Migration Logging

- [x] 1.1 In `app/core/migrations.py`: capture the current revision before running `alembic upgrade head` by calling `alembic current` and parsing its output
- [x] 1.2 After the upgrade, call `alembic current` again to capture the post-upgrade revision
- [x] 1.3 Log the result at INFO level: if revision unchanged → "Database at revision <rev> (head) — no pending migrations"; if changed → "Upgraded database from <old> to <new> (head)"
- [x] 1.4 Run `mypy --strict` on `migrations.py` and fix any type errors

## 2. Frontend — ExecutionLegsTable Error State

- [x] 2.1 In `ExecutionLegsTable.tsx`: refactor the `isError` branch to include a "Retry" button that calls `refetch()` from the `useTradeExecutions` hook return value
- [x] 2.2 Add a diagnostic hint message alongside the retry button: "Could not load executions. Check backend connectivity."
- [x] 2.3 Verify no `dark:` modifier is used; use semantic tokens only (`text-destructive`, `bg-muted`, etc.)

## 3. Frontend — ExecutionRow: Direction Toggle

- [x] 3.1 Add `editDirection` state to `ExecutionRow` initialized from `execution.direction`
- [x] 3.2 Render a LONG/SHORT two-button toggle in edit mode (pill style, consistent with the existing Side badge colors — emerald for LONG, red for SHORT)
- [x] 3.3 Include `direction: editDirection` in the `useUpdateExecution` payload when saving
- [x] 3.4 Ensure cancel resets `editDirection` to the original value

## 4. Frontend — ExecutionRow: Timestamp Picker

- [x] 4.1 Add `editExecutedAt` state to `ExecutionRow` initialized from `execution.executed_at` converted to `datetime-local` format (`YYYY-MM-DDTHH:mm`)
- [x] 4.2 Render `<input type="datetime-local">` in edit mode with the pre-filled value
- [x] 4.3 On save, convert the local datetime string to a UTC ISO-8601 string via `new Date(value).toISOString()` and include as `executed_at` in the patch payload
- [x] 4.4 Disable the save button if `editExecutedAt` is empty

## 5. Frontend — ExecutionRow: P&L Field

- [x] 5.1 Add `editPnl` state to `ExecutionRow` initialized from `execution.pnl ?? ""`
- [x] 5.2 Render a numeric input for P&L in edit mode (allow empty/negative values; placeholder "—")
- [x] 5.3 On save, include `pnl: editPnl === "" ? null : editPnl` in the patch payload
- [x] 5.4 Ensure cancel resets `editPnl` to the original value

## 6. Frontend — ExecutionLegsTable: Multiplier Column

- [x] 6.1 In `ExecutionLegsTable.tsx`: add a `Mult.` column header between `Qty` and `Price` — visible always (not conditional), shows the per-leg multiplier
- [x] 6.2 In `ExecutionRow.tsx` (view mode): render `execution.multiplier` in the new column; display as plain number (e.g., `100`); if `multiplier === 1` render as `—` to reduce noise for equity legs
- [x] 6.3 In `ExecutionRow.tsx` (view mode): add a `Notional` column or tooltip showing `qty × price × multiplier` for legs with `multiplier > 1`; display in the same currency format as `price`
- [x] 6.4 Do NOT add multiplier to the edit form — it is set at leg creation and is not patchable via `LogicalExecutionUpdate`

## 7. Backend — Remove Aggregated Fields from TradeUpdate

- [x] 6.1 In `app/schemas/trade.py` (`TradeUpdate`): remove fields `pnl`, `net_pnl`, `commission`, `quantity`, `entry_price`, `exit_price`, `opened_at`, `closed_at` — keep `direction`, `multiplier`, and all metadata fields (`symbol`, `asset_class`, `stop_loss`, `take_profit`, `notes`, etc.)
- [x] 6.2 In `app/services/trade_service.py`: remove the same 8 fields from `reaggregate_fields` (set becomes empty or only `direction`/`multiplier` if those still trigger re-aggregation)
- [x] 6.3 Run `mypy --strict` and `ruff check` — fix any resulting type errors
- [x] 6.4 Run the test suite (`pytest`) — fix any tests that sent the removed fields in `TradeUpdate` payloads

## 7. Frontend — ExecutionSummaryCard: Multiplier and Notional

- [x] 7.1 In `ExecutionSummaryCard.tsx`: when `trade.multiplier > 1`, add a `Multiplier` tile showing the value (e.g., `100×`)
- [x] 7.2 When `trade.multiplier > 1` and `trade.entry_price` is not null: add a `Notional Entry` tile showing `entry_price × quantity × multiplier` formatted as currency — this is the actual dollar exposure at entry
- [x] 7.3 When `trade.multiplier > 1` and `trade.exit_price` is not null: add a `Notional Exit` tile showing `exit_price × quantity × multiplier`
- [x] 7.4 Rename `VWAP Entry` / `VWAP Exit` to `Entry Price (per unit)` / `Exit Price (per unit)` when `trade.multiplier > 1` to clarify that the raw price is per share/point, not the full position value
- [x] 7.5 When `trade.multiplier === 1` (equity): no change to existing layout — tiles remain as `VWAP Entry`, `VWAP Exit`, `Total Quantity`

## 8. Frontend — Remove Aggregated Fields from Trade Edit Form

- [x] 8.1 In `TradeForm.tsx`: remove `pnl`, `commission`, `quantity`, `entry_price`, `exit_price`, `opened_at`, `closed_at` from the Zod edit schema and the form's default values for **edit mode** (create mode may still need them for manual trades without legs)
- [x] 8.2 Hide the corresponding form inputs in edit mode; display `entry_price`, `exit_price`, `pnl`, `commission` as read-only text sourced from `ExecutionSummaryCard` instead
- [x] 8.3 Run `bunx tsc --noEmit` — zero errors

## 9. Playwright E2E Tests — Global Setup

- [x] 9.1 In `frontend/tests/global-setup.ts`: seed a dedicated `editExecutionTestTradeId` trade (e.g. TSLA LONG) with two execution legs (entry LONG + exit SHORT) via the REST API; write the ID to `seed-state.json`
- [x] 9.2 Seed a dedicated `optionTestTradeId` OPTION trade (e.g. AAPL OPTION, `multiplier=100`) with one entry leg; write the ID to `seed-state.json`
- [x] 9.3 Add `editExecutionTestTradeId: string` and `optionTestTradeId: string` to the `SeedState` type in `global-setup.ts`

## 10. Playwright E2E Tests — Spec File

- [x] 10.1 Create `frontend/tests/specs/execution-leg-editor.spec.ts` with `import seedState from '../.auth/seed-state.json'`
- [x] 10.2 **TC-094** — navigate to `editExecutionTestTradeId`, open overflow menu → Edit on first row, assert inputs visible for direction toggle, datetime, price, qty, commission, pnl
- [x] 10.3 **TC-095** — enter edit mode on LONG leg, click SHORT toggle, save; assert Side badge shows SHORT
- [x] 10.4 **TC-096** — enter edit mode, change datetime input to a new value, save; assert Date cell text updates
- [x] 10.5 **TC-097** — enter edit mode on exit leg, set pnl to a value, save; assert ExecutionSummaryCard P&L text updates
- [x] 10.6 **TC-098** — enter edit mode, change direction + price, click Cancel; assert original values still shown, no mutation request fired (use `page.route` spy)
- [x] 10.7 **TC-099** — abort the executions fetch via `page.route('**/executions**', r => r.abort())`; assert Retry button and hint text visible; restore route and click Retry; assert table rows appear
- [x] 10.8 **TC-100** — open trade edit form; assert no `<input>` for `pnl`, `entry_price`, `exit_price`, `commission`, `quantity`, `opened_at`, `closed_at`; assert these values appear as static text
- [x] 10.9 **TC-101** — navigate to `optionTestTradeId` detail page; assert `Mult.` column visible in legs table; assert option leg row shows `100` in Mult. column; assert notional value shown as `qty × price × 100`

## 11. Verification

- [x] 11.1 Run the full Playwright suite: `npx playwright test` — all TC-094 through TC-101 pass
- [x] 11.2 Open an OPTION trade with existing legs; confirm the `Mult.` column shows `100` for the option leg; confirm notional value displayed
- [x] 11.3 Open an EQUITY trade; confirm the `Mult.` column shows `—` for equity legs (multiplier=1)
- [x] 11.4 Open a trade with existing legs manually; confirm the edit form shows NO inputs for aggregated fields
- [x] 11.5 In the ExecutionLegsTable, enter edit mode on a leg and confirm all six fields render: `direction`, `executed_at`, `price`, `quantity`, `commission`, `pnl`
- [x] 11.6 Edit each leg field, save, and verify the `ExecutionSummaryCard` updates (VWAP, commission total, P&L)
- [x] 11.7 Cancel an edit and confirm no values changed
- [x] 11.8 Restart the backend container and confirm the startup log contains the migration revision line
- [x] 11.9 Run `bunx tsc --noEmit` — zero errors
- [x] 11.10 Run `mypy --strict` on the backend — zero errors
