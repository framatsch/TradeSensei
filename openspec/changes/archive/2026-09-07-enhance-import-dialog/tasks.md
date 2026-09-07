## 1. UI Component Updates

- [x] 1.1 Locate `ImportDateRange.tsx` (or the equivalent file managing the date selection for Schwab/IBKR imports).
- [x] 1.2 Add a Select/Dropdown UI component to the date selection step.
- [x] 1.3 Populate the dropdown with options: "Last 7 days", "Last 30 days", "Last 90 days", "Last 180 days", "Last 360 days", "Month to date", "Year to date".

## 2. Logic Implementation

- [x] 2.1 Implement an `onChange` handler for the dropdown.
- [x] 2.2 Calculate the new start date based on the selected option using the current date (`new Date()`).
- [x] 2.3 Update the underlying date picker state with the calculated start date.

## 3. Account Auto-Selection Implementation

- [x] 3.1 Locate the component where the account list is fetched and the account selection state is managed (e.g., `ImportForm.tsx`).
- [x] 3.2 Add logic to check if the fetched accounts array has a length of exactly 1.
- [x] 3.3 If there is only one account, automatically set the selected account ID to that account's ID.

## 4. Testing

- [x] 4.1 Verify that selecting each date option correctly updates the date picker.
- [x] 4.2 Verify that if a user has exactly one account, it is pre-selected when opening the import dialog.
- [x] 4.3 Verify that if a user has multiple accounts, no account is pre-selected.
- [x] 4.4 Ensure that the overall import flow (payload structure) remains unaffected and imports successfully.
