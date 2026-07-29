## Why

Users sometimes need to force a refresh of the market data if the cached data is incorrect or stale. They also need a way to clear the candle cache for all trades in their account directly from their settings if they encounter widespread market data caching issues.

## Goals

- Provide a UI mechanism to clear the global market data cache (this affects all users, deleting the cached prices for the symbols the current user trades).
- Provide a chart-specific refresh button to fetch the latest data for just one symbol/chart.
- Extend the backend API to support both operations cleanly.
- Accept the tradeoff that this clears data cache from all users (due to global cache design).

## Non-Goals

- Do not implement a cron-based cache invalidation.
- Do not modify how data is fetched from MDH besides bypassing the local cache.
- Do not build an admin UI for this feature.
- Do not implement targeted filtering or selective deletion logic for the bulk clear.

## What Changes

- Add a "Refresh" icon button in the `TradeChart` component adjacent to the "Options" button to reload chart data by bypassing the cache (`force_refresh=true`).
- Add a new API endpoint `DELETE /api/v1/market-data/cache` to clear cached OHLC prices for all symbols traded by the current user.
- Add a "Clear chart candles cache" button in the Settings Hub (Look & Feel tab) that triggers the user-scoped cache clear after a confirmation dialog.

## Capabilities

### New Capabilities
- `chart-cache-refresh`: Defines the ability to forcefully bypass and clear the market data cache.

### Modified Capabilities
- `chart-display-settings`: Modifies the Look & Feel tab in the settings to include the new "Clear chart candles cache" option.

## Impact

- **Frontend**: Modifications to `TradeChart.tsx` and the Look & Feel settings tab components.
- **Backend**: Modifications to the `GET /api/v1/market-data/prices/{symbol}/history` endpoint to support the `force_refresh` query param, and a new endpoint `DELETE /api/v1/market-data/cache`.
- **Database**: No schema changes, but cache clearing deletes rows in the `ohlc_prices` table matching the symbols traded by the current user.
