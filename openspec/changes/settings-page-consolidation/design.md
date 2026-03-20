## Context

The app currently has three separate pages for account and broker management:
- `/dashboard/accounts` — lists trading accounts, lets users create/rename/delete them.
- `/dashboard/connections` — shows only the Schwab OAuth card (`SchwabConnectionCard`).
- No page exists at all for IBKR Flex Query credential management.

User preferences (theme, date range) exist in the frontend via `next-themes` but are not persisted on the server; they reset on new devices or browsers. The backend has no concept of per-user UI settings.

The `BrokerConnection` model is Schwab-specific in spirit (column naming: `access_token`, `refresh_token`, `token_expires_at` all reflect OAuth semantics). IBKR Flex uses a permanent static token + a query ID — no OAuth lifecycle. The model works structurally for IBKR too, but requires `token_expires_at` to be made nullable.

## Goals / Non-Goals

**Goals:**
- Consolidate account management and broker credential management into one `/dashboard/settings` page with two tabs.
- Add IBKR Flex Query credential management (connect / disconnect / status).
- Persist user UI preferences (theme, default date range) server-side via a new `UserSetting` key-value model.
- Apply `default_date_range` setting as the initial filter on the trades page and dashboard when no URL params are present.
- Remove the now-redundant `/dashboard/accounts` and `/dashboard/connections` routes and nav items.
- Replace them with a single "Settings" nav entry (gear icon, bottom of sidebar).

**Non-Goals:**
- Multi-account IBKR (one connection per user is sufficient by design).
- OAuth-style token refresh for IBKR (Flex tokens are long-lived and manually managed by the user).
- Migrating Schwab `BrokerConnection` to a different structure (keep as-is).
- Adding more user settings beyond theme and default_date_range in this iteration.

## Decisions

### D1: Reuse `BrokerConnection` for IBKR instead of a new model

**Decision:** Store IBKR credentials in the existing `broker_connections` table with `broker="ibkr"`, using `access_token` for the Flex Token and `refresh_token` for the Flex Query ID.

**Rationale:** Both Schwab and IBKR ultimately represent "a set of encrypted credentials that grant access to a broker API". Creating a separate model would duplicate all the encryption/decryption and status-check patterns. The column names are semantically imprecise for IBKR but the types are identical (encrypted text strings). This is an acceptable trade-off for one iteration.

**Alternative considered:** A new `AccountProperty` model on the `Account` level. Rejected because IBKR is a user-level connection (one per user, like Schwab), not an account-level property.

**Migration needed:** `token_expires_at` must become nullable (ALTER TABLE migration). Existing Schwab rows are unaffected.

### D2: `UserSetting` as a flat key-value table (not JSON column on User)

**Decision:** Separate `user_settings` table with one row per key.

**Rationale:** A JSON column on `User` would make individual key updates awkward (read-modify-write the entire JSON blob). A flat key-value table allows targeted upserts per key and is simpler to query. With only 2-3 keys in scope, the overhead is negligible.

**Alternative considered:** JSONB column on `users` table. Rejected because it requires full-blob updates and complicates partial updates on the API level.

### D3: Settings page is tab-based, not nested routes

**Decision:** Implement tabs as client-side state (not separate Next.js routes like `/dashboard/settings/general`).

**Rationale:** The settings content is lightweight and doesn't need deep-linkable URLs in this iteration. Tab state in the URL (e.g. `?tab=integrations`) can be added later without schema changes. Client-side tabs are simpler to implement and test.

### D4: IBKR connect endpoint is a simple credential upsert (not OAuth)

**Decision:** `POST /broker/ibkr/connect` takes `{ flex_query_id, flex_token }` and stores them immediately. No redirect flow.

**Rationale:** IBKR Flex credentials are static secrets the user copies from the IBKR web portal. There is no redirect-based authorization flow. A simple form POST is the correct pattern.

### D5: General settings applied as initial URL params, not via context override

**Decision:** When the trades page loads with no URL params, the `TradesPageClient` reads `useSettings()` and, if `default_date_range` is set, synthesizes the appropriate `opened_at_from` into its initial filter state.

**Rationale:** The existing URL-first filter architecture is sound. The settings only provide a *default*; the user can override at any time. This avoids adding a global filter context that conflicts with URL state.

## Risks / Trade-offs

- **IBKR column naming mismatch** (`refresh_token` stores a Query ID): If a future engineer reads the DB schema without context, this is confusing. Mitigation: clear column comments in the model and schema docstrings.
- **`token_expires_at` nullable breaks strict Schwab assertions**: Code that assumes this column is always set for all `BrokerConnection` rows may break. Mitigation: grep for usages before migration and add None-guards.
- **Settings page removes two nav items**: Users bookmarking `/dashboard/accounts` will hit a 404. Mitigation: add a redirect from the old paths to `/dashboard/settings`.

## Migration Plan

1. Alembic: `ALTER TABLE broker_connections ALTER COLUMN token_expires_at DROP NOT NULL`
2. Alembic: `CREATE TABLE user_settings (id, user_id, key, value, created_at, updated_at)`
3. Deploy backend.
4. Deploy frontend (old routes redirect to `/dashboard/settings`).
5. No data migration required — existing Schwab connections are unaffected.

## Open Questions

- Should the `default_date_range` setting also affect the Dashboard overview page (equity curve / metrics period selector)? → Assumed yes for this iteration.
