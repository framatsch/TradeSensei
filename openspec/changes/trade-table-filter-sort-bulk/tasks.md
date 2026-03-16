## 1. Backend — Schemas & Filter Parameters

- [ ] 1.1 Add `TradeFilterParams` schema (Pydantic) with all filter query params: `symbol`, `direction`, `asset_class`, `tag_ids`, `tag_filter_mode`, `playbook_id`, `opened_at_from`, `opened_at_to`, `pnl_positive`
- [ ] 1.2 Add `TradeSortParams` schema with `sort_by` (enum) and `sort_dir` (`asc`/`desc`, default `desc`)
- [ ] 1.3 Add `BulkDeleteRequest` schema: `trade_ids` (list[UUID], min 1, max 100)
- [ ] 1.4 Add `BulkAssignTagsRequest` schema: `trade_ids`, `tag_ids` (min 1), `mode` (`add`/`remove`)
- [ ] 1.5 Add `BulkAssignPlaybookRequest` schema: `trade_ids`, `playbook_id` (UUID or null)
- [ ] 1.6 Add `BulkActionResponse` schema: `updated_count` / `deleted_count`

## 2. Backend — Repository Extensions

- [ ] 2.1 Extend `TradeRepository.list_cursor()` to accept filter + sort params; apply all WHERE clauses dynamically
- [ ] 2.2 Implement AND tag filter using subquery: `WHERE id IN (SELECT trade_id FROM trade_tags WHERE tag_id = ANY(:ids) GROUP BY trade_id HAVING COUNT(DISTINCT tag_id) = :n)`
- [ ] 2.3 Implement OR tag filter using JOIN on `trade_tags`
- [ ] 2.4 Make cursor sort-aware: encode sort field value + id; use NULLS LAST for nullable fields
- [ ] 2.5 Add `TradeRepository.bulk_delete(trade_ids, user_id)` — single query `WHERE id = ANY(:ids) AND user_id = :user_id`
- [ ] 2.6 Add `TradeRepository.bulk_assign_tags(trade_ids, tag_ids, mode, user_id)` — batch insert/delete on `trade_tags`
- [ ] 2.7 Add `TradeRepository.bulk_assign_playbook(trade_ids, playbook_id, user_id)` — batch UPDATE

## 3. Backend — Service Layer

- [ ] 3.1 Update `TradeService.list_cursor()` signature to pass filter + sort params through to repository
- [ ] 3.2 Add `TradeService.bulk_delete(trade_ids, user_id)` with ownership validation
- [ ] 3.3 Add `TradeService.bulk_assign_tags(trade_ids, tag_ids, mode, user_id)` — validate tag ownership (403 if tag belongs to another user)
- [ ] 3.4 Add `TradeService.bulk_assign_playbook(trade_ids, playbook_id, user_id)` — validate playbook ownership (403 if playbook belongs to another user)

## 4. Backend — API Routes

- [ ] 4.1 Update `GET /api/v1/trades` route to accept `TradeFilterParams` + `TradeSortParams` as Query dependencies
- [ ] 4.2 Register `POST /api/v1/trades/bulk/delete` route (BEFORE the create route) — calls `TradeService.bulk_delete`
- [ ] 4.3 Register `POST /api/v1/trades/bulk/assign-tags` route — calls `TradeService.bulk_assign_tags`
- [ ] 4.4 Register `POST /api/v1/trades/bulk/assign-playbook` route — calls `TradeService.bulk_assign_playbook`

## 5. OpenAPI Client Sync

- [ ] 5.1 Start local backend (`deploy-local` skill) and regenerate TypeScript client from updated OpenAPI spec (`openapi-sync` skill)
- [ ] 5.2 Verify new filter/sort params and bulk endpoints appear in generated client types

## 6. Frontend — Hooks

- [ ] 6.1 Extend `useTrades` hook to accept all filter + sort params; include them in query key and API call
- [ ] 6.2 Add `useBulkDeleteTrades` mutation hook — calls `POST /api/v1/trades/bulk/delete`, invalidates `["trades"]`
- [ ] 6.3 Add `useBulkAssignTags` mutation hook — calls `POST /api/v1/trades/bulk/assign-tags`, invalidates `["trades"]`
- [ ] 6.4 Add `useBulkAssignPlaybook` mutation hook — calls `POST /api/v1/trades/bulk/assign-playbook`, invalidates `["trades"]`

