## 1. Backend — Schemas & Filter Parameters

- [x] 1.1 Add `TradeFilterParams` schema (Pydantic) with all filter query params: `symbol`, `direction`, `asset_class`, `tag_ids`, `tag_filter_mode`, `playbook_id`, `opened_at_from`, `opened_at_to`, `pnl_positive`
- [x] 1.2 Add `TradeSortParams` schema with `sort_by` (enum) and `sort_dir` (`asc`/`desc`, default `desc`)
- [x] 1.3 Add `BulkDeleteRequest` schema: `trade_ids` (list[UUID], min 1, max 100)
- [x] 1.4 Add `BulkAssignTagsRequest` schema: `trade_ids`, `tag_ids` (min 1), `mode` (`add`/`remove`)
- [x] 1.5 Add `BulkAssignPlaybookRequest` schema: `trade_ids`, `playbook_id` (UUID or null)
- [x] 1.6 Add `BulkActionResponse` schema: `updated_count` / `deleted_count`

## 2. Backend — Repository Extensions

- [x] 2.1 Extend `TradeRepository.list_cursor()` to accept filter + sort params; apply all WHERE clauses dynamically
- [x] 2.2 Implement AND tag filter using subquery: `WHERE id IN (SELECT trade_id FROM trade_tags WHERE tag_id = ANY(:ids) GROUP BY trade_id HAVING COUNT(DISTINCT tag_id) = :n)`
- [x] 2.3 Implement OR tag filter using JOIN on `trade_tags`
- [x] 2.4 Make cursor sort-aware: encode sort field value + id; use NULLS LAST for nullable fields
- [x] 2.5 Add `TradeRepository.bulk_delete(trade_ids, user_id)` — single query `WHERE id = ANY(:ids) AND user_id = :user_id`
- [x] 2.6 Add `TradeRepository.bulk_assign_tags(trade_ids, tag_ids, mode, user_id)` — batch insert/delete on `trade_tags`
- [x] 2.7 Add `TradeRepository.bulk_assign_playbook(trade_ids, playbook_id, user_id)` — batch UPDATE

## 3. Backend — Service Layer

- [x] 3.1 Update `TradeService.list_cursor()` signature to pass filter + sort params through to repository
- [x] 3.2 Add `TradeService.bulk_delete(trade_ids, user_id)` with ownership validation
- [x] 3.3 Add `TradeService.bulk_assign_tags(trade_ids, tag_ids, mode, user_id)` — validate tag ownership (403 if tag belongs to another user)
- [x] 3.4 Add `TradeService.bulk_assign_playbook(trade_ids, playbook_id, user_id)` — validate playbook ownership (403 if playbook belongs to another user)

## 4. Backend — API Routes

- [x] 4.1 Update `GET /api/v1/trades` route to accept `TradeFilterParams` + `TradeSortParams` as Query dependencies
- [x] 4.2 Register `POST /api/v1/trades/bulk/delete` route (BEFORE the create route) — calls `TradeService.bulk_delete`
- [x] 4.3 Register `POST /api/v1/trades/bulk/assign-tags` route — calls `TradeService.bulk_assign_tags`
- [x] 4.4 Register `POST /api/v1/trades/bulk/assign-playbook` route — calls `TradeService.bulk_assign_playbook`

## 5. OpenAPI Client Sync

- [x] 5.1 Start local backend (`deploy-local` skill) and regenerate TypeScript client from updated OpenAPI spec (`openapi-sync` skill)
- [x] 5.2 Verify new filter/sort params and bulk endpoints appear in generated client types

## 6. Frontend — Hooks

- [x] 6.1 Extend `useTrades` hook to accept all filter + sort params; include them in query key and API call
- [x] 6.2 Add `useBulkDeleteTrades` mutation hook — calls `POST /api/v1/trades/bulk/delete`, invalidates `["trades"]`
- [x] 6.3 Add `useBulkAssignTags` mutation hook — calls `POST /api/v1/trades/bulk/assign-tags`, invalidates `["trades"]`
- [x] 6.4 Add `useBulkAssignPlaybook` mutation hook — calls `POST /api/v1/trades/bulk/assign-playbook`, invalidates `["trades"]`

