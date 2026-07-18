# trading-log-operative-sidebar Specification

## Purpose
Define expected behavior for the Trading Log pillar's dedicated operative sidebar (Actions
and Saved Filters), the collapsible filter configurator, and trade table pagination.

## UI Mockup (non-normative reference)

```
+---------------------------------------------------------------------------------+
| [ 🍱 ] > TRADING LOG                                 Portfolio: [ Default ▼ ]   |
+----------------------+----------------------------------------------------------+
| -- ACTIONS --        |  [ ▼ Filter Configuration ]                              |
| [+ ] New Trade       |  (Search, Date, Status, etc.)             [ Save Filter ]|
| [📥] Quick Import    |                                                          |
| [📤] CSV Export      |  +------------+-------+-------+----------+---------+     |
|                      |  | Date       | Asset | Setup | P&L ($)  | P&L (R) |     |
| --    Trades     --  |  +------------+-------+-------+----------+---------+     |
|    • Open Trades     |  | 03.05.2026 | AAPL  | Break | +$450.00 | +2.5 R  |     |
|    • All Winners     |  | 02.05.2026 | TSLA  | Trend | -$150.00 | -1.0 R  |     |
|    • All Losers      |  +------------+-------+-------+----------+---------+     |
|    • Custom Setup A  |                                                          |
|                      |  < 1 2 3 ... 10 >          [ Rows per page: 50 ▼ ]       |
+----------------------+----------------------------------------------------------+
```

**Key layout rules from mockup:**
- Left sidebar is ~200px wide, always visible on desktop
- "ACTIONS" section comes first, then "Trades" (filter shortcuts) section below
- Main content: collapsible Filter Configuration bar at top, dense data table, pagination footer
- No page title or description in the main area — maximize vertical space for the table
- `[ Save Filter ]` button lives inside the Filter Configuration panel (top right)

## Requirements

### Requirement: Trading Log has a dedicated left sidebar with Actions and Saved Filters sections
When the Trading Log pillar is active (any `/dashboard/trades` route), a dedicated left sidebar SHALL replace the global navigation sidebar. The sidebar SHALL contain two sections: "ACTIONS" and a trades filter section ("Trades"). The global navigation sidebar SHALL be hidden on all `/dashboard/trades` routes.

#### Scenario: Sidebar is visible on trades index
- **WHEN** the user navigates to `/dashboard/trades`
- **THEN** the left sidebar shows an "ACTIONS" section with buttons: "+ New Trade", "Quick Import", "CSV Export"
- **AND** shows a "Trades" section with filter shortcut links

#### Scenario: Actions section contains primary I/O buttons
- **WHEN** the user views the Trading Log sidebar
- **THEN** the Actions section SHALL contain exactly three buttons: "+ New Trade", "Quick Import", "CSV Export"

#### Scenario: New Trade button navigates to trade creation
- **WHEN** the user clicks "+ New Trade" in the sidebar
- **THEN** the browser navigates to `/dashboard/trades/new`

#### Scenario: Quick Import button opens import flow
- **WHEN** the user clicks "Quick Import" in the sidebar
- **THEN** the import dialog or page is opened

#### Scenario: CSV Export button triggers CSV download
- **WHEN** the user clicks "CSV Export" in the sidebar
- **THEN** a CSV export of the current filtered trade set is initiated

### Requirement: Saved Filters section shows preset and user-saved filter shortcuts
The sidebar's "Trades" section SHALL render a list of filter shortcuts. System presets (All Trades, Open Trades, All Winners, All Losers) SHALL appear first, followed by user-saved custom filters. Clicking any shortcut SHALL apply the filter to the table and update URL parameters.

#### Scenario: Preset filters are displayed
- **WHEN** the user views the Trades section
- **THEN** preset filter links are shown: "All Trades", "Open Trades", "All Winners", "All Losers"

#### Scenario: User-saved filters appear below presets
- **WHEN** the user has saved custom filters
- **THEN** they appear below the preset filters in the sidebar Trades section

#### Scenario: Clicking a saved filter updates the table
- **WHEN** the user clicks a saved filter link
- **THEN** the trade table updates to show only trades matching that filter
- **AND** the URL search params are updated to reflect the applied filter

#### Scenario: Active filter is visually highlighted
- **WHEN** a saved filter is the currently active filter
- **THEN** that filter link is visually highlighted (active state)

### Requirement: Collapsible Filter Configurator panel above the trade table
A collapsible "Filter Configuration" panel SHALL appear at the top of the main content area. It SHALL contain: Ticker/symbol search input, date range pickers (from/to), and trade status toggles. It SHALL include a "Save Filter" button that persists the current configuration as a named saved filter.

#### Scenario: Filter Configurator is collapsed by default
- **WHEN** the user loads the Trading Log page
- **THEN** the Filter Configurator panel is collapsed, showing only a toggle button labeled "▼ Filter Configuration"

#### Scenario: Filter Configurator expands on click
- **WHEN** the user clicks the "▼ Filter Configuration" toggle
- **THEN** the panel expands to reveal the search input, date range pickers, and status toggles

#### Scenario: Save Filter button persists current filters
- **WHEN** the user has configured filters and clicks "Save Filter"
- **THEN** a prompt/dialog asks for a filter name
- **AND** the filter is saved and appears in the sidebar Saved Filters section

### Requirement: Pagination footer with rows-per-page selector
The trade table footer SHALL show pagination controls and a "Rows per page" dropdown selector.

#### Scenario: Pagination controls are visible
- **WHEN** the trade table has multiple pages of results
- **THEN** the footer shows pagination controls (previous/next, page numbers)

#### Scenario: Rows per page selector is available
- **WHEN** the user views the trade table
- **THEN** a "Rows per page" dropdown is visible in the footer
- **AND** the user can select a different page size to update the table
