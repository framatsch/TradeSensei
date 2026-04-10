## 1. Backend: Execution CRUD API

- [ ] 1.1 Create `app/schemas/execution.py` with `LogicalExecutionRead` (all fields from model), `LogicalExecutionCreate` (direction, quantity, price, commission, executed_at, pnl), and `LogicalExecutionUpdate` (all optional) Pydantic schemas
- [ ] 1.2 Create `app/repositories/execution.py` with `ExecutionRepository` — methods: `list_by_trade_id`, `get_by_id`, `create`, `update`, `delete`, `reassign_to_trade` (for merge)
- [ ] 1.3 Create `app/services/execution.py` with `ExecutionService` — methods: `list_for_trade`, `create_manual_execution` (creates with status=manual, triggers re-aggregation), `update_execution` (updates + re-aggregates), `delete_execution` (deletes + re-aggregates or deletes empty trade)
- [ ] 1.4 Create `app/api/v1/executions.py` router with endpoints: `GET /trades/{trade_id}/executions`, `POST /trades/{trade_id}/executions`, `PATCH /executions/{execution_id}`, `DELETE /executions/{execution_id}`
- [ ] 1.5 Register the execution router in `app/api/v1/router.py`
- [ ] 1.6 Add `has_conflict` field to `TradeRead` and `TradeFilterParams` schemas; add `has_conflict` filter to trade repository query builder

## 2. Backend: Trade Merge Endpoint

- [ ] 2.1 Add `MergeTradesRequest` schema to `app/schemas/trade.py` with `trade_ids: list[UUID]` (min_length=2, max_length=10)
- [ ] 2.2 Add `merge_trades` method to `TradeService` — validates same symbol/account/asset_class, reassigns all LogicalExecutions to the oldest trade, copies/appends metadata (notes, tags from non-survivors), deletes empty trades, re-aggregates survivor
- [ ] 2.3 Add `POST /api/v1/trades/merge` endpoint to `app/api/v1/trades.py` calling the merge service method
- [ ] 2.4 Write unit tests for merge service: happy path (2 trades), validation failures (different symbol, different account, <2 trades, >10 trades), metadata preservation
- [ ] 2.5 Add `reassign_execution` method to `ExecutionService` — validates same symbol/account between execution and target trade, updates `trade_id`, re-aggregates both source and target trades, deletes source trade if empty
- [ ] 2.6 Add `POST /api/v1/executions/{execution_id}/reassign` endpoint accepting `{"target_trade_id": "uuid"}` — calls `reassign_execution`, returns updated execution + affected trades
- [ ] 2.7 Add `detach_execution` method to `ExecutionService` — validates trade has >1 executions, creates a new Trade, reassigns execution to new trade, re-aggregates both trades
- [ ] 2.8 Add `POST /api/v1/executions/{execution_id}/detach` endpoint — calls `detach_execution`, returns the newly created trade
- [ ] 2.9 Write unit tests for reassign: happy path, symbol mismatch, account mismatch, source trade deleted when empty
- [ ] 2.10 Write unit tests for detach: happy path, cannot detach last execution, new trade is correctly aggregated

## 3. Backend: Auto-Create Execution on Manual Trade Creation

- [ ] 3.1 Modify `TradeService.create_trade` to auto-create a `LogicalExecution` with `status=manual` from the trade's entry fields (direction, quantity, entry_price, opened_at, commission) when the trade is created via the API (not via import)
- [ ] 3.2 Write unit test: creating a trade via `POST /api/v1/trades` results in both a Trade and a LogicalExecution record

## 4. Backend: Re-Aggregation Trigger

- [ ] 4.1 Extract a `re_aggregate_trade(trade_id)` utility in `ExecutionService` that re-computes trade fields (quantity, entry_price, exit_price, pnl, net_pnl, commission, opened_at, closed_at) from the trade's LogicalExecutions using VWAP logic
- [ ] 4.2 Ensure `re_aggregate_trade` also clears `has_conflict` when the position totals are consistent after the mutation
- [ ] 4.3 Call `re_aggregate_trade` from create, update, delete, and merge methods
- [ ] 4.4 Write integration test: add an execution, verify trade values are recomputed; delete an execution, verify trade values update; delete last execution, verify trade is deleted

## 5. Backend: Conflict Filter & System Filter

- [ ] 5.1 Add `has_conflict: bool | None` to `TradeFilterParams` and wire it into the repository query (WHERE clause)
- [ ] 5.2 Create an Alembic data migration (or seed script) to insert a system-level saved filter: `name="Needs Review"`, `scope=SYSTEM`, `definition={"has_conflict": true}`, `needs_review=false`
- [ ] 5.3 Write test: GET /trades?has_conflict=true returns only conflicted trades

