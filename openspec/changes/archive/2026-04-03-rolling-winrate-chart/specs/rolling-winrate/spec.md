## ADDED Requirements

### Requirement: Rolling winrate time series endpoint
The system SHALL provide a `GET /timeseries/rolling-winrate` endpoint that returns a time series of rolling N-trade win rates for the authenticated user's trades.

The endpoint SHALL accept:
- `window` (integer, 5–100, default 20): number of trades in the rolling window
- `account_id` (optional UUID): filter to a single account
- `from_date` / `to_date` (optional ISO date): restrict date range

The response SHALL be an ordered list of `RollingWinratePoint` objects:
```json
{ "date": "2025-11-14", "winrate": 0.65, "trade_count": 20 }
```
where `winrate` is the fraction of winning trades (pnl > 0) in the last `window` closed trades up to and including that date.

#### Scenario: Default window returns 20-trade rolling winrate
- **WHEN** an authenticated user calls `GET /timeseries/rolling-winrate` with no parameters
- **THEN** the response contains one point per closed trade, each with `trade_count` ≤ 20 and `winrate` between 0.0 and 1.0

#### Scenario: Custom window is respected
- **WHEN** an authenticated user calls `GET /timeseries/rolling-winrate?window=10`
- **THEN** all returned points have `trade_count` ≤ 10

#### Scenario: Window out of range returns 422
- **WHEN** an authenticated user calls `GET /timeseries/rolling-winrate?window=200`
- **THEN** the API returns HTTP 422 with a validation error

#### Scenario: Account filter restricts results
- **WHEN** an authenticated user calls `GET /timeseries/rolling-winrate?account_id=<uuid>`
- **THEN** only trades belonging to that account are included in the calculation

#### Scenario: Unauthenticated request is rejected
- **WHEN** a request is made without a valid JWT
- **THEN** the API returns HTTP 401
