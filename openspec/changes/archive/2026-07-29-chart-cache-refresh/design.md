## Context

The Trade Sensei platform caches market data (OHLC price bars) in the backend to limit API calls to the Market Data Hub (LSEG). This cache is currently not easy to bypass or clear if a user notices stale or incorrect price bars. 

## Goals / Non-Goals

**Goals:**
- Provide a UI mechanism to clear the market data cache for all trades in the user's account.
- Provide a chart-specific refresh button to fetch the latest data for just one symbol/chart.
- Extend the backend API to support both operations cleanly.

**Non-Goals:**
- Do not implement a cron-based cache invalidation.
- Do not modify how data is fetched from MDH besides bypassing the local cache.

## Decisions

- **API Design for Chart Refresh:** Add a `force_refresh` boolean query param to `GET /prices/{symbol}/history`. This allows the frontend to easily fetch fresh data just by adding a parameter to the existing call. The backend will bypass checking the DB cache, fetch from the Hub, and overwrite the DB cache with the fresh data.
- **API Design for User-Scoped Cache Clear:** Add `DELETE /api/v1/market-data/cache`. It will query all distinct symbols traded by the authenticated user and execute a `DELETE FROM ohlc_prices WHERE symbol IN (...)`.
- **Frontend State Management:** The chart refresh button will be built directly in `TradeChart.tsx`. The account cache clear will be in the Settings Hub (`components/settings/SettingsHub.tsx` or similar), specifically in the Look & Feel tab.

## Risks / Trade-offs

- **Rate Limits on Hub:** Allowing users to force refresh could theoretically hit MDH rate limits if abused. Mitigation: This is a manual action behind a UI button, so abuse is unlikely. We will not add strict rate-limiting for now.
- **Cache clearing deletes data other users might need:** Since market data (prices) is shared, clearing the cache for symbols traded by user A might also delete the cache for user B who traded the same symbols. However, since the next fetch by user B will automatically refill the cache from the MDH, the impact is minimal and ensures fresh data for everyone.
