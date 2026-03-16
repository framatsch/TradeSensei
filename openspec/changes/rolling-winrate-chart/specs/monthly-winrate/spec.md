## ADDED Requirements

### Requirement: Monthly winrate aggregation endpoint
The system SHALL provide a `GET /timeseries/monthly-winrate` endpoint that returns per-calendar-month win rate aggregations for the authenticated user's closed trades.

The response SHALL be an ordered list of `MonthlyWinratePoint` objects:
```json
{ "month": "2025-11", "winrate": 0.60, "win_count": 12, "loss_count": 8 }
```

The endpoint SHALL accept:
- `account_id` (optional UUID): filter to a single account
- `from_date` / `to_date` (optional ISO date): restrict date range

#### Scenario: Returns one record per calendar month
- **WHEN** an authenticated user calls `GET /timeseries/monthly-winrate`
- **THEN** the response contains one object per calendar month in which at least one trade was closed, ordered ascending by month

#### Scenario: Win and loss counts sum to total trades
- **WHEN** the response is returned
- **THEN** for each point, `win_count + loss_count` equals the total number of closed trades in that month (trades with pnl = 0 counted as losses)

#### Scenario: Account filter restricts results
- **WHEN** an authenticated user calls `GET /timeseries/monthly-winrate?account_id=<uuid>`
- **THEN** only trades belonging to that account contribute to the aggregation

#### Scenario: Unauthenticated request is rejected
- **WHEN** a request is made without a valid JWT
- **THEN** the API returns HTTP 401
