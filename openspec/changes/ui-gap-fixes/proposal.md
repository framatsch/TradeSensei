## Why

The backend API is feature-complete through Iteration 6, but the frontend only exposes a subset of that capability. Users currently cannot edit trades, filter the trade list, view extended analytics charts, or manage accounts from the UI, creating a significant gap between what the platform can do and what users can actually access.

## What Changes

- Add inline editing to the trade detail page (all fields, tag assignment, playbook assignment, clearing optional fields via sentinel pattern fix)
- Add filter and sort controls to the TradeTable (symbol, direction, asset class, date range, tags, playbook, PnL positive/negative)
- Wire existing backend endpoints to new frontend charts: monthly PnL bar chart, PnL by asset class, return distribution histogram
- Place the existing `PnlBySymbolChart` component on the dashboard
- Resolve playbook UUID to its display name on the trade detail page
- Add bulk-selection checkboxes to TradeTable with bulk-delete, bulk-assign-tags, and bulk-assign-playbook actions
- Add IBKR Flex Query tab to the ImportForm (query token + report ID fields, calls `/imports/flex`)
- Add a dedicated `/dashboard/accounts` page for creating, editing, and deleting broker accounts
- Fix `TradeUpdate` schema to support clearing `stop_loss` and `take_profit` to null via explicit sentinel / `None` handling

## Capabilities

### New Capabilities

- `trade-editing`: Inline edit form on the trade detail page covering all mutable fields, tag multi-select, playbook select, and nullable field clearing
- `trade-filtering`: Filter bar and sort controls on the trade list, persisted in URL query params
- `extended-analytics`: Monthly PnL, PnL by asset class, and return distribution charts on the dashboard
- `bulk-trade-ops`: Multi-select checkboxes on TradeTable with bulk delete, assign tags, and assign playbook
- `flex-query-import`: Flex Query tab in ImportForm that calls the existing `/imports/flex` backend endpoint
- `account-management`: Dedicated accounts page with create / edit / delete account forms

### Modified Capabilities

- `trade-detail-view`: Extends the existing read-only trade detail page to support editing (UI-level behavior change)

## Impact

- **Frontend** (primary): New pages (`/dashboard/accounts`), new components (filter bar, bulk action toolbar, flex query form, account form), updated pages (trade detail, dashboard, import)
- **Backend**: Minor — fix `TradeUpdate` nullable sentinel pattern in `app/schemas/trade.py`; no new endpoints required (all backend capabilities already exist)
- **API client**: No new endpoints; existing `/accounts`, `/trades`, `/tags`, `/playbooks`, `/timeseries/*`, `/imports/flex` endpoints are already generated in the TypeScript client
- **No breaking changes**
