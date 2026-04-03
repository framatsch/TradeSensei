## Why

The backend already exposes a rich set of endpoints (monthly PnL, return distribution,
PnL by asset class, rolling winrate, accounts CRUD, bulk trade operations, trade
filtering) that have no corresponding UI. Users currently cannot manage their broker
accounts in the app, cannot filter or edit trades, and have no visibility into their
win-rate progression over time. These gaps make the journal significantly less usable
than it should be given the backend work already done.

## What Changes

- Add a `/dashboard/accounts` page for creating, editing, and deleting broker accounts
- Add filter bar and sortable columns to the trade list
- Add a trade create form and a trade edit form (inline on the detail page)
- Fix the trade detail page: show playbook name instead of raw UUID, show `currency`
  and `pnl_eur` fields
- Fix the `TradeUpdate` nullable sentinel bug for `stop_loss` and `take_profit`
- Add bulk-selection UI to the trade table (bulk delete, assign tag, assign playbook)
- Add three missing analytics charts to the dashboard: Monthly PnL, Return Distribution,
  PnL by Asset Class
- Add a Winrate Development section: rolling winrate over last N trades + monthly winrate
- Add `GET /timeseries/rolling-winrate` backend endpoint

## Capabilities

### New Capabilities

- `account-management`: Full CRUD UI for broker accounts at `/dashboard/accounts`
- `trade-filtering`: Filter bar and sort controls on the trade list; URL-persisted state
- `trade-editing`: Create and edit trades via a shared form component; fix detail page display
- `bulk-trade-ops`: Multi-select in trade table with bulk delete, assign tag, assign playbook
- `extended-analytics`: Monthly PnL chart, Return Distribution histogram, PnL by Asset Class chart on the dashboard
- `winrate-development`: Rolling winrate chart (last N trades) and monthly winrate chart; new backend endpoint

### Modified Capabilities

<!-- No existing spec-level requirements are changing -->

## Impact

**Backend:**
- New endpoint `GET /timeseries/rolling-winrate` (rolling window over N trades)
- Bug fix: `TradeUpdate` sentinel pattern for nullable `stop_loss` / `take_profit`
- `TradeRead` schema: add `playbook_name: str | None` resolved field (avoids extra frontend fetch)

**Frontend:**
- New page: `/dashboard/accounts`
- New page/modal: trade create (`/dashboard/trades/new` or modal)
- Modified page: `/dashboard/trades` — filter bar, sort headers, bulk-select column
- Modified page: `/dashboard/trades/[id]` — edit button, playbook name, currency/pnl_eur
- Modified page: `/dashboard/dashboard` — three new chart components + winrate section
- New components: `TradeForm`, `TradeFilterBar`, `BulkActionBar`, `MonthlyPnlChart`,
  `ReturnDistributionChart`, `PnlByAssetClassChart`, `RollingWinrateChart`
- New hooks: `useMonthlyPnl`, `useReturnDistribution`, `usePnlByAssetClass`,
  `useRollingWinrate`, `useCreateTrade`, `useUpdateTrade`, `useBulkDelete`,
  `useBulkAssignTag`, `useBulkAssignPlaybook`
- OpenAPI client regeneration required after backend changes

**No breaking changes to existing API contracts.**
