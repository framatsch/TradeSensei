## 1. Backend Schemas

- [ ] 1.1 Add `RollingWinratePoint` Pydantic schema (`date`, `winrate: float`, `trade_count: int`) to `backend/app/schemas/timeseries.py`
- [ ] 1.2 Add `MonthlyWinratePoint` Pydantic schema (`month: str`, `winrate: float`, `win_count: int`, `loss_count: int`) to `backend/app/schemas/timeseries.py`
- [ ] 1.3 Add constant `ROLLING_WINRATE_MAX_POINTS = 500` to `backend/app/core/constants.py` and `ROLLING_WINRATE_DEFAULT_WINDOW = 20`, `ROLLING_WINRATE_MIN_WINDOW = 5`, `ROLLING_WINRATE_MAX_WINDOW = 100`

## 2. Backend Repository

- [ ] 2.1 Add `get_rolling_winrate(user_id, window, account_id, from_date, to_date)` async method to `TimeseriesRepository` using SQL window function (`AVG(CASE WHEN pnl > 0 THEN 1.0 ELSE 0.0 END) OVER (ORDER BY closed_at ROWS BETWEEN N-1 PRECEDING AND CURRENT ROW)`)
- [ ] 2.2 Add `get_monthly_winrate(user_id, account_id, from_date, to_date)` async method to `TimeseriesRepository` using `date_trunc('month', closed_at)` group-by aggregation

## 3. Backend Service

- [ ] 3.1 Add `rolling_winrate(user_id, window, account_id, from_date, to_date)` method to `TimeseriesService` delegating to repository
- [ ] 3.2 Add `monthly_winrate(user_id, account_id, from_date, to_date)` method to `TimeseriesService` delegating to repository

## 4. Backend API Routes

- [ ] 4.1 Add `GET /timeseries/rolling-winrate` endpoint to `backend/app/api/v1/timeseries.py` with `window: int = Query(20, ge=5, le=100)`, optional `account_id`, `from_date`, `to_date` params; returns `list[RollingWinratePoint]`
- [ ] 4.2 Add `GET /timeseries/monthly-winrate` endpoint to `backend/app/api/v1/timeseries.py` with optional `account_id`, `from_date`, `to_date` params; returns `list[MonthlyWinratePoint]`

## 5. Backend Tests

- [ ] 5.1 Write unit tests for `TimeseriesService.rolling_winrate` (mock repository, verify delegation and window validation)
- [ ] 5.2 Write integration tests for `TimeseriesRepository.get_rolling_winrate` (real test DB, verify correct rolling calculation)
- [ ] 5.3 Write integration tests for `TimeseriesRepository.get_monthly_winrate` (real test DB, verify win/loss counts and month grouping)
- [ ] 5.4 Write API tests for `GET /timeseries/rolling-winrate` (401 unauthenticated, 422 invalid window, 200 correct shape)
- [ ] 5.5 Write API tests for `GET /timeseries/monthly-winrate` (401 unauthenticated, 200 correct shape, account filter)

## 6. OpenAPI Client Sync

- [ ] 6.1 Run `openapi-sync` skill to regenerate the frontend TypeScript API client after backend endpoints are added

## 7. Frontend Hooks

- [ ] 7.1 Add `useRollingWinrate(window?: number, accountId?: string)` hook in `frontend/hooks/useRollingWinrate.ts` using React Query + generated API client
- [ ] 7.2 Add `useMonthlyWinrate(accountId?: string)` hook in `frontend/hooks/useMonthlyWinrate.ts` using React Query + generated API client

## 8. Frontend Charts

- [ ] 8.1 Implement `RollingWinrateChart` component in `frontend/components/charts/RollingWinrateChart.tsx` — Recharts `LineChart`, x-axis as date, y-axis as percentage (0–100%), window selector dropdown (5, 10, 20, 50)
- [ ] 8.2 Implement `MonthlyWinrateChart` component in `frontend/components/charts/MonthlyWinrateChart.tsx` — Recharts `BarChart`, x-axis as month label, y-axis as percentage, tooltip showing win/loss counts

## 9. Frontend Integration

- [ ] 9.1 Add `RollingWinrateChart` and `MonthlyWinrateChart` to the dashboard analytics section (alongside existing extended charts)
- [ ] 9.2 Verify both charts render correctly with no data, partial data (< window), and full data

## 10. Lint, Types, and Commit

- [ ] 10.1 Run `lint-check` skill — fix all ruff and mypy errors
- [ ] 10.2 Run `unit-test` skill — ensure all tests pass
- [ ] 10.3 Create git commit using `commit-helper` skill
