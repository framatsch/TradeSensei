## Context

Two independent changes are bundled here because both are small, well-scoped, and touch overlapping layers (settings infrastructure, trade list filtering):

1. **Model Book removal**: The star/bookmark feature (`is_modelbook` on Trade and DailyCheckin) is superseded by Taxonomy. It has its own API endpoints, service, repository, schema, and frontend components. Existing starred data exists in the DB but no longer needs to be surfaced.

2. **Trade Status UI Setting**: Users want control over whether open trades appear in dashboard/workspace views. This is a per-user preference (not an env flag) that lives alongside existing UI settings (theme, default_date_range, features).

## Goals / Non-Goals

**Goals:**
- Remove all Model Book code paths end-to-end (DB → API → Frontend)
- Add `show_open_trades` boolean to user settings, default `false`
- When off: trade lists always query with `status=closed`; filter toggle hidden
- When on: trade lists show all trades; Open/Closed/All filter toggle visible
- Saved filter state with `status=open/closed` is silently overridden at query time when setting is off
- Info banner shown when a URL/saved filter contains `status=open` but setting is off
- Help page updated to document the setting

**Non-Goals:**
- Migrating or exporting existing Model Book starred data (columns dropped, data lost)
- Taxonomy implementation (separate change)
- Changing filter persistence mechanism

## Decisions

### 1. Drop `is_modelbook` columns with Alembic migration (no data preservation)

**Decision:** Drop columns directly, no data export or soft-delete.

**Rationale:** The Taxonomy system is the replacement. Migrating star flags to taxonomy entries would create orphaned data with no semantic meaning in the new system. Users can re-classify their important trades via Taxonomy.

**Alternative considered:** Soft-delete (keep column, ignore in API) — rejected because it leaves dead schema weight and confuses future developers.

### 2. `show_open_trades` as a user setting key in `features` dict (not a new top-level field)

**Decision:** Add `show_open_trades` to the existing `features: dict[str, bool]` field in `UserSettings`, not as a new top-level boolean.

**Rationale:** The `features` dict already handles per-user boolean toggles with no schema migration needed. Adding a top-level field would require an Alembic migration on the `users` table. The `features` dict is stored as JSONB — zero migration cost.

**Alternative considered:** New top-level column on users table — rejected due to unnecessary migration complexity for a simple boolean.

### 3. Silent override at query time, not at filter-state level

**Decision:** When `show_open_trades = false`, the `status` parameter is stripped from the API call at the hook/query level. Filter state in URL/memory is not mutated.

**Rationale:** Keeps filter state reversible. If user enables the setting, their previous filter is restored automatically. No data mutation, no migration of saved filters.

**Info banner:** When `show_open_trades = false` AND the URL contains `status=open`, show a dismissible info banner: *"Open trades are hidden. Enable 'Show Open Trades' in Settings → UI to show them."* This prevents silent confusion from bookmarked URLs.

### 4. Setting placed in `FeaturesSettings` component (renamed "UI Settings")

**Decision:** Add `show_open_trades` toggle to `FeaturesSettings.tsx` alongside the existing feature flags (Risk Analytics, Cash & Dividends, Tax Report). No new settings section needed.

**Rationale:** The existing `FeaturesSettings` component already has the deferred Apply pattern and the correct infrastructure. The component label can remain "Features" or be renamed "UI Settings" — cosmetic choice left to implementer.

### 5. Filter toggle affects all trade list surfaces

**Decision:** The Open/Closed/All filter toggle is conditionally rendered in every trade list that has a status filter: `TradesPageClient`, workspace trade tables, dashboard trade widgets.

**Rationale:** Consistency — the setting should behave identically everywhere. Partial application would confuse users.

## Risks / Trade-offs

- **Data loss on Model Book drop**: Users lose their starred trades/check-ins permanently. → Acceptable since Taxonomy replaces this; document in changelog.
- **`features` dict as catch-all**: Using the generic `features` dict for a UI-specific setting mixes concerns slightly. → Acceptable short-term; a dedicated `ui` settings namespace could be introduced later.
- **Info banner UX**: Banner needs to be non-intrusive but visible enough to explain the discrepancy. → Use the existing info/toast pattern already in the codebase.

## Migration Plan

1. Write Alembic migration: drop `is_modelbook` from `trades` and `daily_checkins`
2. Remove backend Model Book code (api, service, repository, schema)
3. Remove `is_modelbook` from Trade/Checkin response schemas
4. Remove frontend Model Book components and hooks
5. Remove Model Book library route (redirect or 404)
6. Add `show_open_trades` to settings infrastructure (backend: no migration needed; frontend: featureFlags + FeaturesSettings)
7. Add query-time override in all trade list hooks
8. Add info banner component for status=open + setting=off case
9. Update Help page
10. Update OpenAPI client (openapi-sync)

**Rollback:** Re-add `is_modelbook` columns via Alembic downgrade. Frontend rollback via git revert. The `show_open_trades` setting key can be ignored without any cleanup.

## Open Questions

- None — all decisions resolved above.
