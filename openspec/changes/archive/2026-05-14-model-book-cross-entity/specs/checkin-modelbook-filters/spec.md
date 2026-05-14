## MODIFIED Requirements

### Requirement: Model Book view provides a dedicated filter panel with date range and regime
The Model Book view SHALL render a filter bar above the grid containing: a date range filter (start date + end date inputs), an entity type toggle (All / Trades / Check-ins), and a regime filter (regime pills). The regime filter SHALL only be visible when the entity type is set to "All" or "Check-ins". These filters SHALL be independent from the Timeline view's filter state.

#### Scenario: User filters Model Book by date range
- **WHEN** the user enters a start date and end date in the Model Book filter bar
- **THEN** only entries within that date range are shown in the grid

#### Scenario: User filters Model Book by regime
- **WHEN** the user selects a regime pill in the Model Book filter bar
- **THEN** only check-in entries with that regime are shown
- **AND** trade entries are unaffected by the regime filter

#### Scenario: User filters by entity type "Trades"
- **WHEN** the user selects "Trades" in the entity type toggle
- **THEN** only starred trade cards are shown
- **AND** the regime filter is hidden

#### Scenario: User filters by entity type "Check-ins"
- **WHEN** the user selects "Check-ins" in the entity type toggle
- **THEN** only starred check-in cards are shown
- **AND** the regime filter is visible

#### Scenario: No filters applied shows all entries
- **WHEN** no filters are active (entity type = "All", no date range, no regime)
- **THEN** all starred entries (trades and check-ins) are shown up to the per-page limit

## ADDED Requirements

### Requirement: Model Book filter bar supports entity type selection
The Model Book filter bar SHALL include a 3-way toggle for entity type: "All", "Trades", "Check-ins". The selected entity type SHALL be passed as a query parameter to the backend aggregation endpoint.

#### Scenario: Entity type defaults to "All"
- **WHEN** the user navigates to the Model Book view
- **THEN** the entity type toggle defaults to "All"
- **AND** both trade cards and check-in cards are visible

#### Scenario: Entity type filter persists in URL params
- **WHEN** the user selects "Trades" entity type
- **THEN** the URL is updated with the entity type parameter
- **AND** refreshing the page preserves the "Trades" selection
