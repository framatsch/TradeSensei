## Context

After `metadata-library-consolidation` completes, three legacy metadata stacks become orphaned:
- `tags` / `trade_tags` — trade-only labels, previously managed in Library > Tags
- `market_phase_definitions` / `daily_checkins.market_phase_id` — check-in phase labels
- `checkin_field_definitions` / `daily_checkin_values` — custom check-in variables

These tables, their API endpoints, services, repositories, and tests must be removed. The removal is **irreversible** — it involves dropping database tables via Alembic and deleting source files. This change must only run after:
1. `metadata-library-consolidation` is complete and deployed
2. All legacy data has been migrated to `taxonomies` / `annotation_definitions`
3. The Check-in form has been updated to use `taxonomies` for phase selection (out of scope for consolidation change)
4. All production data in legacy tables is confirmed migrated or intentionally discarded

**Coupling depth is higher than expected:** Legacy tags are referenced in `trade_service.py`, `analytics_service.py`, `attribution_service.py`, `trade_repository.py`, and `analytics_repository.py` — not just the tags API. Each must be surgically updated.

## Goals / Non-Goals

**Goals:**
- Delete all backend code for `tags`, `market_phase_definitions`, `checkin_field_definitions`
- Drop legacy DB tables via Alembic migration
- Delete dead frontend hooks and components
- Rewrite `CheckinSettings.test.tsx` to cover Market Indexes only
- Update Playwright global-setup to seed taxonomies instead of legacy tags
- Update TC-077 (trade tags test) to interact with the taxonomy multi-select UI

**Non-Goals:**
- Changing the Check-in form's phase selection mechanism (separate change)
- Removing `daily_checkins` itself or its `market_phase_id` FK column until Check-in form migration is complete
- Removing `useCheckinDefinitions.ts` entirely — the Market Indexes hooks within it are still needed

## Decisions

### Decision 1: Drop legacy DB tables in a single irreversible Alembic migration

All five legacy tables (`tags`, `trade_tags`, `market_phase_definitions`, `checkin_field_definitions`, `daily_checkin_values`) are dropped in one migration. No soft-delete or transition period — by the time this change runs, data has already been migrated.

**Prerequisite guard:** The migration SHOULD check that `tags`, `market_phase_definitions`, and `checkin_field_definitions` are empty before dropping. If rows remain, it raises an error and aborts. This prevents accidental data loss.

### Decision 2: `market_phase_id` FK on `daily_checkins` is dropped with the parent table

Dropping `market_phase_definitions` cascades to `daily_checkins.market_phase_id` column removal. The Check-in model and schema must have this FK removed before this migration runs. If the Check-in form migration hasn't happened yet, this change is blocked.

**Alternative:** Leave `market_phase_id` column as nullable orphan. Rejected — leaves schema debris.

### Decision 3: Remove market phase / checkin field hooks from `useCheckinDefinitions.ts`, keep market index hooks

`useCheckinDefinitions.ts` is a multi-purpose hook file. Only the market phase and checkin field hooks are removed. Market index hooks (`useMarketIndexes`, etc.) remain because Settings > Check-in still uses them.

### Decision 4: Backend analytics references to legacy tags are replaced with taxonomy queries

`analytics_service.py` and `attribution_service.py` reference `tag_id` / `trade_tags`. These must be updated to use `trade_taxonomies` / `taxonomy_id`. This is the highest-risk part of this change — analytics correctness must be verified by tests.

## Risks / Trade-offs

- **[Risk] Analytics break after tag → taxonomy swap** → Mitigation: Existing analytics test suite must pass before merge; add explicit tests for taxonomy-based attribution.
- **[Risk] Migration drops non-empty tables** → Mitigation: Pre-drop row count check in migration; abort if any rows exist.
- **[Risk] Check-in form breaks because `market_phase_id` column is dropped before form is migrated** → Mitigation: Hard blocker — this change MUST NOT run until the Check-in form migration is complete.
- **[Risk] `daily_checkin_values` drop breaks check-in read endpoints** → Mitigation: Check-in custom field values must also be migrated to `checkin_annotations` first.

## Migration Plan

**Pre-conditions (verify before running):**
1. `metadata-library-consolidation` deployed ✓
2. Legacy `tags` table empty (data copied to `taxonomies`) ✓
3. Legacy `market_phase_definitions` table empty (data copied to `taxonomies`) ✓
4. Legacy `checkin_field_definitions` table empty (data copied to `annotation_definitions`) ✓
5. Check-in form updated to use taxonomy for phase selection ✓
6. `daily_checkin_values` data migrated to `checkin_annotations` ✓

**Steps:**
1. Remove legacy code from backend (services, repos, schemas, models, API routers)
2. Write Alembic migration with pre-drop guards and table drops
3. Update analytics/attribution service to use taxonomy tables
4. Regenerate OpenAPI client
5. Remove dead frontend files and update components
6. Rewrite unit and Playwright tests

**Rollback:** Not possible once migration runs (destructive). Rollback requires restoring from backup.

## Open Questions

- **Q1: Is `daily_checkin_values` the correct table name for check-in field values?** Verify against actual schema — the model name in code may differ from the table name.
- **Q2: Does `attribution_service.py` use legacy tags for performance attribution charts?** If yes, the attribution analytics must be re-tested after switching to taxonomies to ensure chart data is equivalent.
