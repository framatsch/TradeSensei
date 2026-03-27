## ADDED Requirements

### Requirement: Filter trades by symbol
The `GET /api/v1/trades` endpoint SHALL accept an optional `symbol` query parameter (string). When provided, only trades whose symbol contains the given value (case-insensitive, partial match) SHALL be returned.

#### Scenario: Symbol filter returns matching trades
- **WHEN** client sends `GET /api/v1/trades?symbol=aapl`
- **THEN** response contains only trades where `symbol` contains "AAPL" (case-insensitive)

#### Scenario: Symbol filter with no matches returns empty list
- **WHEN** client sends `GET /api/v1/trades?symbol=ZZZNOTFOUND`
- **THEN** response contains an empty `items` array and `next_cursor` is null

### Requirement: Filter trades by direction
The `GET /api/v1/trades` endpoint SHALL accept an optional `direction` query parameter (`LONG` or `SHORT`). When provided, only trades with the matching direction SHALL be returned.

#### Scenario: Filter by LONG direction
- **WHEN** client sends `GET /api/v1/trades?direction=LONG`
- **THEN** response contains only trades with `direction = "LONG"`

#### Scenario: Invalid direction value returns 422
- **WHEN** client sends `GET /api/v1/trades?direction=INVALID`
- **THEN** response status is 422 with a validation error

### Requirement: Filter trades by asset class
The `GET /api/v1/trades` endpoint SHALL accept an optional `asset_class` query parameter (one of: `EQUITY`, `OPTION`, `FUTURE`, `FOREX`, `CRYPTO`). When provided, only trades with the matching asset class SHALL be returned.

#### Scenario: Filter by asset class
- **WHEN** client sends `GET /api/v1/trades?asset_class=FUTURE`
- **THEN** response contains only trades with `asset_class = "FUTURE"`

### Requirement: Filter trades by tags with AND/OR mode
The `GET /api/v1/trades` endpoint SHALL accept optional `tag_ids` (list of UUIDs, repeated query param) and `tag_filter_mode` (`and` | `or`, default `and`) parameters.
- In `and` mode: only trades that have **all** of the specified tags SHALL be returned.
- In `or` mode: trades that have **at least one** of the specified tags SHALL be returned.

#### Scenario: AND tag filter returns trades with all specified tags
- **WHEN** client sends `GET /api/v1/trades?tag_ids=<id1>&tag_ids=<id2>&tag_filter_mode=and`
- **THEN** response contains only trades that have both tag `<id1>` AND tag `<id2>`

#### Scenario: OR tag filter returns trades with any specified tag
- **WHEN** client sends `GET /api/v1/trades?tag_ids=<id1>&tag_ids=<id2>&tag_filter_mode=or`
- **THEN** response contains trades that have tag `<id1>` OR tag `<id2>` (or both)

#### Scenario: Empty tag_ids list is ignored
- **WHEN** client sends `GET /api/v1/trades` without `tag_ids`
- **THEN** no tag filter is applied; all trades are returned (subject to other filters)

### Requirement: Filter trades by playbook
The `GET /api/v1/trades` endpoint SHALL accept an optional `playbook_id` (UUID) query parameter. When provided, only trades assigned to that playbook SHALL be returned.

#### Scenario: Filter by playbook
- **WHEN** client sends `GET /api/v1/trades?playbook_id=<uuid>`
- **THEN** response contains only trades with `playbook_id = <uuid>`

### Requirement: Filter trades by opened-at date range
The `GET /api/v1/trades` endpoint SHALL accept optional `opened_at_from` and `opened_at_to` query parameters (ISO 8601 timezone-aware datetimes). When provided, only trades with `opened_at` within the range SHALL be returned. Either bound is optional.

#### Scenario: Filter with lower bound only
- **WHEN** client sends `GET /api/v1/trades?opened_at_from=2025-01-01T00:00:00Z`
- **THEN** response contains only trades where `opened_at >= 2025-01-01T00:00:00Z`

#### Scenario: Filter with both bounds
- **WHEN** client sends `GET /api/v1/trades?opened_at_from=2025-01-01T00:00:00Z&opened_at_to=2025-01-31T23:59:59Z`
- **THEN** response contains only trades within January 2025

#### Scenario: Naive datetime is rejected
- **WHEN** client sends `opened_at_from` without timezone offset
- **THEN** response status is 422

### Requirement: Filter trades by PnL sign (winner/loser)
The `GET /api/v1/trades` endpoint SHALL accept an optional `pnl_positive` (boolean) query parameter. When `true`, only trades with `pnl > 0` SHALL be returned. When `false`, only trades with `pnl <= 0` SHALL be returned. When omitted, no PnL filter is applied.

#### Scenario: Filter winners
- **WHEN** client sends `GET /api/v1/trades?pnl_positive=true`
- **THEN** response contains only trades with `pnl > 0`

#### Scenario: Filter losers
- **WHEN** client sends `GET /api/v1/trades?pnl_positive=false`
- **THEN** response contains only trades with `pnl <= 0`

### Requirement: Multiple filters combine with AND logic
When multiple filter parameters are provided simultaneously, the `GET /api/v1/trades` endpoint SHALL return only trades that satisfy **all** active filters.

#### Scenario: Combined symbol and direction filter
- **WHEN** client sends `GET /api/v1/trades?symbol=ES&direction=SHORT`
- **THEN** response contains only trades where symbol contains "ES" AND direction is "SHORT"

### Requirement: Frontend filter bar is always visible
The trades page SHALL display a filter bar above the trade table at all times (not collapsible). The filter bar SHALL contain: symbol text input (debounced 300ms), direction dropdown, asset class dropdown, tags multi-select with AND/OR toggle, playbook dropdown, opened-at date range (two date inputs), winner/loser toggle, and a "Clear filters" button showing the count of active filters.

#### Scenario: Clear filters button resets all filters
- **WHEN** user clicks the "Clear filters" button
- **THEN** all filter inputs are reset to their default (empty/unset) state and the trade list reloads without filters

#### Scenario: Changing a filter resets to page 1
- **WHEN** user changes any filter value
- **THEN** the cursor is reset to null and the first page of results is loaded
