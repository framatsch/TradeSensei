## ADDED Requirements

### Requirement: Trade list has a filter bar
The `/dashboard/trades` page SHALL display a collapsible filter bar above the trade table. When collapsed, the button MUST show a badge with the count of active filters.

#### Scenario: Filter bar defaults to collapsed
- **WHEN** user navigates to the trades page with no filter query params
- **THEN** the filter bar is collapsed and the toggle button shows no badge

#### Scenario: User expands the filter bar
- **WHEN** user clicks the "Filters" toggle button
- **THEN** the filter controls become visible

### Requirement: Trades can be filtered by symbol
The filter bar SHALL include a text input for symbol prefix/exact match.

#### Scenario: Filter by symbol
- **WHEN** user types "AAPL" in the symbol filter and presses Enter or tabs out
- **THEN** the trade table shows only trades where symbol matches "AAPL" (case-insensitive)
- **AND** `?symbol=AAPL` appears in the URL

### Requirement: Trades can be filtered by direction
The filter bar SHALL include a direction selector (LONG / SHORT / All).

#### Scenario: Filter by direction
- **WHEN** user selects "SHORT"
- **THEN** only short trades are shown
- **AND** `?direction=SHORT` appears in the URL

### Requirement: Trades can be filtered by asset class
The filter bar SHALL include a multi-select for asset class (EQUITY, OPTION, FUTURE, FOREX, CRYPTO).

#### Scenario: Filter by asset class
- **WHEN** user selects "OPTION" and "FUTURE"
- **THEN** only trades with those asset classes are shown

### Requirement: Trades can be filtered by date range
The filter bar SHALL include date-from and date-to pickers that filter by `opened_at`.

#### Scenario: Filter by date range
- **WHEN** user sets date-from to 2025-01-01 and date-to to 2025-03-31
- **THEN** only trades opened within Q1 2025 are shown

### Requirement: Trades can be filtered by tag
The filter bar SHALL include a tag multi-select populated from `/tags`.

#### Scenario: Filter by tag
- **WHEN** user selects a tag
- **THEN** only trades that have that tag are shown

### Requirement: Trades can be filtered by playbook
The filter bar SHALL include a playbook single-select populated from `/playbooks`.

#### Scenario: Filter by playbook
- **WHEN** user selects a playbook
- **THEN** only trades assigned to that playbook are shown

### Requirement: Trades can be filtered by PnL sign
The filter bar SHALL include a "Winners only / Losers only / All" radio group.

#### Scenario: Show winners only
- **WHEN** user selects "Winners only"
- **THEN** only trades with PnL > 0 are shown

### Requirement: Trade table columns are sortable
Column headers for opened_at, closed_at, symbol, pnl, and commission SHALL be clickable to sort ascending or descending.

#### Scenario: Sort by PnL descending
- **WHEN** user clicks the "PnL" column header once (if not already sorted by PnL) or twice (to reverse)
- **THEN** trades are sorted by pnl descending
- **AND** a sort indicator arrow is shown on the column header

### Requirement: Filters persist in URL
All active filter and sort state SHALL be reflected in URL query parameters so the view is bookmarkable and survives page refresh.

#### Scenario: User refreshes page with filters applied
- **WHEN** user has filters applied and refreshes the browser
- **THEN** the same filters are re-applied and the same subset of trades is shown
