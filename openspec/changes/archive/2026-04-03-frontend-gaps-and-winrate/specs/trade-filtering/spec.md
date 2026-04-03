## ADDED Requirements

### Requirement: User can filter the trade list
The system SHALL display a filter bar above the trade table allowing the user to
filter by symbol (text search), direction (LONG/SHORT), asset class, playbook,
date range (opened_at from/to), tag, and winner/loser.

#### Scenario: Filter by symbol
- **WHEN** user types a symbol in the filter bar
- **THEN** the trade table updates to show only trades whose symbol contains the input (case-insensitive)

#### Scenario: Filter by direction
- **WHEN** user selects "LONG" from the direction dropdown
- **THEN** only LONG trades are shown

#### Scenario: Filter by playbook
- **WHEN** user selects a playbook from the filter dropdown
- **THEN** only trades assigned to that playbook are shown

#### Scenario: Multiple filters combined
- **WHEN** user sets both a symbol filter and a direction filter
- **THEN** only trades matching both criteria are shown

#### Scenario: Clear all filters
- **WHEN** user clicks "Clear filters"
- **THEN** all filters are reset and the full trade list is restored

---

### Requirement: Filter state is persisted in the URL
The system SHALL store all active filter values as URL query parameters so that
the filtered view survives page reload and is shareable.

#### Scenario: Filter survives reload
- **WHEN** user sets a filter and reloads the page
- **THEN** the same filter is still active and the table shows filtered results

#### Scenario: Browser back restores previous filter
- **WHEN** user changes a filter then clicks browser back
- **THEN** the previous filter state is restored

---

### Requirement: User can sort the trade list by column
The system SHALL allow sorting the trade table by clicking column headers for
symbol, PnL, opened_at, and closed_at. Clicking the same header toggles
ascending/descending order.

#### Scenario: Sort by PnL ascending
- **WHEN** user clicks the "PnL" column header once
- **THEN** trades are sorted from lowest to highest PnL
- **AND** a sort indicator (arrow) is shown on the header

#### Scenario: Toggle sort direction
- **WHEN** user clicks an already-sorted column header
- **THEN** sort order toggles between ascending and descending
