## 1. Backend — Database & Models

- [x] 1.1 Create `UserSetting` SQLAlchemy model (`backend/app/models/user_setting.py`) with fields: `id`, `user_id` (FK → users, CASCADE), `key`, `value`, `created_at`, `updated_at`
- [x] 1.2 Add `user_settings` relationship to `User` model (`backend/app/models/user.py`)
- [x] 1.3 Register `UserSetting` in `backend/app/models/__init__.py`
- [x] 1.4 Generate Alembic migration: make `broker_connections.token_expires_at` nullable
- [x] 1.5 Generate Alembic migration: create `user_settings` table with index on `(user_id, key)` unique constraint

## 2. Backend — Pydantic Schemas

- [x] 2.1 Create `UserSettingsRead` and `UserSettingsUpdate` schemas in `backend/app/schemas/user.py` — fixed keys `theme` (literal `"system"|"light"|"dark"`) and `default_date_range` (literal `"all"|"ytd"|"last30"`)
- [x] 2.2 Add `IBKRConnectRequest` schema to `backend/app/schemas/broker.py` with `flex_query_id: str` (min_length=1) and `flex_token: str` (min_length=1)

## 3. Backend — Services

- [x] 3.1 Add `get_settings(user_id)` method to `UserService` — reads `user_settings` rows, merges with defaults, returns `UserSettingsRead`
- [x] 3.2 Add `update_settings(user_id, update)` method to `UserService` — upserts changed keys, returns updated `UserSettingsRead`
- [x] 3.3 Add `connect_ibkr(user_id, flex_query_id, flex_token)` method to `BrokerService` — encrypts credentials, upserts `BrokerConnection` with `broker="ibkr"`, `token_expires_at=None`
- [x] 3.4 Add guard in `BrokerService` token-refresh logic to skip rows where `broker="ibkr"` or `token_expires_at is None`

## 4. Backend — API Routes

- [x] 4.1 Add `GET /users/me/settings` route to `backend/app/api/v1/users.py` calling `UserService.get_settings`
- [x] 4.2 Add `PUT /users/me/settings` route to `backend/app/api/v1/users.py` calling `UserService.update_settings`
- [x] 4.3 Add `POST /broker/ibkr/connect` route to `backend/app/api/v1/broker.py` calling `BrokerService.connect_ibkr`, returns `BrokerStatusResponse`
- [x] 4.4 Verify `GET /broker/ibkr/status` and `DELETE /broker/ibkr` work correctly via existing generic broker routes (manual check / test)

## 5. Frontend — API Client & Hooks

- [x] 5.1 Regenerate the OpenAPI TypeScript client after backend changes (`openapi-sync` skill or `npm run generate-api`)
- [x] 5.2 Create `frontend/hooks/useSettings.ts` — React Query hook for `GET/PUT /users/me/settings` with optimistic updates
- [x] 5.3 Create `frontend/hooks/useIBKRConnection.ts` — React Query hook wrapping `POST /broker/ibkr/connect`, `GET /broker/ibkr/status`, `DELETE /broker/ibkr`

## 6. Frontend — Settings Page Structure

- [x] 6.1 Create `frontend/app/dashboard/settings/page.tsx` with two tabs ("General" and "Accounts & Integrations") using client-side tab state
- [x] 6.2 Add redirect from `/dashboard/accounts` → `/dashboard/settings` (`frontend/app/dashboard/accounts/page.tsx` replaced with a `redirect()` call)
- [x] 6.3 Add redirect from `/dashboard/connections` → `/dashboard/settings` (`frontend/app/dashboard/connections/page.tsx` replaced with a `redirect()` call)
- [x] 6.4 Update `frontend/app/dashboard/layout.tsx` sidebar: remove "Accounts" and "Connections" nav items, add "Settings" entry with gear icon (bottom of nav)

## 7. Frontend — General Tab

- [x] 7.1 Create `frontend/components/settings/GeneralSettings.tsx` — theme segmented control (System/Light/Dark) wired to `useSettings` and `next-themes`
- [x] 7.2 Add default date range dropdown (All Time / Year to Date / Last 30 Days) to `GeneralSettings.tsx`, saving via `useSettings`

## 8. Frontend — Accounts & Integrations Tab

- [x] 8.1 Create `frontend/components/settings/AccountSettings.tsx` — renders existing account list logic (reuse components from deleted `/dashboard/accounts`)
- [x] 8.2 Create `frontend/components/settings/IBKRConnectionCard.tsx` — disconnected state: form with Flex Query ID + Token inputs + Connect button; connected state: status badge + Disconnect button
- [x] 8.3 Create `frontend/components/settings/BrokerIntegrations.tsx` — renders `IBKRConnectionCard` and the existing `SchwabConnectionCard` side by side
- [x] 8.4 Compose `AccountSettings` and `BrokerIntegrations` into the Accounts & Integrations tab of the settings page

## 9. Frontend — Apply Default Date Range

- [x] 9.1 Update `frontend/app/dashboard/trades/TradesPageClient.tsx` — on initial load with no URL params, read `default_date_range` from `useSettings` and set `opened_at_from` accordingly
- [x] 9.2 Apply the same logic to the dashboard overview page if a date range selector exists there
