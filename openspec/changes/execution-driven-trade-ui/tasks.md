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

## 10. Frontend: Trade Edit Form Refactor

- [ ] 10.1 Update `TradeEditForm` to accept an `executions` prop (or fetch them). When executions exist (length > 0): render Quantity, Entry Price, Exit Price, PnL, Commission, Opened At, Closed At as read-only inputs with `bg-secondary/50`, lock icon, and "Computed from executions" hint text
- [ ] 10.2 Add a "Edit individual executions in the Execution Legs section" link in the read-only fields section
- [ ] 10.3 Update `handleSubmit` to exclude computed fields from the `TradeUpdate` payload when executions exist
- [ ] 10.4 Verify the form still works fully editable for trades with zero executions (backward compat)

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

## 13. Testing & Cleanup

- [ ] 13.1 Write backend unit tests for `ExecutionService`: create, update, delete, re-aggregation correctness
- [ ] 13.2 Write backend unit tests for execution API endpoints: list, create, update, delete, authorization
- [ ] 13.3 Write backend unit tests for merge endpoint: happy path, validation failures, metadata preservation
- [ ] 13.4 Update or replace any existing `PartialCloseModal` frontend tests with `AddExecutionModal` tests
- [ ] 13.5 Run linting (`ruff check`, `ruff format`, `mypy --strict`) and fix any issues
- [ ] 13.6 Run full backend test suite and fix any regressions
