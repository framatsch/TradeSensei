## ADDED Requirements

### Requirement: Single Portfolio Enforcement
The filter panel SHALL force the selection of exactly one portfolio or base currency at any given time to prevent multi-portfolio aggregation without currency conversion.

#### Scenario: User attempts to deselect last portfolio
- **WHEN** the user tries to deselect the currently active portfolio in the filter panel
- **THEN** the system prevents the action and displays an error message or automatically reselects a default portfolio.

#### Scenario: User attempts to select multiple portfolios
- **WHEN** the user tries to select a second portfolio
- **THEN** the system replaces the current selection with the newly selected portfolio, maintaining only one active selection.

### Requirement: Trade Status Toggle
The filter panel SHALL provide a global toggle to determine if open trades (Unrealized P&L) are included in the metrics.

#### Scenario: Default Trade Status Toggle State
- **WHEN** the Reporting Hub is first loaded
- **THEN** the Trade Status Toggle defaults to "Closed Only".

#### Scenario: Include Open Trades
- **WHEN** the user turns the Trade Status Toggle to "Include Open Trades"
- **THEN** the widgets update to include both closed and open trades in calculations.

### Requirement: Date Range and Tag Filters
The filter panel SHALL provide a date range selector, playbook selector, and tag selector.

#### Scenario: Select Date Range
- **WHEN** the user selects a new start and end date
- **THEN** the widgets update to show data only within that date range.

### Requirement: Server-Side Clustering Delegation
The frontend SHALL NOT perform client-side aggregations and SHALL request server-side clustering or hexbinning for scatterplots when the dataset exceeds 500 trades.

#### Scenario: Requesting Hexbinned Scatterplot
- **WHEN** the current filter combination yields more than 500 trades
- **THEN** the frontend API request parameters or the backend response structure inherently triggers/returns hexbinned data instead of raw data points, preventing browser crashes.

### Requirement: View Management State
The system SHALL provide View Management capabilities to save, load, and share filter configurations.

#### Scenario: Save View
- **WHEN** the user configures a set of filters and clicks "Save As..."
- **THEN** the system saves the filter combination as a named view (e.g., "Q1 Breakout Strategies").
