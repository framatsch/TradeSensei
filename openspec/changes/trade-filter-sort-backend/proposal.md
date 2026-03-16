## Why

The `GET /trades` endpoint currently only supports cursor-based pagination; all filtering and sorting is done client-side in the frontend. As accounts grow beyond a few hundred trades, this becomes unusable — the frontend fetches all pages just to filter by symbol or date range. Server-side filtering and sorting are table-stakes features for any data-heavy application.

## What Changes

- `GET /trades` is extended with optional filter query parameters: `symbol`, `asset_class`, `side`, `account_id`, `playbook_id`, `tag_id`, `from_date`, `to_date`, `min_pnl`, `max_pnl`
- `GET /trades` is extended with sort parameters: `sort_by` (field name) and `sort_dir` (`asc`/`desc`)
- All filter/sort params are optional; existing behavior is unchanged when omitted
- Frontend `TradeFilterBar` and `useTrades` hook are updated to pass these params to the API

## Capabilities

### New Capabilities

- `trade-server-side-filter`: Server-side filtering on `GET /trades` by symbol, asset class, side, account, playbook, tag, date range, PnL range
- `trade-server-side-sort`: Server-side sorting on `GET /trades` by configurable field and direction

### Modified Capabilities

<!-- none — the GET /trades endpoint is extended, not changed in behavior for existing callers -->

## Impact

- **Backend**: `TradeRepository.list_cursor` extended with filter+sort params; `TradeService.list_trades` signature updated; new `TradeFilterParams` and `TradeSortParams` Pydantic models; route handler updated
- **Frontend**: `useTrades` hook updated to pass filter/sort state to API; `TradeFilterBar` component connects to sort controls
- **API Client**: OpenAPI client regeneration needed
- **Database**: Existing indexes on `closed_at` are sufficient for date-range filtering; a composite index on `(user_id, symbol)` and `(user_id, asset_class)` may be beneficial — add as explicit migrations if needed
- **Breaking**: None — all new params are optional
