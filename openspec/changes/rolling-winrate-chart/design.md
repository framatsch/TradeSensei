## Context

The timeseries API (`/timeseries/*`) already provides daily PnL, monthly PnL, PnL by symbol, PnL by asset class, and return distribution. All endpoints follow the same pattern: `TimeseriesService` → `TimeseriesRepository` → SQL aggregation over the `trades` table. The frontend renders these with Recharts in the dashboard analytics section.

Win rate as a single aggregate metric exists in `/metrics/summary` but has no time dimension. Traders frequently ask "am I getting better or worse?" — a question only a rolling or monthly winrate time series can answer.

## Goals / Non-Goals

**Goals:**
- Add `GET /timeseries/rolling-winrate?window=20&account_id=...` returning a list of `{date, winrate, trade_count}` points (one per closed trade, each representing the last N-trade winrate)
- Add `GET /timeseries/monthly-winrate?account_id=...` returning `{month, winrate, win_count, loss_count}` per calendar month
- Two new Recharts charts in the frontend: `RollingWinrateChart` (line) and `MonthlyWinrateChart` (bar)
- New hooks `useRollingWinrate` and `useMonthlyWinrate` consuming the generated API client

**Non-Goals:**
- No database schema changes
- No rolling winrate by playbook or tag (out of scope for this change)
- No real-time updates (WebSocket / SSE)
- No changes to existing endpoints

## Decisions

### Window-based rolling calculation in SQL vs Python

**Decision**: Compute rolling winrate using SQL window functions (`AVG(CASE WHEN pnl > 0 THEN 1.0 ELSE 0.0 END) OVER (ORDER BY closed_at ROWS BETWEEN N-1 PRECEDING AND CURRENT ROW)`).

**Rationale**: Keeps computation in the DB, avoids loading full trade history into Python. TimescaleDB is PostgreSQL-compatible so all window functions are supported. Alternative (Python pandas rolling) would require fetching all trades, which is wasteful for large datasets.

### Single endpoint for both rolling and monthly winrate vs combined

**Decision**: Two separate endpoints (`/rolling-winrate` and `/monthly-winrate`).

**Rationale**: Different response shapes (trade-level points vs. month aggregates), different query patterns, different chart types. Combining would complicate both the schema and the query. Consistency with existing timeseries endpoints (each is its own route).

### Window size: query param vs user profile setting

**Decision**: Query parameter `window` (integer, 5–100, default 20).

**Rationale**: Profile settings add significant scope; a query param allows the frontend to offer a selector control without backend state. Consistent with how other analytics tools handle this.

## Risks / Trade-offs

- [Performance] SQL window function over a large trades table could be slow → The `trades` table is a TimescaleDB hypertable with `closed_at` index; queries filtered by `account_id` + date range should be fast. Add explicit `account_id` filtering.
- [Sparse data] Accounts with < N trades return fewer than expected points → This is correct behavior; document it in the API response; the chart handles partial data gracefully.
- [Frontend clutter] Adding 2 more charts increases dashboard density → Charts are added to the existing "Extended Analytics" collapsible section, not the primary view.
