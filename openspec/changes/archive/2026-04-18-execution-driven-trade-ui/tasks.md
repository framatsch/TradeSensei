## 1. Backend: Execution CRUD API

- [x] 1.1 Create `app/schemas/execution.py` with `LogicalExecutionRead` (all fields from model), `LogicalExecutionCreate` (direction, quantity, price, commission, executed_at, pnl), and `LogicalExecutionUpdate` (all optional) Pydantic schemas
- [x] 1.2 Create `app/repositories/execution.py` with `ExecutionRepository` — methods: `list_by_trade_id`, `get_by_id`, `create`, `update`, `delete`, `reassign_to_trade` (for merge)
- [x] 1.3 Create `app/services/execution.py` with `ExecutionService` — methods: `list_for_trade`, `create_manual_execution` (creates with status=manual, triggers re-aggregation), `update_execution` (updates + re-aggregates), `delete_execution` (deletes + re-aggregates or deletes empty trade)
- [x] 1.4 Create `app/api/v1/executions.py` router with endpoints: `GET /trades/{trade_id}/executions`, `POST /trades/{trade_id}/executions`, `PATCH /executions/{execution_id}`, `DELETE /executions/{execution_id}`
- [x] 1.5 Register the execution router in `app/api/v1/router.py`
- [x] 1.6 Add `has_conflict` field to `TradeRead` and `TradeFilterParams` schemas; add `has_conflict` filter to trade repository query builder

## 2. Backend: Trade Merge Endpoint

- [x] 2.1 Add `MergeTradesRequest` schema to `app/schemas/trade.py` with `trade_ids: list[UUID]` (min_length=2, max_length=10)
- [x] 2.2 Add `merge_trades` method to `TradeService` — validates same symbol/account/asset_class, reassigns all LogicalExecutions to the oldest trade, copies/appends metadata (notes, tags from non-survivors), deletes empty trades, re-aggregates survivor
- [x] 2.3 Add `POST /api/v1/trades/merge` endpoint to `app/api/v1/trades.py` calling the merge service method
- [x] 2.4 Write unit tests for merge service: happy path (2 trades), validation failures (different symbol, different account, <2 trades, >10 trades), metadata preservation
- [x] 2.5 Add `reassign_execution` method to `ExecutionService` — validates same symbol/account between execution and target trade, updates `trade_id`, re-aggregates both source and target trades, deletes source trade if empty
- [x] 2.6 Add `POST /api/v1/executions/{execution_id}/reassign` endpoint accepting `{"target_trade_id": "uuid"}` — calls `reassign_execution`, returns updated execution + affected trades
- [x] 2.7 Add `detach_execution` method to `ExecutionService` — validates trade has >1 executions, creates a new Trade, reassigns execution to new trade, re-aggregates both trades
- [x] 2.8 Add `POST /api/v1/executions/{execution_id}/detach` endpoint — calls `detach_execution`, returns the newly created trade
- [x] 2.9 Write unit tests for reassign: happy path, symbol mismatch, account mismatch, source trade deleted when empty
- [x] 2.10 Write unit tests for detach: happy path, cannot detach last execution, new trade is correctly aggregated

## 3. Backend: Auto-Create Execution on Manual Trade Creation

- [x] 3.1 Modify `TradeService.create_trade` to auto-create a `LogicalExecution` with `status=manual` from the trade's entry fields (direction, quantity, entry_price, opened_at, commission) when the trade is created via the API (not via import)
- [x] 3.2 Write unit test: creating a trade via `POST /api/v1/trades` results in both a Trade and a LogicalExecution record

## 4. Backend: Re-Aggregation Trigger

