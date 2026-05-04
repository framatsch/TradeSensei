# checkin-modelbook-filters Specification

## Purpose
TBD - created by archiving change checkin-hub-ui-gaps. Update Purpose after archive.
## Requirements
### Requirement: Model Book view provides a dedicated filter panel with date range and regime
The Model Book view SHALL render a filter bar above the grid containing a date range filter (start date + end date inputs) and a regime filter (regime pills). These filters SHALL be independent from the Timeline view's filter state.

#### Scenario: User filters Model Book by date range
- **WHEN** the user enters a start date and end date in the Model Book filter bar
- **THEN** only check-in entries within that date range are shown in the grid

#### Scenario: User filters Model Book by regime
- **WHEN** the user selects a regime pill in the Model Book filter bar
- **THEN** only check-in entries with that regime are shown in the grid

#### Scenario: No filters applied shows all entries
- **WHEN** neither a date range nor a regime is selected
- **THEN** all check-in entries are shown (up to the current per-page limit)

### Requirement: Model Book view provides a per-page selector
The Model Book view SHALL render a per-page selector (dropdown) allowing the user to choose how many cards are shown per page. The available options SHALL be 12, 24, and 48. The default SHALL be 12.

#### Scenario: User changes items per page
- **WHEN** the user selects "24" in the per-page dropdown
- **THEN** the grid reloads and shows up to 24 cards per page
- **AND** pagination resets to page 1

#### Scenario: Per-page selector is visible in Model Book
- **WHEN** the user is in the Model Book view
- **THEN** a "Items per page" dropdown is visible in the filter bar area

