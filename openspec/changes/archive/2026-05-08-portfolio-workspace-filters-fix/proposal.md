## Why

Currently, the filter view in the Portfolio Workspace redundantly displays a Portfolio selection dropdown, even though the active portfolio is already determined globally (e.g., via the title bar or route). Additionally, the Strategy scatter plot visualization always displays unfiltered data regardless of the user's selected global filters. This change replaces the redundant portfolio filter with a more granular, account-level multi-select filter and ensures all widgets (like the Strategy scatter plot) accurately respect the global filter state.

## What Changes

- Remove the redundant Portfolio selection dropdown from the Portfolio Workspace filter view.
- Add an Account multi-select dropdown in the filter view (defaults to "All" accounts within the active portfolio).
- Bind the new Account filter to the global filter state.
- Update the Strategy scatter plot widget to consume and respect the global filter parameters (e.g., date range, accounts, tags) instead of fetching or displaying unfiltered data.

## Capabilities

### New Capabilities
- `dashboard-account-filtering`: Ability to filter workspace metrics and widgets by one or multiple accounts within the active portfolio context.

### Modified Capabilities
- `filter-url-sync`: Global filter state must be updated to include the multi-select account parameter and remove the portfolio parameter (if it was present).

## Impact

- **Frontend/UI**: Changes to the Portfolio Workspace filter UI components (replacing Portfolio dropdown with Account multi-select). Update the Strategy scatter plot widget to pass filter state to its data-fetching hook.
- **State Management**: Updates to the global filter state (e.g., Context or Zustand store) and potentially the `filter-url-sync` logic.
- **Backend/API (if applicable)**: Ensure API endpoints that power the Strategy scatter plot correctly accept and apply the account-level and standard filters.