- [x] 4.1 Extract a `re_aggregate_trade(trade_id)` utility in `ExecutionService` that re-computes trade fields (quantity, entry_price, exit_price, pnl, net_pnl, commission, opened_at, closed_at) from the trade's LogicalExecutions using VWAP logic
- [x] 4.2 Ensure `re_aggregate_trade` also clears `has_conflict` when the position totals are consistent after the mutation
- [x] 4.3 Call `re_aggregate_trade` from create, update, delete, and merge methods
- [x] 4.4 Write integration test: add an execution, verify trade values are recomputed; delete an execution, verify trade values update; delete last execution, verify trade is deleted

## 5. Backend: Conflict Filter & System Filter

- [x] 5.1 Add `has_conflict: bool | None` to `TradeFilterParams` and wire it into the repository query (WHERE clause)
- [x] 5.2 Create an Alembic data migration (or seed script) to insert a system-level saved filter: `name="Needs Review"`, `scope=SYSTEM`, `definition={"has_conflict": true}`, `needs_review=false`
- [x] 5.3 Write test: GET /trades?has_conflict=true returns only conflicted trades

## 6. Frontend: TypeScript Types & React Query Hooks

- [x] 6.1 Add `ExecutionStatus`, `LogicalExecution`, `LogicalExecutionCreate`, `LogicalExecutionUpdate` types to `lib/types.ts`
- [x] 6.2 Add `MergeTradesRequest` type to `lib/types.ts`
- [x] 6.3 Add `has_conflict` boolean field to the `Trade` interface in `lib/types.ts`
- [x] 6.4 Create `hooks/useExecutions.ts` with: `useTradeExecutions(tradeId)` (GET list), `useCreateExecution(tradeId)` (POST), `useUpdateExecution()` (PATCH), `useDeleteExecution()` (DELETE), `useReassignExecution()` (POST reassign), `useDetachExecution()` (POST detach) — all invalidating trade + execution caches on mutation
- [x] 6.5 Create `hooks/useMergeTrades.ts` with `useMergeTrades()` mutation hook (POST /trades/merge) that invalidates the trades list cache
- [x] 6.6 Add `ReassignExecutionRequest` type (`{ target_trade_id: string }`) to `lib/types.ts`

## 7. Frontend: Execution Legs Display Components

- [x] 7.1 Create `components/trades/ExecutionStatusBadge.tsx` — small colored badge rendering `imported` (blue), `manual` (purple), `merged` (orange), `split` (cyan) following project badge conventions
- [x] 7.2 Create `components/trades/ExecutionSummaryCard.tsx` — displays VWAP entry price, VWAP exit price, total quantity, total commission, stop loss, take profit. Shows "Computed" badge and "Values are computed from N execution legs" subtitle. Uses `bg-card rounded-xl border border-border` styling
- [x] 7.3 Create `components/trades/ExecutionRow.tsx` — single execution row: date, side badge (BUY green / SELL red), qty, price, commission, P&L, status badge, overflow menu (⋮) with actions: "Edit", "Move to...", "Detach as new Trade", "Delete". Supports click-to-edit inline mode (price, qty, commission become inputs; Save/Cancel buttons appear)
- [x] 7.4 Create `components/trades/ExecutionLegsTable.tsx` — fetches executions via `useTradeExecutions(tradeId)`, renders header row + `ExecutionRow` for each execution, "+ Add Execution" button in header. Collapsible section with collapse/expand toggle
- [x] 7.5 Update `app/dashboard/trades/[id]/page.tsx`: replace the flat "Execution Details" grid with `ExecutionSummaryCard` + `ExecutionLegsTable`. Remove `PartialCloseModal` import and "Partial Close" button

## 8. Frontend: Chart Execution Markers

