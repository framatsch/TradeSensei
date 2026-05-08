## Context

In the Trade Sensei Platform, the Portfolio Workspace displays high-level analytics (including the Strategy scatter plot) and provides a filter bar for refining the displayed data. Currently, this filter bar includes a Portfolio dropdown. However, because the portfolio context is already set at a higher level (e.g., in the title bar or app shell), selecting a portfolio in the workspace filter is redundant.

Instead, users need the ability to drill down into specific accounts within the selected portfolio. Furthermore, there is a known bug where the Strategy scatter plot visualization ignores the global filter state entirely and always displays all available data.

## Goals / Non-Goals

**Goals:**
- Replace the Portfolio filter component in the Workspace filter bar with an Account filter component.
- The Account filter should be a multi-select dropdown, defaulting to an "All" state when no specific accounts are selected.
- Ensure the global filter state (e.g., Zustand store or URL parameters) handles `accountIds` as an array of selected strings/UUIDs.
- Bind the Strategy scatter plot to this global filter state so it dynamically updates when dates, accounts, or other filter parameters change.

**Non-Goals:**
- Redesigning the entire Workspace UI or changing the layout of other widgets.
- Changing the backend aggregation logic for metrics (unless they currently lack support for account-level filtering, which is out of scope for the pure UI state binding, but API calls must pass the arguments).
- Introducing new visualizations to the Strategy tab.

## Decisions

1. **Account Multi-Select in Filter State**: 
   - **Decision**: Represent selected accounts as an array of IDs in the global filter state. If the array is empty (or explicitly "All"), the API/hooks will fetch data for all accounts in the current portfolio.
   - **Rationale**: It allows flexible grouping of multiple accounts (e.g., combining two specific margin accounts but excluding a cash account).
   - **Alternatives Considered**: A single-select account dropdown. Rejected because users often want to see aggregate performance across a subset of their accounts.

2. **Propagating Filters to the Scatter Plot**:
   - **Decision**: Update the Strategy scatter plot component (using Recharts) to consume the global filter parameters from the shared hook (e.g., `useFilters` or `useWorkspaceFilters`). Pass these parameters down to the respective `useQuery` API hook.
   - **Rationale**: Keeps the component reactive to state changes, fixing the bug where it was statically fetching all data or ignoring the filter context.

## Risks / Trade-offs

- **Risk: Performance overhead on multi-account queries.** 
  - *Mitigation*: The backend TimescaleDB aggregations should already be optimized for indexed account IDs. If performance drops when explicitly filtering by 3+ accounts vs. "All", we may need to verify the query plans.
- **Risk: Scatter plot data fetching errors.** 
  - *Mitigation*: Ensure the API endpoint powering the Strategy scatter plot accepts an array of `account_ids` alongside the existing portfolio context and date ranges.
