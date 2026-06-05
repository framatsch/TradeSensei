## Why

Dashboard analytics and the Trades list currently offer no way to scope results by instrument symbol or asset class at the filter level. Traders who focus on specific instruments (e.g. only equities, only a handful of tickers) cannot narrow dashboard metrics without manually isolating accounts or playbooks — which are orthogonal dimensions. Adding symbol and asset-class filtering closes this gap and brings the Dashboard filter bar to parity with the granularity already available in the Trades list.

## What Changes

- **New `symbols` filter field** — include list of ticker symbols (prefix-match / wildcard), available in both the Trades filter and the Dashboard (`DashboardFilterConfig`).
- **New `excluded_symbols` filter field** — exclude list, available in both surfaces. Combines with `symbols` as AND-logic (include ∩ NOT exclude).
- **Asset class filter on Dashboard** — `asset_classes` multi-select already exists in `TradeFilters` but is absent from `DashboardFilterConfig`; add it there.
- **Tag-Input UI component** — reusable chip/tag input supporting include (neutral) and exclude (red) tags with `!`-prefix shortcut during typing. Includes a help icon tooltip explaining the syntax to users. Used on both filter bars.
- **Backend filter logic** — `ILIKE 'symbol%'` prefix-match query applied before trade aggregation in analytics and in the trades list query.
- **URL serialization** — `symbols` (comma-sep) and `excluded_symbols` (comma-sep, prefixed `!` in URL for readability) synced to URL params on both pages.
- **Saved Views compatibility** — new fields default to `null`; existing saved views remain valid without migration.

## Capabilities

### New Capabilities

- `symbol-filter`: Tag-input based include/exclude symbol filter with prefix-match semantics, used on both the Trades filter bar and the Dashboard filter bar.

### Modified Capabilities

- `filter-url-sync`: URL sync extended to cover `symbols` and `excluded_symbols` params on both `/dashboard/trades` and `/dashboard/workspace/*` routes.

## Impact

- **Backend**: `DashboardFilterConfig` Pydantic schema gains `symbols`, `excluded_symbols`, `asset_classes`. All analytics repository queries that accept this config must apply the new predicates before aggregation. Trades list query (`TradeFilters`) already has `symbol` (singular, exact) — extend to `symbols` (list, prefix-match) and add `excluded_symbols`.
- **Frontend**: New `SymbolTagInput` component. `WorkspaceFilterBar` and `TradeFilterBar` both rendered with the new fields. `WorkspaceFilterContext` and `useTradeFilterParams` extended for URL serialization.
- **OpenAPI client**: Regenerated after backend schema changes.
- **No DB migration required** — purely query-level filtering, no new columns.
