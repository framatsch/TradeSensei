## MODIFIED Requirements

### Requirement: All active trade filter state is reflected in URL search parameters
The Trading Log filter state (symbol include/exclude lists, asset classes, date range, status toggles, direction, account, playbook, taxonomy, PnL, hour of day, day of week, active saved filter ID) SHALL be synchronized to the URL search parameters at all times. Navigating to a URL with filter params SHALL restore the filter state. The singular `symbol` param is replaced by `symbols` (comma-separated include list) and `excluded_symbols` (comma-separated exclude list).

#### Scenario: Symbol include tags are synced to URL
- **WHEN** the user adds `AAPL` and `MSFT` as include symbols on the Trades filter
- **THEN** the URL search params are updated with `symbols=AAPL,MSFT`

#### Scenario: Symbol exclude tags are synced to URL
- **WHEN** the user adds `TSLA` as an exclude symbol on the Trades filter
- **THEN** the URL search params include `excluded_symbols=TSLA`

#### Scenario: URL with symbols param restores symbol filter state
- **WHEN** the user navigates to `/dashboard/trades?symbols=AAPL,MSFT&excluded_symbols=TSLA`
- **THEN** the Trades filter bar shows `AAPL` and `MSFT` as include tags and `TSLA` as an exclude tag
- **AND** the trade table is filtered accordingly

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
- **WHEN** the user navigates directly to `/dashboard/trades?symbols=AAPL&status=closed`
- **THEN** the trade table is filtered to show closed trades with symbol starting with `AAPL`
- **AND** the Filter Configurator reflects the active parameters

#### Scenario: Sharing a filtered URL reproduces the filter state
- **WHEN** a user copies the URL with filter params and opens it in a new session
- **THEN** the same filter configuration is applied to the trade table

## ADDED Requirements

### Requirement: Dashboard workspace filter state includes symbol and asset class in URL
The Dashboard/Workspace filter state SHALL sync `symbols`, `excluded_symbols`, and `asset_classes` to URL search parameters using the same comma-separated format as the Trades filter.

#### Scenario: Dashboard symbol filter synced to URL
- **WHEN** the user adds include/exclude symbols in the Dashboard extended filter section
- **THEN** the URL is updated with `symbols=<include-list>` and/or `excluded_symbols=<exclude-list>`

#### Scenario: Dashboard asset class filter synced to URL
- **WHEN** the user selects one or more asset classes in the Dashboard extended filter section
- **THEN** the URL is updated with `asset_classes=EQUITY,OPTION` (comma-separated)

#### Scenario: URL with extended params restores Dashboard filter state
- **WHEN** the user navigates to a workspace URL with `symbols=AAPL&asset_classes=EQUITY`
- **THEN** the Dashboard filter bar reflects those active extended filters
- **AND** the extended section is expanded automatically to show the active filters
