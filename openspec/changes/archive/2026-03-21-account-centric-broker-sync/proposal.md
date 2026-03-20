## Why

Currently, broker credentials (like IBKR tokens or Schwab keys) are stored globally in a `broker_connections` table per user. This assumes one connection per broker across the entire application. By moving towards app keys and secrets for Schwab (and using Flex queries for IBKR), we need to tie these credentials to specific accounts, allowing users to have multiple accounts with different keys for the same broker. Shifting to an account-centric credential model enables true multi-account support and simplifies synchronization logic.

## What Changes

- Deprecate the global `BrokerConnection` model and drop its table.
- Introduce an explicit `type` column to the `Account` model (e.g., MANUAL, SCHWAB, IBKR).
- Add an `AccountProperty` model to securely store encrypted key-value pairs (API credentials) tied to a specific account via Fernet encryption.
- **BREAKING**: Refactor the Backend Broker API so that sync actions are scoped to `account_id` instead of a user-level global connection.
- Redesign the Account Settings UI to let users select an account type and securely input their API credentials when adding/editing an account.
- Revamp the `/dashboard/import` page to enforce account selection first, and dynamically show API sync or file upload options based on the chosen account's type.

## Capabilities

### New Capabilities
- `account-centric-broker-sync`: The ability to sync trades directly via APIs using encrypted credentials tied directly to an individual trading account.

### Modified Capabilities
- `account-management`: Adding explicit account types (MANUAL, SCHWAB, IBKR) and securely managing encrypted properties (App Keys, Flex Tokens).
- `trade-import`: Moving from a generalized import page to an account-first UI flow with dynamic sync vs upload options based on account type.

## Impact

- **Database**: Dropping `broker_connections`, modifying `accounts`, and creating `account_properties`.
- **Backend API**: Refactoring `/api/v1/broker/sync` and `/api/v1/accounts`. Requires Pydantic schema changes.
- **Frontend UI**: Complete rewrite of the `/dashboard/import` page and updates to `/dashboard/settings` Account management modals.
- **Dependencies**: Uses the existing Python `cryptography` (Fernet) package, applied differently.