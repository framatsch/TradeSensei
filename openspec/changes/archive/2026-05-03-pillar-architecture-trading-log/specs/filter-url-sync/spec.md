## ADDED Requirements

### Requirement: All active trade filter state is reflected in URL search parameters
The Trading Log filter state (ticker search, date range, status toggles, active saved filter ID) SHALL be synchronized to the URL search parameters at all times. Navigating to a URL with filter params SHALL restore the filter state.

#### Scenario: Ticker filter is synced to URL
- **WHEN** the user types a ticker in the search input
- **THEN** the URL search params are updated with `ticker=<value>`

#### Scenario: Date range filter is synced to URL
- **WHEN** the user selects a date range in the Filter Configurator
- **THEN** the URL reflects `date_from=<ISO>` and `date_to=<ISO>`

#### Scenario: Status filter is synced to URL
- **WHEN** the user toggles a trade status filter
- **THEN** the URL reflects `status=<value>`

#### Scenario: Active saved filter ID is synced to URL
- **WHEN** the user selects a saved filter from the sidebar
- **THEN** the URL reflects `view_id=<filter-id>`

#### Scenario: URL with filter params restores filter state
- **WHEN** the user navigates directly to `/dashboard/trades?ticker=AAPL&status=closed`
- **THEN** the trade table is filtered to show closed AAPL trades
- **AND** the Filter Configurator reflects the active parameters

#### Scenario: Sharing a filtered URL reproduces the filter state
- **WHEN** a user copies the URL with filter params and opens it in a new session
- **THEN** the same filter configuration is applied to the trade table