- [x] 8.1 Refactor `TradeChart` marker logic to accept a `LogicalExecution[]` array (via props or `useTradeExecutions`) instead of using trade-level `opened_at`/`closed_at`
- [x] 8.2 Group executions by snapped candle time and side (entry vs exit). For each candle: if one execution, render a single `arrowUp`/`arrowDown` with label `"+{qty} @ ${price}"`; if multiple same-side executions, merge into one marker with combined label `"+{qty1}+{qty2} @ ${price1}/${price2}"`
- [x] 8.3 Render entry markers (arrowUp, belowBar, #00d2ff cyan) and exit markers (arrowDown, aboveBar, #f0abfc fuchsia) independently — a candle with both entries and exits gets two markers
- [x] 8.4 Fallback: if no executions are loaded yet (loading state or legacy trade), fall back to the current single ENTRY/EXIT marker behavior using trade-level timestamps

## 9. Frontend: Add Execution Modal

- [x] 9.1 Create `components/trades/AddExecutionModal.tsx` — modal with BUY/SELL segmented toggle, Quantity input, Price input, Executed At datetime-local input (defaults to now), Commission input (defaults to 0), optional P&L input. Cancel and "Add Execution" buttons. Full-width on mobile
- [x] 9.2 Wire `AddExecutionModal` into `ExecutionLegsTable` — clicking "+ Add Execution" opens it, successful creation refreshes the table and summary card
- [x] 9.3 Delete `components/trades/PartialCloseModal.tsx` and remove all imports/references from the codebase
- [x] 9.4 Update `hooks/useTrade.ts` to remove the `usePartialCloseTrade` hook (or deprecate it)

## 10. Frontend: Inline Editing in Sidebar Cards + Remove Edit Form

- [x] 10.1 Add inline-editable SL/TP to `PerformanceCard`: click on SL or TP value → transforms into number input with Save (✓) / Cancel (✕) buttons. Save calls `PATCH /api/v1/trades/{id}` with `{ stop_loss }` or `{ take_profit }`. Clearing sends `null`. Dependent metrics (Initial Risk, Planned RRR, Realized R) recalculate on save
- [x] 10.2 Add inline-editable Playbook to `PlaybookPsychologyCard`: click playbook name → dropdown of all playbooks appears. Selecting auto-saves via `PATCH /api/v1/trades/{id}` with `{ playbook_id }`. "None" option clears the assignment
- [x] 10.3 Add inline-editable Tags to `PlaybookPsychologyCard`: click tags area → tag picker with search appears. Toggling tags auto-saves via `PATCH /api/v1/trades/{id}` with updated `{ tag_ids }` array
- [x] 10.4 Create `components/trades/CorrectTradeModal.tsx` — small modal for rare corrections: editable Symbol + Asset Class fields, read-only Direction + Currency, warning text ("These fields affect trade identity. Only change them to fix import errors."), sets `is_manually_edited: true` on save
- [x] 10.5 Update Trade Detail header overflow menu (⋮): replace "Edit Trade" with "Correct Trade..." which opens the `CorrectTradeModal`
- [x] 10.6 Remove `TradeEditForm` component and the `{isEditing ? <TradeEditForm/> : <NormalView/>}` toggle from `TradeDetailPage` — the page always renders the normal view
- [x] 10.7 Delete `components/trades/TradeEditForm.tsx` and remove all imports/references from the codebase

## 11. Frontend: Conflict Resolution UI

- [x] 11.1 Create `components/trades/ConflictBanner.tsx` — amber banner with warning icon, title "Position Conflict", explanation text, Dismiss button (session-only via useState), Help link. Uses `bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800`
- [x] 11.2 Add `ConflictBanner` to `TradeDetailPage` — renders below the header when `trade.has_conflict === true`
- [x] 11.3 Update `TradeRow` — add a small amber ⚠ icon next to the symbol when `has_conflict === true`
- [x] 11.4 Add "Needs Review" to the sidebar trade filter list — display the system filter with a count badge showing number of conflicted trades. Wire click to apply the filter

## 12. Frontend: Trade Merge Workflow

- [x] 12.1 Create `components/trades/MergePreviewModal.tsx` — displays source trade cards (symbol, qty, execution count, PnL each), arrow, merged result card (combined values). Warning text about irreversibility. Cancel and "Merge Trades" buttons. Calls `useMergeTrades` on confirm
- [x] 12.2 Create `components/trades/TradePickerModal.tsx` — searchable list of trades filtered to same symbol/account. Checkboxes to select trades. Reused for both "Merge with..." and "Move to..." flows. "Continue"/"Select" button returns the selected trade(s)
- [x] 12.3 Update `BulkActionToolbar` — add "Merge" button visible when 2+ selected trades share the same symbol. Clicking opens `MergePreviewModal` with selected trades
- [x] 12.4 Update `TradeDetailPage` — add overflow menu (⋮) to header with "Edit Trade", "Merge with...", "Delete Trade" options. "Merge with..." opens `TradePickerModal`
- [x] 12.5 Wire "Move to..." in `ExecutionRow` context menu: clicking opens `TradePickerModal` (single-select mode), on selection calls `useReassignExecution` with `{ target_trade_id }`, refreshes both source and target trade caches, shows success toast
- [x] 12.6 Wire "Detach as new Trade" in `ExecutionRow` context menu: clicking shows confirmation dialog, on confirm calls `useDetachExecution`, refreshes execution table, shows success toast with link to newly created trade

## 13. Backend Tests: New Execution & Merge Tests

- [x] 13.1 Create `tests/test_execution_service.py` — unit tests for `ExecutionService`: `create_manual_execution` (happy path, validation), `update_execution` (price change triggers re-aggregation), `delete_execution` (re-aggregates parent, deletes empty trade), `reassign_execution` (happy path, symbol mismatch, account mismatch, source trade deleted when empty), `detach_execution` (happy path, cannot detach last execution)
- [x] 13.2 Create `tests/test_execution_api.py` — integration tests for execution endpoints: `GET /trades/{id}/executions` (list, empty, auth), `POST /trades/{id}/executions` (create manual, validation 422), `PATCH /executions/{id}` (update, auth), `DELETE /executions/{id}` (delete, last-execution cascade), `POST /executions/{id}/reassign` (happy path, validation), `POST /executions/{id}/detach` (happy path, single-execution rejection)
- [x] 13.3 Create `tests/test_merge_trades.py` — integration tests for `POST /api/v1/trades/merge`: happy path (2 trades, 3 trades), validation failures (different symbol, different account, <2 trades, >10 trades), metadata preservation (notes appended, tags from oldest, playbook from oldest), re-aggregation correctness of survivor

## 14. Backend Tests: Consolidate Existing Tests

- [x] 14.1 Update `tests/test_trades_partial_close.py` → replace the 4 `PartialClose` tests with execution-based equivalents: "adding a SELL execution to an open LONG trade reduces position", "adding SELL for full qty closes the trade", "invalid execution (qty=0) returns 422". Rename file to `tests/test_trades_execution_close.py`
- [x] 14.2 Update `tests/test_aggregator.py` → replace `test_aggregate_partial_close` with execution-driven aggregation test: "re-aggregate from 2 BUY + 1 SELL execution computes correct VWAP entry, exit, PnL" — Added `test_vwap_entry_exit_calculation_multi_leg()` and `test_vwap_with_multiplier_options_contract()`
- [x] 14.3 Update `tests/test_trade_service.py` → fix tests that break due to `create_trade` now auto-creating a `LogicalExecution`. Verify that `create_trade` response includes the auto-created execution. Add assertion that the execution has `status=manual` — Already present: `test_create_trade_auto_creates_execution()`
- [x] 14.4 Update `tests/test_trades_api.py` → add `has_conflict` field assertions to trade response tests. Add filter test: `GET /trades?has_conflict=true` — Already present: `test_has_conflict_filter_returns_only_conflicted_trades()` and related tests
- [x] 14.5 Update `tests/test_trade_schemas.py` → add tests for new schemas: `LogicalExecutionRead`, `LogicalExecutionCreate`, `LogicalExecutionUpdate`, `MergeTradesRequest` validation — Already present with complete field coverage
- [x] 14.6 Add precise VWAP aggregation tests to `tests/test_aggregator.py` — see spec `specs/aggregator-vwap-precision/spec.md` for exact input values, formulas, and expected outputs (VWAP entry, VWAP exit, gross PnL, net PnL, net_pnl with multiplier, closed_at) — Created spec file and implemented tests
- [x] 14.7 Add precise schema field tests to `tests/test_trade_schemas.py` — see spec `specs/schema-field-contracts/spec.md` for exhaustive field lists, type constraints, defaults, and validation boundaries for `LogicalExecutionRead`, `LogicalExecutionCreate`, `LogicalExecutionUpdate`, and `MergeTradesRequest` — Created spec file and implemented field completeness tests

## 15. Frontend Tests: Trade Detail E2E Consolidation

The existing `Trade Detail` describe block in `trades.spec.ts` has only one test (TC-060: "page renders
without 404") with zero assertions on actual content. This must be expanded to cover the new
execution-driven layout and serve as a proper regression suite.

### Seed data reference

`global-setup.ts` creates the following deterministic records. Tests read IDs from
`tests/.auth/seed-state.json` (type: `SeedState`):

| Key in SeedState | Description |
|---|---|
| `executionTradeId` | MSFT LONG trade with **2 pre-seeded execution legs**: BUY 100 @ $400.00 (commission $2.00) + SELL 50 @ $420.00 (commission $1.00). Re-aggregated values: `entry_price=$400.00`, `exit_price=$420.00`, `quantity=100`, `commission=$3.00`. |
| `mergeTradeIds[0]` | AAPL LONG 50 @ $180.00 — survivor trade (older, opened 45 days ago) |
| `mergeTradeIds[1]` | AAPL LONG 30 @ $182.00 — trade to be merged in (opened 44 days ago) |

For tests that just need any trade detail page (TC-060, TC-064 to TC-067), navigate to the first trade
in the list as before.

### Selector conventions for new components

| Component | How to find it |
|---|---|
| Execution Summary Card | `page.getByText('Execution Summary')` (heading inside the card) |
| "Computed" badge | `page.getByText('Computed')` (badge inside summary card) |
| "Values are computed from N execution legs" | `page.getByText(/Values are computed from \d+ execution legs?/)` |
| VWAP Entry value | `page.getByText('VWAP Entry').locator('..').getByRole('term')` — or use the `<dd>` sibling of `<dt>` containing "VWAP Entry". Simpler: assert `page.getByText('$400.00')` is visible in the card. |
| Execution Legs section header | `page.getByRole('button', { name: /Execution Legs/ })` (the collapse toggle) |
| "+ Add Execution" button | `page.getByRole('button', { name: 'Add Execution' })` |
| Execution table rows | `page.locator('table tbody tr')` — each row is a `<tr>` inside the `ExecutionLegsTable` |
| Side badge in execution row | `page.getByText('LONG')` / `page.getByText('SHORT')` within `tbody tr` |
| Status badge in execution row | `page.getByText('manual')` / `page.getByText('imported')` within `tbody tr` |
| Execution row overflow menu (⋮) | `page.locator('tbody tr').first().getByRole('button', { name: '' })` — or locate by `MoreHorizontal` aria via `page.locator('tbody tr').first().locator('button').last()` |
| Trade header overflow menu (⋮) | `page.getByRole('button', { name: 'Trade actions' })` (aria-label on the button) |
| Conflict banner | `page.getByText('Position Conflict')` |
| "Gross P&L" sidebar label | `page.getByText('Gross P&L')` |
| "Net P&L" sidebar label | `page.getByText('Net P&L')` |
| "Holding Period" sidebar label | `page.getByText('Holding Period')` |
| "Return %" sidebar label | `page.getByText('Return %')` |
| Stop Loss inline field | `page.getByLabel('Stop Loss')` — or `page.getByText('Stop Loss').locator('..').locator('button')` for the click-to-edit trigger |
| Playbook inline field | `page.getByTitle('Click to change playbook')` |
| AddExecutionModal | `page.getByRole('heading', { name: 'Add Execution' })` |
| AddExecutionModal error | `page.getByText('Quantity must be greater than 0.')` |
| BUY toggle in modal | `page.getByRole('button', { name: 'BUY' })` |
| SELL toggle in modal | `page.getByRole('button', { name: 'SELL' })` |
| MergePreviewModal heading | `page.getByRole('heading', { name: 'Merge Trades' })` |
| "Merge Trades" confirm button | `page.getByRole('button', { name: 'Merge Trades' })` (the blue submit button) |
| "Merge" bulk toolbar button | `page.getByRole('button', { name: 'Merge' })` in the bulk toolbar |
| BulkActionToolbar | visible when checkboxes are selected; look for `page.getByRole('button', { name: 'Merge' })` |

### How to navigate to the execution-test trade

```typescript
import seedState from '../.auth/seed-state.json';
// ...
await page.goto(`/dashboard/trades/${seedState.executionTradeId}`);
await page.waitForLoadState('networkidle');
```

---

- [x] 15.1 Rewrite/expand the `Trade Detail` describe block in `trades.spec.ts` with the following
  tests. For TC-060 to TC-067, navigate via the trades list (first row link) as before — these tests
  do **not** depend on the execution-test seed trade.
  - TC-060 (update): Trade detail page renders trade header — assert `page.locator('main')` is visible
    AND that the page contains at least one of the direction badges LONG or SHORT
    (`page.getByText('LONG').or(page.getByText('SHORT')).first()` is visible).
  - TC-061: Navigate to `executionTradeId`. Assert `page.getByText('Execution Summary')` is visible.
    Assert `page.getByText('VWAP Entry')` is visible. Assert `page.getByText('$400.00')` appears at
    least once in the summary card. Assert `page.getByText('Total Quantity')` is visible.
    Assert `page.getByText('$3.00')` is visible (commission).
  - TC-062: Navigate to `executionTradeId`. Wait for `page.locator('table tbody tr')` to have count 2
    (`await expect(page.locator('table tbody tr')).toHaveCount(2)`). Assert first row contains `LONG`
    badge and second row contains `SHORT` badge.
  - TC-063: Navigate to `executionTradeId`. Get all `<td>` cells in column 0 (Date) from `tbody tr`.
    Assert the first row's date string is earlier than the second row's date string (parse with
    `new Date()`).
  - TC-064: Navigate to `executionTradeId`. Assert `page.getByRole('button', { name: 'Add Execution' })`
    is visible.
  - TC-065: Navigate via list. Assert `page.getByText('Gross P&L')` is visible. Assert
    `page.getByText('Net P&L')` is visible. Assert `page.getByText('Return %')` is visible. Assert
    `page.getByText('Holding Period')` is visible.
  - TC-066: Navigate via list. Click `page.getByRole('button', { name: 'Trade actions' })`. Assert
    `page.getByText('Correct Trade…')` is visible. Assert `page.getByText('Merge with…')` is visible.
  - TC-067: Navigate via list to a non-conflicting trade (first row is fine). Assert
    `page.getByText('Position Conflict')` is **not** visible
    (`await expect(page.getByText('Position Conflict')).not.toBeVisible()`).

- [x] 15.2 Add E2E tests for Add Execution Modal flow in a new `describe('Add Execution Modal')` block
  in `trades.spec.ts`. All three tests navigate to `executionTradeId` first.
  - TC-070: Click `page.getByRole('button', { name: 'Add Execution' })`. Assert
    `page.getByRole('heading', { name: 'Add Execution' })` is visible. Assert
    `page.getByRole('button', { name: 'BUY' })` is visible. Assert
    `page.getByRole('button', { name: 'SELL' })` is visible. Assert a `datetime-local` input is
    present (`page.locator('input[type="datetime-local"]')` is visible).
  - TC-071: Open the modal. Fill Quantity = `"10"`, Price = `"410.00"`. Click
    `page.getByRole('button', { name: 'Add Execution' }).last()` (the submit button in the modal — use
    `.last()` to avoid matching the trigger button). Assert modal closes
    (`page.getByRole('heading', { name: 'Add Execution' })` becomes not visible). Assert
    `page.locator('table tbody tr')` count increases to 3.
  - TC-072: Open the modal. Set Quantity to `"0"` (type "0" into the Quantity field). Click the submit
    button. Assert `page.getByText('Quantity must be greater than 0.')` is visible. Assert the modal is
    still open (`page.getByRole('heading', { name: 'Add Execution' })` is still visible).

- [x] 15.3 Add E2E tests for inline sidebar editing in a new `describe('Inline Sidebar Editing')` block.
  All tests navigate to `executionTradeId`.
  - TC-075: Locate the Stop Loss section: `page.getByText('Stop Loss').locator('..')`. Click the
    displayed value button (it renders `—` by default). Assert an `<input type="number">` appears
    (`page.locator('input[type="number"]').first()` is visible). Type `"150.00"`. Click the Save
    button (`page.locator('button[title="Save"]').first()`). Assert the input disappears and the
    text `$150.00` appears in the Stop Loss area.
  - TC-076: `page.getByTitle('Click to change playbook')` click. Assert a dropdown appears containing
    `page.getByText('Breakout')` (seeded playbook). Click `Breakout`. Assert the trigger now shows
    `Breakout` (`page.getByTitle('Click to change playbook')` contains text "Breakout").
  - TC-077: Locate the Tags section in the PlaybookPsychologyCard. Click the tags edit area. Assert
    the tag picker appears containing `page.getByText('high-conviction')`. Click it. Assert the tag
    appears as selected (the tag chip is visible in the card area).

- [x] 15.4 Add E2E tests for the Merge workflow in a new `describe('Merge Workflow')` block in
  `trades.spec.ts`. Read `mergeTradeIds` from `seed-state.json`.
  - TC-080: Navigate to `/dashboard/trades`. Check the checkbox in the row for `mergeTradeIds[0]`
    and the row for `mergeTradeIds[1]`. Use `page.locator(`tr:has-text("${id}") input[type="checkbox"]`)`.
    Assert `page.getByRole('button', { name: 'Merge' })` becomes visible in the toolbar.
  - TC-081: With both checkboxes selected, click `page.getByRole('button', { name: 'Merge' })`. Assert
    `page.getByRole('heading', { name: 'Merge Trades' })` is visible. Assert
    `page.getByText('All execution legs will be moved to the oldest trade.')` is visible. Assert the
    combined qty section shows `page.getByText('Combined Qty')` is visible.
  - TC-082: In the open MergePreviewModal, click `page.getByRole('button', { name: 'Merge Trades' })`.
    Wait for the modal to close (`page.getByRole('heading', { name: 'Merge Trades' })` not visible).
    Assert the URL navigates to `/dashboard/trades/${mergeTradeIds[0]}` (survivor is the older trade).

- [x] 15.5 Add E2E tests for execution context menu actions in a new `describe('Execution Context Menu')`
  block. Navigate to `executionTradeId`. Wait for `table tbody tr` count ≥ 1.
  - TC-085: Click the overflow menu button in the first execution row:
    `page.locator('tbody tr').first().locator('button').last()`. Assert the dropdown appears with text
    `Edit`, `Move to...`, `Detach as new Trade`, `Delete` all visible.
  - TC-086: With the dropdown open, click `Detach as new Trade`. A `window.confirm` dialog will appear
    — handle it with `page.on('dialog', d => d.accept())` (set up before the click). Assert the
    execution table row count decreases by 1. Assert a `trade-detached` CustomEvent is dispatched (or
    simply assert that `table tbody tr` count equals the previous count minus 1 after a short wait).

- [x] 15.6 Search `trades.spec.ts` and all files in `frontend/tests/` for `PartialClose` and
  `TradeEditForm`. Delete any `describe` or `test` block referencing these. Confirm with
  `grep -r "PartialClose\|TradeEditForm" frontend/tests/` returning zero results.

- [x] 15.7 Update the `TC-051` test in `trades.spec.ts`. The current `expectedHeaders` array is:
  `['Symbol', 'Direction', 'Asset Class', 'Entry Price', 'Exit Price', 'PnL', 'Opened At', 'Closed At']`.
  Check the live table (navigate to `/dashboard/trades` and run `page.$$eval('thead th', els => els.map(e => e.textContent?.trim()))`)
  and compare. Add or remove headers to match what the current UI actually renders. The check must
  pass with `getByRole('columnheader', { name: header })` for each entry.

## 16. Linting & Regression Check

- [x] 16.1 Run `ruff check` + `ruff format` + `mypy --strict` on all new and modified backend files, fix any issues
- [x] 16.2 Run full backend test suite (`pytest`), fix any regressions in existing tests caused by the execution-layer changes
- [x] 16.3 Run frontend type check (`tsc --noEmit`) and fix any TypeScript errors in new/modified components

## 17. Alignment with `simplified-execution-model`

Tasks below are pending and must be completed after `simplified-execution-model` is applied. The data-model migration (`status` enum → `origin` + `deleted` + `user_modified`) invalidates several components implemented in sections 1–16.

- [x] 17.1 Update `ExecutionStatusBadge` component: replace `status`-based mapping with the derivation table from `simplified-execution-model/specs/execution-provenance/spec.md` (origin + deleted + user_modified → badge label + color). Tracked also in `simplified-execution-model` task 8.3.
- [x] 17.2 Update `ExecutionRow` context menu: add "Split" option (opens `SplitExecutionModal` from `simplified-execution-model` task 8.9) for non-deleted executions with `origin='imported'` or `origin='manual'`. Tracked also in `simplified-execution-model` task 8.9.
- [x] 17.3 Update `ExecutionLegsTable`: add "Show deleted" toggle and `[Restore]` button on deleted rows. Tracked also in `simplified-execution-model` tasks 8.4–8.5.
- [x] 17.4 Remove `has_conflict`-dependent UI: delete `ConflictBanner` component, remove conflict badge (⚠) from `TradeRow`, remove "Needs Review" system filter from sidebar and delete its seed data row. `has_conflict` is removed from the trade model in `simplified-execution-model` task 5.5. Tracked also in `simplified-execution-model` task 8.11.
- [x] 17.5 Remove `is_empty`-dependent UI: delete EMPTY badge from `TradeCard`, remove "Archive" tab from `TradeListTabs`, drop `include_empty`/`only_empty` params from trade list hook and filter form. Tracked also in `simplified-execution-model` task 8.10.
- [x] 17.6 Update backend service and repository call sites that pass `status='manual'` to pass `origin='manual'` (tasks 1.3 and 3.1 in this spec were implemented against the old model).
- [x] 17.7 Update TypeScript types: remove `status` field from `LogicalExecution` interface; add `origin`, `deleted`, `user_modified`, `parent_id`. Remove `has_conflict` and `is_empty` from the `Trade` interface. Tracked also in `simplified-execution-model` tasks 8.1–8.2.
- [x] 17.8 Update all backend and frontend tests that assert `status === 'manual'` or `status === 'imported'` (etc.) to assert `origin === 'manual'` / `origin === 'imported'`, and add assertions for `deleted` and `user_modified` where relevant.
- [x] 17.9 Run `ruff check`, `mypy --strict`, `pytest`, and `tsc --noEmit` — all must pass after the model migration.
