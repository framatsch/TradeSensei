## ADDED Requirements

### Requirement: All trade endpoints scoped to portfolio
The system SHALL require a `portfolio_id` path segment on all endpoints that
read or write trades:
- `GET /api/v1/portfolios/{portfolio_id}/trades`
- `POST /api/v1/portfolios/{portfolio_id}/trades`
- `GET /api/v1/portfolios/{portfolio_id}/trades/{trade_id}`
- `PATCH /api/v1/portfolios/{portfolio_id}/trades/{trade_id}`
- `DELETE /api/v1/portfolios/{portfolio_id}/trades/{trade_id}`
- `POST /api/v1/portfolios/{portfolio_id}/trades/bulk/delete`
- `POST /api/v1/portfolios/{portfolio_id}/trades/bulk/assign-tags`
- `POST /api/v1/portfolios/{portfolio_id}/trades/bulk/assign-playbook`
- `POST /api/v1/portfolios/{portfolio_id}/trades/merge`
- `POST /api/v1/portfolios/{portfolio_id}/trades/{trade_id}/partial-close`

The system MUST verify that the requesting user owns the portfolio before
servicing any request.

#### Scenario: Request with valid portfolio returns trades
- **WHEN** a user calls `GET /api/v1/portfolios/{portfolio_id}/trades` for
  a portfolio they own
- **THEN** the system SHALL return only trades whose account belongs to that
  portfolio

#### Scenario: Request with foreign portfolio_id rejected
- **WHEN** a user calls any scoped endpoint with a `portfolio_id` belonging
  to another user
- **THEN** the system SHALL return HTTP 404 (ownership must not be disclosed)

#### Scenario: Trade from another portfolio not accessible via path
- **WHEN** a user calls `GET /api/v1/portfolios/{portfolio_id}/trades/{trade_id}`
  where `trade_id` belongs to a different portfolio
- **THEN** the system SHALL return HTTP 404

---

### Requirement: Metrics and timeseries endpoints scoped to portfolio
The system SHALL scope all metrics and timeseries aggregation endpoints to a
portfolio:
- `GET /api/v1/portfolios/{portfolio_id}/metrics/summary`
- `GET /api/v1/portfolios/{portfolio_id}/metrics/equity-curve`
- `GET /api/v1/portfolios/{portfolio_id}/metrics/drawdown`
- `GET /api/v1/portfolios/{portfolio_id}/timeseries/*`

Aggregations MUST only include trades from accounts linked to the portfolio.

#### Scenario: Metrics scoped to portfolio
- **WHEN** a user calls metrics with a valid `portfolio_id`
- **THEN** the system SHALL compute metrics only over trades in that portfolio

#### Scenario: account_id filter within portfolio still works
- **WHEN** a user calls metrics with both `portfolio_id` (path) and
  `account_id` (query param)
- **THEN** the system SHALL verify that the `account_id` belongs to the
  portfolio before filtering; if not, return HTTP 400

---

### Requirement: Import endpoints scoped to portfolio
The system SHALL scope all broker import endpoints to a portfolio:
- `POST /api/v1/portfolios/{portfolio_id}/imports/upload`
- `POST /api/v1/portfolios/{portfolio_id}/imports/{account_id}/fresh-start`
- `POST /api/v1/portfolios/{portfolio_id}/imports/flex`

The system MUST verify that the target `account_id` belongs to the specified
portfolio before processing any import.

#### Scenario: Import to account in portfolio succeeds
- **WHEN** a user uploads a file to `imports/upload` with an `account_id`
  that belongs to the specified portfolio
- **THEN** the system SHALL process the import and return the import result

#### Scenario: Import to account outside portfolio rejected
- **WHEN** a user uploads a file specifying an `account_id` that belongs to
  a different portfolio
- **THEN** the system SHALL return HTTP 403 with a descriptive error

---

### Requirement: Cross-portfolio reads are rejected
The system SHALL never return trade, execution, cash-transaction, or metrics
data that spans more than one portfolio per request.

#### Scenario: No combined endpoint returns cross-portfolio data
- **WHEN** a request is made to any data endpoint without a portfolio_id
  path segment (using the old URL pattern)
- **THEN** the system SHALL return HTTP 410 Gone with a deprecation message
  pointing to the new portfolio-scoped URL

#### Scenario: Repository layer double-checks portfolio membership
- **WHEN** the repository method executes a query for trades
- **THEN** the query SHALL include a JOIN or subquery that verifies
  `trades.account.portfolio_id = :portfolio_id AND portfolio.user_id = :user_id`
  preventing cross-user or cross-portfolio data leakage even if the service
  layer passed incorrect IDs

---

### Requirement: Cash-transaction endpoints scoped to portfolio
The system SHALL scope cash-transaction endpoints under the portfolio:
- `GET /api/v1/portfolios/{portfolio_id}/accounts/{account_id}/cash-transactions`
- `POST /api/v1/portfolios/{portfolio_id}/accounts/{account_id}/cash-transactions`
- `GET/PATCH/DELETE /api/v1/portfolios/{portfolio_id}/accounts/{account_id}/cash-transactions/{tid}`

The system MUST verify that `account_id` belongs to `portfolio_id` on every
request.

#### Scenario: Cash-transaction on account in portfolio accessible
- **WHEN** a user calls the cash-transaction endpoint with a valid
  portfolio_id and an account_id that belongs to it
- **THEN** the system SHALL return or persist the cash transaction

#### Scenario: account_id outside portfolio rejected
- **WHEN** a user calls the cash-transaction endpoint with an account_id
  that does not belong to the specified portfolio
- **THEN** the system SHALL return HTTP 404
