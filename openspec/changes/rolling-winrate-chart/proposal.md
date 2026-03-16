## Why

Traders need to track their consistency over time — not just overall win rate, but how it evolves week-over-week or month-over-month. Currently the platform offers no rolling winrate visualization, leaving a key behavioral-analysis metric missing from the dashboard.

## What Changes

- New backend endpoint `GET /timeseries/rolling-winrate` that returns a rolling N-period winrate time series (configurable window, default 20 trades)
- New backend endpoint `GET /timeseries/monthly-winrate` that returns per-calendar-month winrate aggregation
- New frontend chart component `RollingWinrateChart` (line chart, rolling window selector)
- New frontend chart component `MonthlyWinrateChart` (bar chart, month-by-month winrate %)
- Both charts integrated into the dashboard analytics section

## Capabilities

### New Capabilities

- `rolling-winrate`: Rolling N-trade winrate time series endpoint and frontend line chart with configurable window
- `monthly-winrate`: Per-month winrate aggregation endpoint and frontend bar chart

### Modified Capabilities

<!-- none -->

## Impact

- **Backend**: New service method in `timeseries` service + repository queries; new routes in `app/api/v1/timeseries.py`
- **Frontend**: 2 new Recharts components in `frontend/components/charts/`; integration into `frontend/app/dashboard/page.tsx` or analytics section; new hooks `useRollingWinrate` + `useMonthlyWinrate`
- **API Client**: OpenAPI client regeneration needed after endpoint additions
- **Database**: No schema changes; queries over existing `trades` table (`closed_at`, `pnl`)
