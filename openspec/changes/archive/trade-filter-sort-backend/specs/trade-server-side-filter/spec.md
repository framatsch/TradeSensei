## ADDED Requirements

### Requirement: Server-side trade filtering
The system SHALL support optional filter query parameters on `GET /trades` that are applied server-side before pagination.

Supported filter parameters:
- `symbol` (string): exact or case-insensitive match
- `asset_class` (string enum): filter by asset class
- `side` (string enum: `long`, `short`): filter by trade direction
- `account_id` (UUID): filter by broker account
- `playbook_id` (UUID): filter to trades assigned to a specific playbook
- `tag_id` (UUID): filter to trades that have a specific tag
- `from_date` / `to_date` (ISO date): inclusive date range on `closed_at`
- `min_pnl` / `max_pnl` (decimal): inclusive PnL range

All parameters are optional. When omitted, no filter is applied for that dimension. Multiple filters are combined with AND logic.

#### Scenario: Symbol filter returns only matching trades
- **WHEN** an authenticated user calls `GET /trades?symbol=AAPL`
- **THEN** only trades with `symbol` matching "AAPL" (case-insensitive) are returned

#### Scenario: Date range filter restricts results
- **WHEN** an authenticated user calls `GET /trades?from_date=2025-01-01&to_date=2025-03-31`
- **THEN** only trades with `closed_at` between 2025-01-01 and 2025-03-31 (inclusive) are returned

#### Scenario: Tag filter returns only trades with that tag
- **WHEN** an authenticated user calls `GET /trades?tag_id=<uuid>`
- **THEN** only trades that have that tag in their `trade_tags` join are returned

#### Scenario: Combined filters use AND logic
- **WHEN** an authenticated user calls `GET /trades?symbol=TSLA&side=long`
- **THEN** only trades matching both symbol TSLA AND side long are returned

#### Scenario: No filter params returns all trades (existing behavior)
- **WHEN** an authenticated user calls `GET /trades` with no filter params
- **THEN** all trades belonging to the user are returned (paginated), matching current behavior

#### Scenario: Unauthenticated request is rejected
- **WHEN** a request is made without a valid JWT
- **THEN** the API returns HTTP 401
