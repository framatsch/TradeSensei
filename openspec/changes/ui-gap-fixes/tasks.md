## 1. Backend — Fix TradeUpdate Nullable Sentinel

- [x] 1.1 Update `app/schemas/trade.py` `TradeUpdate` to distinguish `null` (clear field) from omitted (leave unchanged) using `model_fields_set` in a `model_validator`
- [x] 1.2 Update `app/services/trade_service.py` `update_trade` to apply `null` values as `None` to the ORM object when `stop_loss` / `take_profit` appear in `model_fields_set`
- [x] 1.3 Add a unit test in `tests/unit/test_trade_service.py` verifying that sending `stop_loss: null` clears the field and omitting it leaves it unchanged

## 2. Frontend — Trade Detail: Playbook Name Resolution

- [x] 2.1 In `app/dashboard/trades/[id]/page.tsx`, fetch `/playbooks` (or use the existing `usePlaybooks` hook) and resolve `trade.playbook_id` to its `name` for display
- [x] 2.2 Replace the raw UUID display with the resolved name (fallback to "—" if no playbook assigned)

## 3. Frontend — Trade Editing UI

- [x] 3.1 Create `components/trades/TradeEditForm.tsx` — controlled form with all mutable trade fields (symbol, direction, asset class, quantity, entry price, exit price, stop loss + clear, take profit + clear, opened_at, closed_at, commission, currency, PnL override)
- [x] 3.2 Add tag multi-select to `TradeEditForm` using existing `useTags` hook and `TagBadge` component
- [x] 3.3 Add playbook single-select to `TradeEditForm` (with "None" option to clear) using existing `usePlaybooks` hook
- [x] 3.4 Add `useUpdateTrade` mutation hook in `hooks/useTrade.ts` (or extend existing) that calls `PATCH /trades/{id}` and invalidates the trade cache
- [x] 3.5 Wire the "Edit" / "Save" / "Cancel" toggle into `app/dashboard/trades/[id]/page.tsx` — toggles between read-only view and `TradeEditForm`
- [x] 3.6 Add inline validation to `TradeEditForm` (negative prices, missing required fields)

## 4. Frontend — Trade List Filtering & Sorting

- [x] 4.1 Create `components/trades/TradeFilterBar.tsx` — collapsible panel with controls for symbol (text), direction (select), asset class (multi-select), date range (from/to), tag (multi-select), playbook (select), and PnL sign (radio)
- [x] 4.2 Implement URL query param sync in `app/dashboard/trades/page.tsx` using `useSearchParams` / `useRouter` — read initial filter state from URL, write changes back on filter change
- [x] 4.3 Update `hooks/useTrades.ts` to accept a filter object and include all filter params in the React Query key and API call
- [x] 4.4 Add active-filter count badge to the filter toggle button in `TradeFilterBar`
- [x] 4.5 Add sortable column headers to `TradeTable` for `opened_at`, `closed_at`, `symbol`, `pnl`, `commission` — clicking toggles asc/desc; show sort indicator arrow; persist sort in URL params

## 5. Frontend — Bulk Trade Operations

- [x] 5.1 Add a checkbox column to `TradeTable` (header select-all + per-row checkbox), managing selected IDs in local `useState`
- [x] 5.2 Create `components/trades/BulkActionToolbar.tsx` — appears when selection is non-empty; shows count + "Delete", "Assign Tag", "Assign Playbook" buttons
- [x] 5.3 Implement bulk delete: confirmation dialog → `DELETE /trades/bulk` → clear selection + refetch
- [x] 5.4 Implement bulk assign tag: tag picker popover → `PATCH /trades/bulk/tags` → refetch
- [x] 5.5 Implement bulk assign playbook: playbook picker popover → `PATCH /trades/bulk/playbook` → refetch
- [x] 5.6 Add `useBulkDeleteTrades`, `useBulkAssignTag`, `useBulkAssignPlaybook` mutation hooks in `hooks/useTrades.ts`

## 6. Frontend — Extended Analytics Charts

- [x] 6.1 Create `components/charts/MonthlyPnlChart.tsx` — Recharts BarChart consuming `/timeseries/monthly-pnl`; green/red bars; empty state placeholder
- [x] 6.2 Create `hooks/useMonthlyPnl.ts` React Query hook for `/timeseries/monthly-pnl`
- [x] 6.3 Create `components/charts/PnlByAssetClassChart.tsx` — Recharts BarChart (or PieChart) consuming `/timeseries/pnl-by-asset-class`
- [x] 6.4 Create `hooks/usePnlByAssetClass.ts` React Query hook
- [x] 6.5 Create `components/charts/ReturnDistributionChart.tsx` — Recharts BarChart histogram consuming `/timeseries/return-distribution`
- [x] 6.6 Create `hooks/useReturnDistribution.ts` React Query hook
- [x] 6.7 Add `MonthlyPnlChart`, `PnlBySymbolChart` (already exists), `PnlByAssetClassChart`, and `ReturnDistributionChart` to `app/dashboard/page.tsx` in a second analytics row below the existing equity/drawdown charts

## 7. Frontend — Flex Query Import Tab

- [x] 7.1 Refactor `components/imports/ImportForm.tsx` into a tabbed layout: "File Upload" tab (existing) + "Flex Query" tab
- [x] 7.2 Create `components/imports/FlexQueryForm.tsx` — form fields for Query ID, Token, account selector; calls `POST /imports/flex`
- [x] 7.3 Add `useFlexImport` mutation hook in a new or existing imports hooks file
- [x] 7.4 Display import result summary (trades imported count) on success; display backend error message on failure

## 8. Frontend — Account Management Page

- [x] 8.1 Create `app/dashboard/accounts/page.tsx` — lists all accounts with name, broker, currency, description columns; "New Account" button; empty state
- [x] 8.2 Create `components/accounts/AccountList.tsx` — table with edit/delete actions per row
- [x] 8.3 Create `components/accounts/AccountForm.tsx` — create/edit form with fields: name (required), broker (required), currency (required, default USD), description (optional)
- [x] 8.4 Add create account mutation (`POST /accounts`), update mutation (`PATCH /accounts/{id}`), and delete mutation (`DELETE /accounts/{id}`) to a new `hooks/useAccounts.ts` (or extend existing)
- [x] 8.5 Wire inline edit toggle and delete confirmation dialog into `AccountList`
- [x] 8.6 Add "Accounts" link to the sidebar navigation in `app/dashboard/layout.tsx`
