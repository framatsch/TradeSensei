## ADDED Requirements

### Requirement: Account-level filtering within Portfolio Workspace
The Portfolio Workspace SHALL allow users to filter dashboard data (metrics, visualizations, and lists) by one or multiple accounts within the currently selected portfolio context. 

#### Scenario: User selects a specific account
- **WHEN** the user selects a single account from the Account multi-select filter
- **THEN** all widgets on the dashboard (including the Strategy scatter plot) reflect only the data belonging to that account

#### Scenario: User selects multiple accounts
- **WHEN** the user selects multiple accounts from the Account multi-select filter
- **THEN** the dashboard aggregates and displays data for all selected accounts

#### Scenario: User selects "All" accounts (default)
- **WHEN** the user clears all account selections or explicitly selects "All"
- **THEN** the dashboard fetches and aggregates data for all accounts available in the current portfolio

### Requirement: Strategy Scatter Plot respects global filters
The Strategy scatter plot widget SHALL respect the global filter state, including date range, account selection, and tags, when fetching and rendering data.

#### Scenario: Date range filter applied to Strategy scatter plot
- **WHEN** the user modifies the global date range filter
- **THEN** the Strategy scatter plot refetches and displays only the execution data within that date range

#### Scenario: Account filter applied to Strategy scatter plot
- **WHEN** the user updates the Account multi-select filter
- **THEN** the Strategy scatter plot updates to show only the data belonging to the selected account(s)
