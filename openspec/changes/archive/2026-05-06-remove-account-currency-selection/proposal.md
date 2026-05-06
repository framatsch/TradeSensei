## Why

Currently, when creating an account, the user is prompted to select a currency. However, the currency is already defined at the portfolio level (as `base_currency`), and all accounts within that portfolio should inherit it. Allowing users to select an account currency creates redundancy, confusion, and potential data inconsistency between the account and its parent portfolio. Removing this selection streamlines account creation and enforces a single source of truth for currency.

## What Changes

- **BREAKING**: Remove `currency` from `AccountCreate` schema payload.
- Update the backend account creation logic to automatically inherit the `base_currency` from the provided `portfolio_id`.
- **BREAKING**: Remove the currency selection field from the frontend account creation form and edit forms.
- Make the `currency` property read-only on the frontend if displayed.
- Remove `currency` from `AccountUpdate` as it should no longer be editable.

## Capabilities

### New Capabilities
<!-- No new capabilities being introduced -->

### Modified Capabilities
- `account-management`: Modify Account Creation scenario to inherit currency from portfolio and remove manual currency selection.

## Impact

- **Backend**: `AccountCreate` and `AccountUpdate` schemas in `backend/app/schemas/account.py`. `AccountService.create` to inherit portfolio's `base_currency`.
- **Frontend**: `AccountCreateForm`, `AccountEditForm` in `frontend/src/components/account/...`.
- **Database**: The `accounts.currency` column will still exist but its value will be derived and kept in sync with the portfolio, or it could potentially be removed if it's completely redundant (though keeping it might be safer for existing code/migrations).
