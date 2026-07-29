## ADDED Requirements

### Requirement: Global Cache Clear Endpoint
The backend SHALL expose a new endpoint `DELETE /api/v1/market-data/cache` that clears all entries in the global `ohlc_prices` table.
The endpoint SHALL return a `204 No Content` upon successful deletion.
*Note: The UI button for this endpoint SHALL display a "Danger" warning indicating that it clears all data cache from all users across the entire platform.*

#### Scenario: Global cache clear deletes all cached prices
- **WHEN** an authenticated user calls `DELETE /api/v1/market-data/cache`
- **THEN** all rows in the `ohlc_prices` table are deleted for all users, and a success response is returned

### Requirement: Chart-Level Force Refresh
The `GET /api/v1/market-data/prices/{symbol}/history` endpoint SHALL accept an optional boolean query parameter `force_refresh` (default `false`).
If `force_refresh=true`, the backend SHALL bypass the local database cache, fetch directly from the upstream Market Data Hub, and overwrite the existing cache entries for that request.

#### Scenario: Fetch with force_refresh bypasses cache
- **WHEN** `GET /api/v1/market-data/prices/AAPL/history?force_refresh=true` is called
- **THEN** the backend skips checking the `ohlc_prices` cache, fetches data from the upstream Hub, updates the cache, and returns the data.

### Requirement: Chart Component Refresh Icon
The `TradeChart` component SHALL display a "Refresh" icon button placed adjacent to the existing "Options" button.
When clicked, the button SHALL trigger a reload of the chart data by calling the market data endpoint with `force_refresh=true`.

#### Scenario: User clicks refresh on a chart
- **WHEN** the user clicks the "Refresh" icon next to the "Options" button on a trade chart
- **THEN** the chart enters a loading state, calls the market data endpoint with `force_refresh=true`, and re-renders with the fresh data
