## 1. Backend — Startup Migration Logging

- [ ] 1.1 In `app/core/migrations.py`: capture the current revision before running `alembic upgrade head` by calling `alembic current` and parsing its output
- [ ] 1.2 After the upgrade, call `alembic current` again to capture the post-upgrade revision
- [ ] 1.3 Log the result at INFO level: if revision unchanged → "Database at revision <rev> (head) — no pending migrations"; if changed → "Upgraded database from <old> to <new> (head)"
- [ ] 1.4 Run `mypy --strict` on `migrations.py` and fix any type errors

## 2. Frontend — ExecutionLegsTable Error State

- [ ] 2.1 In `ExecutionLegsTable.tsx`: refactor the `isError` branch to include a "Retry" button that calls `refetch()` from the `useTradeExecutions` hook return value
- [ ] 2.2 Add a diagnostic hint message alongside the retry button: "Could not load executions. Check backend connectivity."
- [ ] 2.3 Verify no `dark:` modifier is used; use semantic tokens only (`text-destructive`, `bg-muted`, etc.)

## 3. Frontend — ExecutionRow: Direction Toggle

- [ ] 3.1 Add `editDirection` state to `ExecutionRow` initialized from `execution.direction`
- [ ] 3.2 Render a LONG/SHORT two-button toggle in edit mode (pill style, consistent with the existing Side badge colors — emerald for LONG, red for SHORT)
- [ ] 3.3 Include `direction: editDirection` in the `useUpdateExecution` payload when saving
- [ ] 3.4 Ensure cancel resets `editDirection` to the original value

## 4. Frontend — ExecutionRow: Timestamp Picker

- [ ] 4.1 Add `editExecutedAt` state to `ExecutionRow` initialized from `execution.executed_at` converted to `datetime-local` format (`YYYY-MM-DDTHH:mm`)
- [ ] 4.2 Render `<input type="datetime-local">` in edit mode with the pre-filled value
- [ ] 4.3 On save, convert the local datetime string to a UTC ISO-8601 string via `new Date(value).toISOString()` and include as `executed_at` in the patch payload
- [ ] 4.4 Disable the save button if `editExecutedAt` is empty

## 5. Frontend — ExecutionRow: P&L Field

- [ ] 5.1 Add `editPnl` state to `ExecutionRow` initialized from `execution.pnl ?? ""`
- [ ] 5.2 Render a numeric input for P&L in edit mode (allow empty/negative values; placeholder "—")
- [ ] 5.3 On save, include `pnl: editPnl === "" ? null : editPnl` in the patch payload
- [ ] 5.4 Ensure cancel resets `editPnl` to the original value

## 6. Frontend — ExecutionLegsTable: Multiplier Column

- [ ] 6.1 In `ExecutionLegsTable.tsx`: add a `Mult.` column header between `Qty` and `Price` — visible always (not conditional), shows the per-leg multiplier
- [ ] 6.2 In `ExecutionRow.tsx` (view mode): render `execution.multiplier` in the new column; display as plain number (e.g., `100`); if `multiplier === 1` render as `—` to reduce noise for equity legs
- [ ] 6.3 In `ExecutionRow.tsx` (view mode): add a `Notional` column or tooltip showing `qty × price × multiplier` for legs with `multiplier > 1`; display in the same currency format as `price`
- [ ] 6.4 Do NOT add multiplier to the edit form — it is set at leg creation and is not patchable via `LogicalExecutionUpdate`

## 7. Backend — Remove Aggregated Fields from TradeUpdate

- [ ] 6.1 In `app/schemas/trade.py` (`TradeUpdate`): remove fields `pnl`, `net_pnl`, `commission`, `quantity`, `entry_price`, `exit_price`, `opened_at`, `closed_at` — keep `direction`, `multiplier`, and all metadata fields (`symbol`, `asset_class`, `stop_loss`, `take_profit`, `notes`, etc.)
- [ ] 6.2 In `app/services/trade_service.py`: remove the same 8 fields from `reaggregate_fields` (set becomes empty or only `direction`/`multiplier` if those still trigger re-aggregation)
- [ ] 6.3 Run `mypy --strict` and `ruff check` — fix any resulting type errors
- [ ] 6.4 Run the test suite (`pytest`) — fix any tests that sent the removed fields in `TradeUpdate` payloads

## 7. Frontend — ExecutionSummaryCard: Multiplier and Notional