## 6. Frontend: TypeScript Types & React Query Hooks

- [ ] 6.1 Add `ExecutionStatus`, `LogicalExecution`, `LogicalExecutionCreate`, `LogicalExecutionUpdate` types to `lib/types.ts`
- [ ] 6.2 Add `MergeTradesRequest` type to `lib/types.ts`
- [ ] 6.3 Add `has_conflict` boolean field to the `Trade` interface in `lib/types.ts`
- [ ] 6.4 Create `hooks/useExecutions.ts` with: `useTradeExecutions(tradeId)` (GET list), `useCreateExecution(tradeId)` (POST), `useUpdateExecution()` (PATCH), `useDeleteExecution()` (DELETE), `useReassignExecution()` (POST reassign), `useDetachExecution()` (POST detach) — all invalidating trade + execution caches on mutation
- [ ] 6.5 Create `hooks/useMergeTrades.ts` with `useMergeTrades()` mutation hook (POST /trades/merge) that invalidates the trades list cache
- [ ] 6.6 Add `ReassignExecutionRequest` type (`{ target_trade_id: string }`) to `lib/types.ts`

## 7. Frontend: Execution Legs Display Components

- [ ] 7.1 Create `components/trades/ExecutionStatusBadge.tsx` — small colored badge rendering `imported` (blue), `manual` (purple), `merged` (orange), `split` (cyan) following project badge conventions
- [ ] 7.2 Create `components/trades/ExecutionSummaryCard.tsx` — displays VWAP entry price, VWAP exit price, total quantity, total commission, stop loss, take profit. Shows "Computed" badge and "Values are computed from N execution legs" subtitle. Uses `bg-card rounded-xl border border-border` styling
- [ ] 7.3 Create `components/trades/ExecutionRow.tsx` — single execution row: date, side badge (BUY green / SELL red), qty, price, commission, P&L, status badge, overflow menu (⋮) with actions: "Edit", "Move to...", "Detach as new Trade", "Delete". Supports click-to-edit inline mode (price, qty, commission become inputs; Save/Cancel buttons appear)
- [ ] 7.4 Create `components/trades/ExecutionLegsTable.tsx` — fetches executions via `useTradeExecutions(tradeId)`, renders header row + `ExecutionRow` for each execution, "+ Add Execution" button in header. Collapsible section with collapse/expand toggle
- [ ] 7.5 Update `app/dashboard/trades/[id]/page.tsx`: replace the flat "Execution Details" grid with `ExecutionSummaryCard` + `ExecutionLegsTable`. Remove `PartialCloseModal` import and "Partial Close" button

## 8. Frontend: Chart Execution Markers