## 7. Frontend — Filter Bar Component

- [ ] 7.1 Create `TradeFilterBar` component with: symbol text input (300ms debounce), direction dropdown, asset class dropdown
- [ ] 7.2 Add tags multi-select to `TradeFilterBar` using `useTags()` hook; include AND/OR toggle button
- [ ] 7.3 Add playbook dropdown to `TradeFilterBar` using `usePlaybooks()` hook
- [ ] 7.4 Add opened-at date range inputs (two `<input type="date">`) to `TradeFilterBar`
- [ ] 7.5 Add winner/loser toggle (3-state: all / winners / losers) to `TradeFilterBar`
- [ ] 7.6 Add "Clear filters" button with active filter count badge; clicking resets all filters

## 8. Frontend — Sortable Table Headers

- [ ] 8.1 Add `SortIcon` sub-component that shows ↕ (neutral), ↑ (asc), ↓ (desc) based on current sort state
- [ ] 8.2 Update all column `<th>` elements in `TradeTable` to be clickable; pass `onSortChange` callback
- [ ] 8.3 Implement sort toggle logic: click non-active column → sets it desc; click active column → toggles direction

## 9. Frontend — Row Checkboxes & Selection State

- [ ] 9.1 Add checkbox column as first `<th>` / `<td>` in `TradeTable` and `TradeRow`
- [ ] 9.2 Implement `selectedIds: Set<string>` state in the trades page; pass down selection handlers
- [ ] 9.3 Implement select-all / indeterminate header checkbox logic
- [ ] 9.4 Highlight selected rows with a subtle background color
- [ ] 9.5 Clear selection when page/cursor changes

## 10. Frontend — Bulk Action Toolbar & Modals

- [ ] 10.1 Create `TradeSelectionToolbar` component — shows count + action buttons; hidden when `selectedIds.size === 0`
- [ ] 10.2 Create `ConfirmDeleteModal` — shows count of trades to delete; "Cancel" / "Delete N trades" buttons
- [ ] 10.3 Create `BulkTagModal` — multi-select tag list with mode toggle (Add / Remove); confirm button
- [ ] 10.4 Create `BulkPlaybookModal` — single-select playbook dropdown with "None (unassign)" option; confirm button
- [ ] 10.5 Wire up all bulk mutations in `TradeSelectionToolbar`; clear selection and reload after success
- [ ] 10.6 Show toast/error feedback on bulk action failure

## 11. Frontend — Trades Page Integration

- [ ] 11.1 Update `trades/page.tsx` to host filter state (`useTradeFilters`), sort state, and selection state
- [ ] 11.2 Pass filter + sort state to `TradeTable` (and via `useTrades` hook)
- [ ] 11.3 Reset cursor to null whenever filter or sort state changes
- [ ] 11.4 Render `TradeFilterBar` above the table and `TradeSelectionToolbar` between filter bar and table

## 12. Backend — Tests

- [ ] 12.1 Unit tests for `TradeService.bulk_delete` — ownership check, partial matches
- [ ] 12.2 Unit tests for `TradeService.bulk_assign_tags` — add mode, remove mode, tag ownership check
- [ ] 12.3 Unit tests for `TradeService.bulk_assign_playbook` — assign, unassign, playbook ownership check
- [ ] 12.4 Integration tests for `GET /api/v1/trades` — symbol filter, direction filter, tag AND/OR filter, date range, pnl_positive, sort by PnL/symbol
- [ ] 12.5 Integration tests for `POST /api/v1/trades/bulk/delete`, `bulk/assign-tags`, `bulk/assign-playbook`

## 13. Code Review

- [ ] 13.1 Run `lint-check` skill (ruff + mypy --strict) on backend changes; fix all issues
- [ ] 13.2 Run `unit-test` skill; verify all new tests pass and coverage ≥ 80% for new service methods
- [ ] 13.3 Launch `code-reviewer` agent for architecture, type safety, and security review
