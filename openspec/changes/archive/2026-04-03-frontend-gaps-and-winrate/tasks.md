## 1. Backend: TradeRead playbook_name + TradeUpdate sentinel fix

- [x] 1.1 Add `playbook_name: str | None` computed field to `TradeRead` schema (resolve from joined playbook relationship)
- [x] 1.2 Update `TradesRepository.get_by_id()` and `get_all()` to eager-load `Trade.playbook` so the name is available
- [x] 1.3 Implement `UNSET` sentinel for `TradeUpdate` — introduce a typed `NotGiven` wrapper so `stop_loss` and `take_profit` can distinguish "not provided" from "set to null"
- [x] 1.4 Update `TradesService.update_trade()` to handle the sentinel: only update fields where the value is not `NotGiven`
- [x] 1.5 Update `TradeUpdate` schema fields `stop_loss`, `take_profit` to use the sentinel type annotation

## 2. Backend: Rolling winrate endpoint

- [x] 2.1 Add `RollingWinratePoint` Pydantic schema with fields `trade_index`, `closed_at`, `rolling_winrate`, `window`
- [x] 2.2 Implement `TimeSeriesService.get_rolling_winrate(user_id, window_trades, account_id, from_dt, to_dt)` using a Python sliding `deque`
- [x] 2.3 Add `GET /timeseries/rolling-winrate` route with query params `window_trades` (int, default 20, min 5, max 100), `account_id`, `from_dt`, `to_dt`
- [x] 2.4 Regenerate frontend OpenAPI TypeScript client after backend changes

## 3. Frontend: Account management page

- [x] 3.1 Create `app/dashboard/accounts/page.tsx` — list all accounts with name, broker, currency, active status
- [x] 3.2 Create `AccountForm.tsx` component (shared for create/edit): fields name (required), broker, currency (default USD), is_active toggle
- [x] 3.3 Add `useCreateAccount`, `useUpdateAccount`, `useDeleteAccount` mutation hooks
- [x] 3.4 Add delete confirmation dialog with warning about cascading trade deletion
- [x] 3.5 Add "Accounts" nav item to `dashboard/layout.tsx` sidebar

## 4. Frontend: Trade filtering and sorting

- [x] 4.1 Create `TradeFilterBar.tsx` component with inputs for symbol (text), direction (select), asset class (select), playbook (select), date range (from/to), tag (multi-select), winner/loser (select)
- [x] 4.2 Implement URL query param persistence using `useSearchParams` + `router.replace` in the trade list page
- [x] 4.3 Update `useTrades()` hook to accept and forward filter params to the API
- [x] 4.4 Mount `TradeFilterBar` above `TradeTable` in `app/dashboard/trades/page.tsx`
- [x] 4.5 Add sortable column headers to `TradeTable` (symbol, PnL, opened_at, closed_at) with sort indicator arrows
- [x] 4.6 Add "Clear filters" button that resets all filter state and URL params

## 5. Frontend: Trade create and edit

- [x] 5.1 Create shared `TradeForm.tsx` component with all trade fields (symbol, direction, asset_class, quantity, entry_price, exit_price, stop_loss, take_profit, opened_at, closed_at, pnl, commission, currency, account_id, playbook_id, tag_ids, notes)
- [x] 5.2 Create `app/dashboard/trades/new/page.tsx` — mounts `TradeForm` in create mode; on success navigate to new trade detail
- [x] 5.3 Create `app/dashboard/trades/[id]/edit/page.tsx` — fetches trade, mounts `TradeForm` pre-populated in edit mode
- [x] 5.4 Add `useCreateTrade` mutation hook calling `POST /trades`
- [x] 5.5 Add `useUpdateTrade` mutation hook calling `PATCH /trades/{id}`
- [x] 5.6 Add "New Trade" button on `app/dashboard/trades/page.tsx`
- [x] 5.7 Add "Edit" button on `app/dashboard/trades/[id]/page.tsx` linking to edit page
- [x] 5.8 Fix trade detail page: replace raw `playbook_id` UUID display with `playbook_name` from `TradeRead`
- [x] 5.9 Fix trade detail page: display `currency` and `pnl_eur` fields when present

## 6. Frontend: Bulk trade operations

- [x] 6.1 Add checkbox column to `TradeRow.tsx` and `TradeTable.tsx`; manage selected IDs in local `useState`
- [x] 6.2 Add "select all visible" header checkbox that toggles all current page rows
- [x] 6.3 Create `BulkActionBar.tsx` component — appears when selection is non-empty; shows count + action buttons
- [x] 6.4 Implement bulk delete action: confirmation dialog → call `DELETE /trades/bulk` → invalidate trade list query
- [x] 6.5 Implement bulk assign tag: tag picker popover → call `POST /trades/bulk/tags` → invalidate trade list query
- [x] 6.6 Implement bulk assign playbook: playbook picker popover → call `POST /trades/bulk/playbook` → invalidate trade list query
- [x] 6.7 Add `useBulkDelete`, `useBulkAssignTag`, `useBulkAssignPlaybook` mutation hooks

## 7. Frontend: Extended analytics charts

- [x] 7.1 Add `useMonthlyPnl` data hook calling `GET /timeseries/monthly-pnl`
- [x] 7.2 Create `MonthlyPnlChart.tsx` — Recharts `BarChart` with green/red bars, tooltip showing PnL, trade count, win rate
- [x] 7.3 Add `useReturnDistribution` data hook calling `GET /timeseries/return-distribution`
- [x] 7.4 Create `ReturnDistributionChart.tsx` — Recharts histogram with positive/negative bucket colouring and bucket range tooltip
- [x] 7.5 Add `usePnlByAssetClass` data hook calling `GET /timeseries/pnl-by-asset-class`
- [x] 7.6 Create `PnlByAssetClassChart.tsx` — Recharts `BarChart` with asset class on x-axis, tooltip with PnL/count/winrate
- [x] 7.7 Add "Analytics" section to `app/dashboard/page.tsx` below the daily PnL chart, mounting all three new charts

## 8. Frontend: Winrate development charts

- [x]  8.1 Add `useRollingWinrate(windowTrades)` data hook calling `GET /timeseries/rolling-winrate`
- [x]  8.2 Create `RollingWinrateChart.tsx` — Recharts `LineChart` with a dashed 50% reference line and window size selector (10/20/50)
- [x]  8.3 Add `useMonthlyWinrate` derived hook (reuse `useMonthlyPnl` data, extract `win_rate` per month)
- [x]  8.4 Create `MonthlyWinrateChart.tsx` — Recharts `BarChart` with 50% reference line and month/winrate/count tooltip
- [x] 8.5 Add "Win Rate Development" section to `app/dashboard/page.tsx` below the Analytics section, mounting both winrate charts side-by-side