- [ ] 7.1 In `ExecutionSummaryCard.tsx`: when `trade.multiplier > 1`, add a `Multiplier` tile showing the value (e.g., `100×`)
- [ ] 7.2 When `trade.multiplier > 1` and `trade.entry_price` is not null: add a `Notional Entry` tile showing `entry_price × quantity × multiplier` formatted as currency — this is the actual dollar exposure at entry
- [ ] 7.3 When `trade.multiplier > 1` and `trade.exit_price` is not null: add a `Notional Exit` tile showing `exit_price × quantity × multiplier`
- [ ] 7.4 Rename `VWAP Entry` / `VWAP Exit` to `Entry Price (per unit)` / `Exit Price (per unit)` when `trade.multiplier > 1` to clarify that the raw price is per share/point, not the full position value
- [ ] 7.5 When `trade.multiplier === 1` (equity): no change to existing layout — tiles remain as `VWAP Entry`, `VWAP Exit`, `Total Quantity`

## 8. Frontend — Remove Aggregated Fields from Trade Edit Form

- [ ] 8.1 In `TradeForm.tsx`: remove `pnl`, `commission`, `quantity`, `entry_price`, `exit_price`, `opened_at`, `closed_at` from the Zod edit schema and the form's default values for **edit mode** (create mode may still need them for manual trades without legs)
- [ ] 8.2 Hide the corresponding form inputs in edit mode; display `entry_price`, `exit_price`, `pnl`, `commission` as read-only text sourced from `ExecutionSummaryCard` instead
- [ ] 8.3 Run `bunx tsc --noEmit` — zero errors

## 9. Playwright E2E Tests — Global Setup

- [ ] 9.1 In `frontend/tests/global-setup.ts`: seed a dedicated `editExecutionTestTradeId` trade (e.g. TSLA LONG) with two execution legs (entry LONG + exit SHORT) via the REST API; write the ID to `seed-state.json`
- [ ] 9.2 Seed a dedicated `optionTestTradeId` OPTION trade (e.g. AAPL OPTION, `multiplier=100`) with one entry leg; write the ID to `seed-state.json`
- [ ] 9.3 Add `editExecutionTestTradeId: string` and `optionTestTradeId: string` to the `SeedState` type in `global-setup.ts`

## 10. Playwright E2E Tests — Spec File

- [ ] 10.1 Create `frontend/tests/specs/execution-leg-editor.spec.ts` with `import seedState from '../.auth/seed-state.json'`
- [ ] 10.2 **TC-094** — navigate to `editExecutionTestTradeId`, open overflow menu → Edit on first row, assert inputs visible for direction toggle, datetime, price, qty, commission, pnl
- [ ] 10.3 **TC-095** — enter edit mode on LONG leg, click SHORT toggle, save; assert Side badge shows SHORT
- [ ] 10.4 **TC-096** — enter edit mode, change datetime input to a new value, save; assert Date cell text updates
- [ ] 10.5 **TC-097** — enter edit mode on exit leg, set pnl to a value, save; assert ExecutionSummaryCard P&L text updates
- [ ] 10.6 **TC-098** — enter edit mode, change direction + price, click Cancel; assert original values still shown, no mutation request fired (use `page.route` spy)
- [ ] 10.7 **TC-099** — abort the executions fetch via `page.route('**/executions**', r => r.abort())`; assert Retry button and hint text visible; restore route and click Retry; assert table rows appear
- [ ] 10.8 **TC-100** — open trade edit form; assert no `<input>` for `pnl`, `entry_price`, `exit_price`, `commission`, `quantity`, `opened_at`, `closed_at`; assert these values appear as static text
- [ ] 10.9 **TC-101** — navigate to `optionTestTradeId` detail page; assert `Mult.` column visible in legs table; assert option leg row shows `100` in Mult. column; assert notional value shown as `qty × price × 100`

## 11. Verification

- [ ] 11.1 Run the full Playwright suite: `npx playwright test` — all TC-094 through TC-101 pass
- [ ] 11.2 Open an OPTION trade with existing legs; confirm the `Mult.` column shows `100` for the option leg; confirm notional value displayed
- [ ] 11.3 Open an EQUITY trade; confirm the `Mult.` column shows `—` for equity legs (multiplier=1)
- [ ] 11.4 Open a trade with existing legs manually; confirm the edit form shows NO inputs for aggregated fields
- [ ] 11.5 In the ExecutionLegsTable, enter edit mode on a leg and confirm all six fields render: `direction`, `executed_at`, `price`, `quantity`, `commission`, `pnl`
- [ ] 11.6 Edit each leg field, save, and verify the `ExecutionSummaryCard` updates (VWAP, commission total, P&L)
- [ ] 11.7 Cancel an edit and confirm no values changed
- [ ] 11.8 Restart the backend container and confirm the startup log contains the migration revision line
- [ ] 11.9 Run `bunx tsc --noEmit` — zero errors
- [ ] 11.10 Run `mypy --strict` on the backend — zero errors
