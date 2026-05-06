## ADDED Requirements

### Requirement: Account filter state is synced to URL
The global Account multi-select filter state SHALL be synchronized to the URL search parameters to allow sharing and restoring of account-specific views.

#### Scenario: Single account filter is synced to URL
- **WHEN** the user selects a single account in the Account filter
- **THEN** the URL search params are updated with `accountIds=<id>`

#### Scenario: Multiple accounts filter is synced to URL
- **WHEN** the user selects multiple accounts in the Account filter
- **THEN** the URL search params are updated with multiple `accountIds` or a comma-separated list `accountIds=<id1>,<id2>`

#### Scenario: Default (All) account filter is reflected in URL
- **WHEN** the user selects "All" or clears the account selection
- **THEN** the `accountIds` parameter is removed from the URL, indicating all accounts should be fetched

#### Scenario: URL with account parameter restores filter state
- **WHEN** the user navigates directly to `/dashboard/portfolio?accountIds=123`
- **THEN** the Account filter initializes with the specific account selected
- **AND** the dashboard data is filtered to that account
