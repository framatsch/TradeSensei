## 1. Global Filter State Updates

- [ ] 1.1 Update the global filter state store (e.g., Zustand or Context) to support an `accountIds` array.
- [ ] 1.2 Remove the redundant `portfolioId` from the filter state store, assuming the portfolio context is provided globally (e.g. from routing or a parent provider).
- [ ] 1.3 Update the `filter-url-sync` logic to parse and stringify `accountIds` in the URL search parameters.
- [ ] 1.4 Ensure URL syncing correctly handles the empty/all state (removing `accountIds` from URL) and multi-select values (comma-separated or multiple keys).

## 2. Filter Component UI Updates

- [ ] 2.1 Locate the Workspace Filter Bar component in the frontend.
- [ ] 2.2 Remove the existing Portfolio dropdown selector from the filter bar.
- [ ] 2.3 Implement and add a new Account multi-select dropdown component to the filter bar.
- [ ] 2.4 Wire the new Account multi-select component to read from and write to the global filter state store (`accountIds`).
- [ ] 2.5 Ensure the dropdown defaults to "All" (empty `accountIds`) and displays the correct available accounts based on the current active portfolio.

## 3. Strategy Scatter Plot Fixes

- [ ] 3.1 Locate the Strategy scatter plot component and its associated data-fetching hook.
- [ ] 3.2 Update the component to consume the active global filter state (e.g., `accountIds`, `date_from`, `date_to`).
- [ ] 3.3 Pass the current global filter parameters into the TanStack Query hook that fetches the scatter plot data.
- [ ] 3.4 Verify the scatter plot correctly refetches and renders when the Account or Date Range filters change.

## 4. Verification & Testing

- [ ] 4.1 Verify the Account multi-select filter syncs to the URL and restores state upon reload.
- [ ] 4.2 Verify the Portfolio dropdown is no longer present in the filter view.
- [ ] 4.3 Verify the Strategy scatter plot updates correctly based on date range and account selection.
- [ ] 4.4 Ensure no TypeScript or linting errors were introduced by the filter state updates.
