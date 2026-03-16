## ADDED Requirements

### Requirement: Server-side trade sorting
The system SHALL support optional sort query parameters on `GET /trades` that control the order of returned results.

Supported sort parameters:
- `sort_by` (string, default: `closed_at`): field to sort by. Allowed values: `closed_at`, `symbol`, `pnl`, `pnl_eur`, `asset_class`, `side`
- `sort_dir` (string enum: `asc`, `desc`, default: `desc`): sort direction

When `sort_by` is set to a non-default value (anything other than `closed_at`), the cursor-based pagination SHALL be replaced with offset-based pagination using a `skip` integer parameter (default 0) in place of `cursor`.

#### Scenario: Default sort is closed_at descending
- **WHEN** an authenticated user calls `GET /trades` with no sort params
- **THEN** trades are returned ordered by `closed_at` descending (most recent first), matching current behavior

#### Scenario: Custom sort field is respected
- **WHEN** an authenticated user calls `GET /trades?sort_by=pnl&sort_dir=asc`
- **THEN** trades are returned ordered by `pnl` ascending

#### Scenario: Invalid sort_by value returns 422
- **WHEN** an authenticated user calls `GET /trades?sort_by=unknown_field`
- **THEN** the API returns HTTP 422

#### Scenario: Non-default sort uses offset pagination
- **WHEN** an authenticated user calls `GET /trades?sort_by=symbol&skip=20`
- **THEN** trades are returned sorted by symbol, starting from record 20

#### Scenario: Unauthenticated request is rejected
- **WHEN** a request is made without a valid JWT
- **THEN** the API returns HTTP 401
