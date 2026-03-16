## Why

The trades table currently shows a flat, unfiltered list with no way to narrow down trades by symbol, direction, tags, playbook, date range, or outcome — making it difficult to analyze subsets of trades. There is also no way to sort by any column, nor to perform bulk operations (delete, tag assignment, playbook assignment) across multiple trades at once.

## What Changes

- **Filter bar** above the trades table with: symbol text search, direction (LONG/SHORT), asset class, tags (multi-select with AND/OR toggle), playbook, opened-at date range, and winner/loser toggle
- **Sortable columns**: every column in the trade table becomes clickable to sort ascending/descending; changing sort resets pagination to page 1
- **Row checkboxes** with select-all / indeterminate state for multi-selection
- **Bulk action toolbar** that appears when ≥1 trade is selected: bulk delete, bulk add tags, bulk remove tags, bulk assign playbook
- **Backend filter + sort parameters** added to `GET /api/v1/trades`
- **Three new bulk endpoints**: `POST /api/v1/trades/bulk-delete`, `POST /api/v1/trades/bulk-assign-tags`, `POST /api/v1/trades/bulk-assign-playbook`

## Capabilities

### New Capabilities

- `trade-filtering`: Filter the trade list by symbol, direction, asset class, tags (with AND/OR mode), playbook, opened-at date range, and PnL sign (winner/loser)
- `trade-sorting`: Sort the trade list by any column (symbol, direction, asset class, entry price, exit price, PnL, opened at, closed at); sort direction toggle; changing sort resets to page 1
- `trade-bulk-actions`: Multi-select trades via checkboxes; bulk delete with confirmation; bulk add/remove tags (additive mode); bulk assign/unassign playbook

### Modified Capabilities

<!-- No existing specs to modify -->

## Impact

- **Backend**: `app/api/trades.py` (new query params, 3 new routes), `app/schemas/trade.py` (new request/response schemas for bulk + filter), `app/services/trade_service.py` (3 new bulk methods), `app/repositories/trade_repository.py` (extended `list_cursor`, 3 new batch methods)
- **Frontend**: `hooks/useTrades.ts` (extended params), new hooks `useBulkDeleteTrades`, `useBulkAssignTags`, `useBulkAssignPlaybook`; new components `TradeFilterBar`, `TradeSelectionToolbar`, `BulkTagModal`, `BulkPlaybookModal`, `ConfirmDeleteModal`; updated `TradeTable` and `TradeRow`
- **OpenAPI client**: Must be regenerated after backend changes
- **No breaking changes** to existing API consumers — all new parameters are optional with backward-compatible defaults