## 7. Frontend — Filter Bar Component

- [x] 7.1 Create `TradeFilterBar` component with: symbol text input (300ms debounce), direction dropdown, asset class dropdown
- [x] 7.2 Add tags multi-select to `TradeFilterBar` using `useTags()` hook; include AND/OR toggle button
- [x] 7.3 Add playbook dropdown to `TradeFilterBar` using `usePlaybooks()` hook
- [x] 7.4 Add opened-at date range inputs (two `<input type="date">`) to `TradeFilterBar`
- [x] 7.5 Add winner/loser toggle (3-state: all / winners / losers) to `TradeFilterBar`
- [x] 7.6 Add "Clear filters" button with active filter count badge; clicking resets all filters

## 8. Frontend — Sortable Table Headers

- [x] 8.1 Add `SortIcon` sub-component that shows ↕ (neutral), ↑ (asc), ↓ (desc) based on current sort state
- [x] 8.2 Update all column `<th>` elements in `TradeTable` to be clickable; pass `onSortChange` callback
- [x] 8.3 Implement sort toggle logic: click non-active column → sets it desc; click active column → toggles direction

## 9. Frontend — Row Checkboxes & Selection State

- [x] 9.1 Add checkbox column as first `<th>` / `<td>` in `TradeTable` and `TradeRow`
- [x] 9.2 Implement `selectedIds: Set<string>` state in the trades page; pass down selection handlers
- [x] 9.3 Implement select-all / indeterminate header checkbox logic
- [x] 9.4 Highlight selected rows with a subtle background color
- [x] 9.5 Clear selection when page/cursor changes

## 10. Frontend — Bulk Action Toolbar & Modals

- [x] 10.1 Create `TradeSelectionToolbar` component — shows count + action buttons; hidden when `selectedIds.size === 0`
- [x] 10.2 Create `ConfirmDeleteModal` — shows count of trades to delete; "Cancel" / "Delete N trades" buttons
- [x] 10.3 Create `BulkTagModal` — multi-select tag list with mode toggle (Add / Remove); confirm button
- [x] 10.4 Create `BulkPlaybookModal` — single-select playbook dropdown with "None (unassign)" option; confirm button
- [x] 10.5 Wire up all bulk mutations in `TradeSelectionToolbar`; clear selection and reload after success
- [x] 10.6 Show toast/error feedback on bulk action failure

## 11. Frontend — Trades Page Integration

- [x] 11.1 Update `trades/page.tsx` to host filter state (`useTradeFilters`), sort state, and selection state
- [x] 11.2 Pass filter + sort state to `TradeTable` (and via `useTrades` hook)
- [x] 11.3 Reset cursor to null whenever filter or sort state changes
- [x] 11.4 Render `TradeFilterBar` above the table and `TradeSelectionToolbar` between filter bar and table

## 12. Backend — Tests

- [x] 12.1 Unit tests for `TradeService.bulk_delete` — ownership check, partial matches
- [x] 12.2 Unit tests for `TradeService.bulk_assign_tags` — add mode, remove mode, tag ownership check
- [x] 12.3 Unit tests for `TradeService.bulk_assign_playbook` — assign, unassign, playbook ownership check
- [x] 12.4 Integration tests for `GET /api/v1/trades` — symbol filter, direction filter, tag AND/OR filter, date range, pnl_positive, sort by PnL/symbol
- [x] 12.5 Integration tests for `POST /api/v1/trades/bulk/delete`, `bulk/assign-tags`, `bulk/assign-playbook`

## 13. Code Review

- [x] 13.1 Run `lint-check` skill (ruff + mypy --strict) on backend changes; fix all issues
- [x] 13.2 Run `unit-test` skill; verify all new tests pass and coverage ≥ 80% for new service methods
- [x] 13.3 Launch `code-reviewer` agent for architecture, type safety, and security review
