## Why

Account management, broker connections (Schwab OAuth, IBKR Flex), and UI preferences are scattered across separate pages (`/dashboard/accounts`, `/dashboard/connections`) and partially missing from the UI entirely (IBKR credentials, theme toggle, date range defaults). This creates a fragmented user experience and an inconsistent backend architecture where broker integrations lack a unified abstraction. Consolidating everything into a single Settings page — with clearly separated tabs — is the right moment to unify the data model and eliminate the scattered navigation.

## What Changes

- **New**: `/dashboard/settings` page with two tabs: **General** and **Accounts & Integrations**.
- **New**: `UserSetting` DB model (key-value store per user for UI preferences: theme, default date range).
- **New**: `GET /users/me/settings` and `PUT /users/me/settings` API endpoints.
- **Modified**: `BrokerConnection` model — `token_expires_at` becomes nullable to support IBKR Flex Queries (which do not have short-lived OAuth expiry cycles).
- **New**: `POST /broker/ibkr/connect` endpoint — accepts `flex_query_id` + `flex_token`, stores them encrypted in `BrokerConnection` (broker=`"ibkr"`, access_token=token, refresh_token=query_id).
- **Removed**: `/dashboard/accounts` page (functionality moved into Settings → Accounts & Integrations tab).
- **Removed**: `/dashboard/connections` page (functionality moved into Settings → Accounts & Integrations tab).
- **Modified**: Sidebar navigation — replaces separate "Accounts" and "Connections" links with a single "Settings" entry (gear icon).
- **Modified**: Dashboard and Trade list — apply `default_date_range` user setting as the initial filter when no URL params are present.

## Capabilities

### New Capabilities

- `user-settings`: Key-value user preferences store (theme, default date range) — backend model, service, API endpoints, and frontend hook.
- `ibkr-broker-connection`: IBKR Flex Query credential management — connect/disconnect via the unified `BrokerConnection` table.
- `settings-page`: Unified frontend Settings page with General and Accounts & Integrations tabs, replacing the standalone accounts and connections pages.

### Modified Capabilities

- `broker-connection`: `token_expires_at` becomes nullable to accommodate non-OAuth broker integrations (IBKR). Existing Schwab behaviour is unchanged.

## Impact

- **Backend models**: New `UserSetting` model; migration for nullable `token_expires_at` on `BrokerConnection`.
- **Backend API**: New routes in `users.py` (settings); new route in `broker.py` (IBKR connect).
- **Backend services**: New `user_settings` logic in `user_service.py`; new IBKR connect logic in `broker_service.py`.
- **Frontend routes**: New `app/dashboard/settings/`; delete `app/dashboard/accounts/` and `app/dashboard/connections/`.
- **Frontend components**: New `components/settings/` directory with `GeneralSettings`, `AccountSettings`, `IBKRConnectionCard`, reuse of `SchwabConnectionCard`.
- **Frontend hooks**: New `useSettings` hook for user settings API.
- **Navigation**: `app/dashboard/layout.tsx` sidebar updated.
- **No breaking API changes** for existing Schwab OAuth flow or trade import endpoints.
