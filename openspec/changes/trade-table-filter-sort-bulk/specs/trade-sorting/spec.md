## ADDED Requirements

### Requirement: Sort trades by any column via query parameters
The `GET /api/v1/trades` endpoint SHALL accept optional `sort_by` and `sort_dir` query parameters.
- `sort_by` SHALL accept: `symbol`, `direction`, `asset_class`, `entry_price`, `exit_price`, `pnl`, `quantity`, `opened_at`, `closed_at`
- `sort_dir` SHALL accept: `asc`, `desc` (default: `desc`)
- Default sort (when `sort_by` is omitted) SHALL remain `opened_at DESC` for backward compatibility.
- NULL values for nullable sort fields (e.g., `pnl`, `closed_at`, `exit_price`) SHALL be sorted NULLS LAST in both directions.

#### Scenario: Sort by PnL descending
- **WHEN** client sends `GET /api/v1/trades?sort_by=pnl&sort_dir=desc`
- **THEN** response items are ordered by `pnl` descending, with NULL pnl entries at the end

#### Scenario: Sort by symbol ascending
- **WHEN** client sends `GET /api/v1/trades?sort_by=symbol&sort_dir=asc`
- **THEN** response items are ordered alphabetically by symbol A→Z

#### Scenario: Invalid sort_by value returns 422
- **WHEN** client sends `GET /api/v1/trades?sort_by=invalid_field`
- **THEN** response status is 422 with a validation error

#### Scenario: Default sort preserved when no sort params provided
- **WHEN** client sends `GET /api/v1/trades` without sort parameters
- **THEN** response items are ordered by `opened_at DESC` (existing behavior preserved)

### Requirement: Cursor pagination is stable within a sort session
When `sort_by` and `sort_dir` are specified, cursor-based pagination SHALL remain stable for the duration of that sort session. The cursor SHALL encode the sort field value and trade ID to enable correct keyset pagination.

#### Scenario: Next page respects sort order
- **WHEN** client fetches page 1 with `sort_by=pnl&sort_dir=desc` and then uses the returned `next_cursor` with the same sort parameters
- **THEN** page 2 continues from where page 1 ended, maintaining PnL descending order

### Requirement: Changing sort or filter resets pagination to page 1
The frontend MUST reset the cursor to null whenever the sort field, sort direction, or any filter value changes.

#### Scenario: Sort change resets to page 1
- **WHEN** user clicks a column header to change the sort
- **THEN** the cursor is reset to null and the first page is loaded with the new sort

### Requirement: Frontend table headers are sortable
Every column header in the trade table SHALL be clickable. Clicking a header SHALL:
1. Set that column as the active sort field
2. If already the active sort field, toggle the direction (asc ↔ desc)
3. Reset pagination to page 1
Sort state SHALL be indicated visually with an up/down arrow icon on the active column header.

#### Scenario: Click unselected column header
- **WHEN** user clicks a column header that is not the current sort column
- **THEN** that column becomes the active sort, direction defaults to desc, cursor resets

#### Scenario: Click active column header toggles direction
- **WHEN** user clicks the currently active sort column header
- **THEN** sort direction toggles between asc and desc, cursor resets
