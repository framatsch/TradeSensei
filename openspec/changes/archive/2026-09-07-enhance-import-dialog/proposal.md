## Why

Users currently have to manually pick a start date in the date picker and manually select an account when importing trades. This is tedious. Adding quick-selection options for dates and automatically selecting the account (when only one exists) will speed up the workflow and improve the user experience of the import dialog.

## What Changes

- Add a dropdown menu (or similar select UI component) to the existing unified import dialog used for both Schwab and IBKR imports (specifically during the date selection step).
- The dropdown will contain pre-defined timeframe options:
  - Last 7 days
  - Last 30 days
  - Last 90 days
  - Last 180 days
  - Last 360 days
  - Month-to-date (Seit Monatsanfang)
  - Year-to-date (Seit Jahresanfang)
- Selecting an option from the dropdown will automatically update the underlying start date value in the date picker.
- Automatically select the first account in the account dropdown if the user only has exactly one account in their portfolio.

## Capabilities

### New Capabilities

- `import-date-presets`: Pre-defined date selections for the import dialog.
- `import-account-autoselect`: Automatically select the account if only one exists.

### Modified Capabilities

- (None)

## Impact

- Frontend: `ImportDateRange.tsx` (and potentially `ImportForm.tsx`) will be modified to include the new dropdown, state handling, and the logic to auto-select the account when only one is available.
- UX: Faster date selection and reduced click overhead for single-account users during the import flow.