- [ ] 8.1 Refactor `TradeChart` marker logic to accept a `LogicalExecution[]` array (via props or `useTradeExecutions`) instead of using trade-level `opened_at`/`closed_at`
- [ ] 8.2 Group executions by snapped candle time and side (entry vs exit). For each candle: if one execution, render a single `arrowUp`/`arrowDown` with label `"+{qty} @ ${price}"`; if multiple same-side executions, merge into one marker with combined label `"+{qty1}+{qty2} @ ${price1}/${price2}"`
- [ ] 8.3 Render entry markers (arrowUp, belowBar, #00d2ff cyan) and exit markers (arrowDown, aboveBar, #f0abfc fuchsia) independently — a candle with both entries and exits gets two markers
- [ ] 8.4 Fallback: if no executions are loaded yet (loading state or legacy trade), fall back to the current single ENTRY/EXIT marker behavior using trade-level timestamps

## 9. Frontend: Add Execution Modal

- [ ] 9.1 Create `components/trades/AddExecutionModal.tsx` — modal with BUY/SELL segmented toggle, Quantity input, Price input, Executed At datetime-local input (defaults to now), Commission input (defaults to 0), optional P&L input. Cancel and "Add Execution" buttons. Full-width on mobile
- [ ] 9.2 Wire `AddExecutionModal` into `ExecutionLegsTable` — clicking "+ Add Execution" opens it, successful creation refreshes the table and summary card
- [ ] 9.3 Delete `components/trades/PartialCloseModal.tsx` and remove all imports/references from the codebase
- [ ] 9.4 Update `hooks/useTrade.ts` to remove the `usePartialCloseTrade` hook (or deprecate it)

## 10. Frontend: Inline Editing in Sidebar Cards + Remove Edit Form

- [ ] 10.1 Add inline-editable SL/TP to `PerformanceCard`: click on SL or TP value → transforms into number input with Save (✓) / Cancel (✕) buttons. Save calls `PATCH /api/v1/trades/{id}` with `{ stop_loss }` or `{ take_profit }`. Clearing sends `null`. Dependent metrics (Initial Risk, Planned RRR, Realized R) recalculate on save
- [ ] 10.2 Add inline-editable Playbook to `PlaybookPsychologyCard`: click playbook name → dropdown of all playbooks appears. Selecting auto-saves via `PATCH /api/v1/trades/{id}` with `{ playbook_id }`. "None" option clears the assignment
- [ ] 10.3 Add inline-editable Tags to `PlaybookPsychologyCard`: click tags area → tag picker with search appears. Toggling tags auto-saves via `PATCH /api/v1/trades/{id}` with updated `{ tag_ids }` array
- [ ] 10.4 Create `components/trades/CorrectTradeModal.tsx` — small modal for rare corrections: editable Symbol + Asset Class fields, read-only Direction + Currency, warning text ("These fields affect trade identity. Only change them to fix import errors."), sets `is_manually_edited: true` on save
- [ ] 10.5 Update Trade Detail header overflow menu (⋮): replace "Edit Trade" with "Correct Trade..." which opens the `CorrectTradeModal`
- [ ] 10.6 Remove `TradeEditForm` component and the `{isEditing ? <TradeEditForm/> : <NormalView/>}` toggle from `TradeDetailPage` — the page always renders the normal view
- [ ] 10.7 Delete `components/trades/TradeEditForm.tsx` and remove all imports/references from the codebase

## 11. Frontend: Conflict Resolution UI

- [ ] 11.1 Create `components/trades/ConflictBanner.tsx` — amber banner with warning icon, title "Position Conflict", explanation text, Dismiss button (session-only via useState), Help link. Uses `bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800`
- [ ] 11.2 Add `ConflictBanner` to `TradeDetailPage` — renders below the header when `trade.has_conflict === true`
- [ ] 11.3 Update `TradeRow` — add a small amber ⚠ icon next to the symbol when `has_conflict === true`
- [ ] 11.4 Add "Needs Review" to the sidebar trade filter list — display the system filter with a count badge showing number of conflicted trades. Wire click to apply the filter

## 12. Frontend: Trade Merge Workflow

- [ ] 12.1 Create `components/trades/MergePreviewModal.tsx` — displays source trade cards (symbol, qty, execution count, PnL each), arrow, merged result card (combined values). Warning text about irreversibility. Cancel and "Merge Trades" buttons. Calls `useMergeTrades` on confirm
- [ ] 12.2 Create `components/trades/TradePickerModal.tsx` — searchable list of trades filtered to same symbol/account. Checkboxes to select trades. Reused for both "Merge with..." and "Move to..." flows. "Continue"/"Select" button returns the selected trade(s)
- [ ] 12.3 Update `BulkActionToolbar` — add "Merge" button visible when 2+ selected trades share the same symbol. Clicking opens `MergePreviewModal` with selected trades
- [ ] 12.4 Update `TradeDetailPage` — add overflow menu (⋮) to header with "Edit Trade", "Merge with...", "Delete Trade" options. "Merge with..." opens `TradePickerModal`
- [ ] 12.5 Wire "Move to..." in `ExecutionRow` context menu: clicking opens `TradePickerModal` (single-select mode), on selection calls `useReassignExecution` with `{ target_trade_id }`, refreshes both source and target trade caches, shows success toast
- [ ] 12.6 Wire "Detach as new Trade" in `ExecutionRow` context menu: clicking shows confirmation dialog, on confirm calls `useDetachExecution`, refreshes execution table, shows success toast with link to newly created trade

## 13. Backend Tests: New Execution & Merge Tests

- [ ] 13.1 Create `tests/test_execution_service.py` — unit tests for `ExecutionService`: `create_manual_execution` (happy path, validation), `update_execution` (price change triggers re-aggregation), `delete_execution` (re-aggregates parent, deletes empty trade), `reassign_execution` (happy path, symbol mismatch, account mismatch, source trade deleted when empty), `detach_execution` (happy path, cannot detach last execution)
- [ ] 13.2 Create `tests/test_execution_api.py` — integration tests for execution endpoints: `GET /trades/{id}/executions` (list, empty, auth), `POST /trades/{id}/executions` (create manual, validation 422), `PATCH /executions/{id}` (update, auth), `DELETE /executions/{id}` (delete, last-execution cascade), `POST /executions/{id}/reassign` (happy path, validation), `POST /executions/{id}/detach` (happy path, single-execution rejection)
- [ ] 13.3 Create `tests/test_merge_trades.py` — integration tests for `POST /api/v1/trades/merge`: happy path (2 trades, 3 trades), validation failures (different symbol, different account, <2 trades, >10 trades), metadata preservation (notes appended, tags from oldest, playbook from oldest), re-aggregation correctness of survivor

## 14. Backend Tests: Consolidate Existing Tests

- [ ] 14.1 Update `tests/test_trades_partial_close.py` → replace the 4 `PartialClose` tests with execution-based equivalents: "adding a SELL execution to an open LONG trade reduces position", "adding SELL for full qty closes the trade", "invalid execution (qty=0) returns 422". Rename file to `tests/test_trades_execution_close.py`
- [ ] 14.2 Update `tests/test_aggregator.py` → replace `test_aggregate_partial_close` with execution-driven aggregation test: "re-aggregate from 2 BUY + 1 SELL execution computes correct VWAP entry, exit, PnL"
- [ ] 14.3 Update `tests/test_trade_service.py` → fix tests that break due to `create_trade` now auto-creating a `LogicalExecution`. Verify that `create_trade` response includes the auto-created execution. Add assertion that the execution has `status=manual`
- [ ] 14.4 Update `tests/test_trades_api.py` → add `has_conflict` field assertions to trade response tests. Add filter test: `GET /trades?has_conflict=true`
- [ ] 14.5 Update `tests/test_trade_schemas.py` → add tests for new schemas: `LogicalExecutionRead`, `LogicalExecutionCreate`, `LogicalExecutionUpdate`, `MergeTradesRequest` validation

## 15. Frontend Tests: Trade Detail E2E Consolidation

The existing `Trade Detail` describe block in `trades.spec.ts` has only one test (TC-060: "page renders without 404") with zero assertions on actual content. This must be expanded to cover the new execution-driven layout and serve as a proper regression suite.

- [ ] 15.1 Rewrite/expand the `Trade Detail` describe block in `trades.spec.ts` with the following tests:
  - TC-060 (update): Trade detail page renders trade header (symbol, direction badge, asset class badge, P&L, status OPEN/CLOSED)
  - TC-061: Execution Summary Card displays computed VWAP entry price, exit price, total quantity, total commission
  - TC-062: Execution Legs Table renders correct number of execution rows with date, side badge, qty, price, status badge
  - TC-063: Execution rows are sorted chronologically (oldest first)
  - TC-064: "Add Execution" button is visible in the execution legs section header
  - TC-065: Performance sidebar shows Gross P&L, Net P&L, Return %, Holding Period
  - TC-066: Overflow menu (⋮) on header contains "Merge with...", "Correct Trade...", "Delete Trade"
  - TC-067: Conflict banner is NOT shown for non-conflicting trades
- [ ] 15.2 Add E2E tests for Add Execution Modal flow:
  - TC-070: Clicking "+ Add Execution" opens the modal with BUY/SELL toggle, qty, price, date, commission fields
  - TC-071: Submitting valid execution data closes modal, new execution row appears in the table, summary card values update
  - TC-072: Submitting invalid data (qty=0) shows validation error, modal stays open
- [ ] 15.3 Add E2E tests for inline sidebar editing:
  - TC-075: Clicking SL value in Performance Card transforms it into an editable input, saving updates the value
  - TC-076: Clicking playbook name in Playbook Card opens dropdown, selecting a playbook auto-saves
  - TC-077: Clicking tags area in Playbook Card opens tag picker, toggling a tag auto-saves
- [ ] 15.4 Add E2E tests for Merge workflow:
  - TC-080: Selecting 2+ same-symbol trades in the list shows "Merge" button in toolbar
  - TC-081: Clicking "Merge" opens preview modal showing source trades and combined result
  - TC-082: Confirming merge navigates to the merged trade, trade list is refreshed
- [ ] 15.5 Add E2E test for execution context menu actions:
  - TC-085: Overflow menu (⋮) on execution row shows "Edit", "Move to...", "Detach as new Trade", "Delete"
  - TC-086: "Detach as new Trade" removes execution from current trade and shows success toast with link
- [ ] 15.6 Delete any existing `PartialCloseModal` and `TradeEditForm` test files or test blocks, verify no references remain in the test suite
- [ ] 15.7 Update Trade List tests (TC-051) to include `Qty` and `Broker` column headers if the table structure changed

## 16. Linting & Regression Check

- [ ] 16.1 Run `ruff check` + `ruff format` + `mypy --strict` on all new and modified backend files, fix any issues
- [ ] 16.2 Run full backend test suite (`pytest`), fix any regressions in existing tests caused by the execution-layer changes
- [ ] 16.3 Run frontend type check (`tsc --noEmit`) and fix any TypeScript errors in new/modified components
