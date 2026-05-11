## Why

After the `metadata-library-consolidation` change migrates the UI to the modern `taxonomies` + `annotation_definitions` system and completes the data migration from the legacy tables, the legacy backend code and tests become dead weight. Removing the three legacy stacks (`tags`, `market_phase_definitions`, `checkin_field_definitions`) eliminates ~800–1000 lines of backend code, a dead API surface, and test coverage that no longer maps to live functionality. This change is intentionally gated — it must not be executed until the UI migration and all data migrations are complete and verified.

## What Changes

- **BREAKING: Remove `/api/v1/tags` endpoints and all supporting backend code** (model, schema, repository, service, router registration, FK on `trade_tags`)
- **BREAKING: Remove `/api/v1/market-phases` endpoints and all supporting backend code** (model, schema, repository, service, router registration, FK on `daily_checkins.market_phase_id`)
- **BREAKING: Remove `/api/v1/checkin-fields` endpoints and all supporting backend code** (model, schema, repository, service, router registration, FK on `daily_checkin_values`)
- **Alembic migration: drop legacy tables** (`tags`, `trade_tags`, `market_phase_definitions`, `checkin_field_definitions`, `daily_checkin_values`) — hard irreversible drop
- **Frontend: delete dead hook and component files** (`useTags.ts`, `useCheckinDefinitions.ts` market-phase/checkin-field parts, `TagList.tsx`, `TagBadge.tsx`)
- **Frontend: update all components** that still reference legacy types/hooks to use taxonomy/annotation equivalents
- **Tests: rewrite `CheckinSettings.test.tsx`** to test Market Indexes only (legacy sections gone)
- **Tests: update `global-setup.ts`** to seed taxonomies instead of legacy tags; remove legacy tag seeding
- **Tests: update Playwright specs** that reference legacy tags UI to use taxonomy UI

## Capabilities

### New Capabilities
- `legacy-metadata-removal`: Removal of the three legacy metadata stacks from backend, frontend, and tests

### Modified Capabilities
- `checkin-global-settings`: Remove all remaining test coverage for Market Phases and Custom Metrics sections
- `taxonomy-management`: Playwright tests seed and interact with taxonomies, not legacy tags

## Impact

**Backend (delete/remove)**
- `backend/app/api/v1/tags.py` — delete
- `backend/app/api/v1/market_phases.py` — delete
- `backend/app/api/v1/checkin_fields.py` — delete
- `backend/app/models/tag.py`, `trade_tag.py` — delete
- `backend/app/models/market_phase_definition.py` (if separate file) — delete
- `backend/app/models/checkin_field_definition.py` — delete
- `backend/app/repositories/market_phase_definition_repository.py` — delete
- `backend/app/repositories/checkin_field_definition_repository.py` — delete
- `backend/app/services/market_phase_definition_service.py` — delete
- `backend/app/services/checkin_field_definition_service.py` — delete
- `backend/app/schemas/` — remove market phase and checkin field DTOs
- `backend/app/api/v1/router.py` — unregister three routers
- `backend/app/models/__init__.py` — remove imports
- New Alembic migration: DROP TABLE for all legacy tables (irreversible)

**Frontend (delete/update)**
- `frontend/hooks/useTags.ts` — delete
- `frontend/hooks/useCheckinDefinitions.ts` — remove market phase and checkin field hooks (keep market index hooks)
- `frontend/components/tags/TagList.tsx` — delete
- `frontend/components/tags/TagBadge.tsx` — replace usages with taxonomy badge or delete
- All components importing `useTags` / `TagBadge` — update to taxonomy equivalents

**Tests**
- `frontend/__tests__/components/settings/CheckinSettings.test.tsx` — rewrite to market-indexes-only
- `frontend/tests/global-setup.ts` — replace legacy tag seeding with taxonomy seeding
- `frontend/tests/specs/topbar-navigation.spec.ts` — TC-094 redirect test still valid (URL unchanged)
- `frontend/tests/specs/trades.spec.ts` — TC-077 update to use taxonomy multi-select UI
- Backend pytest files for market phases and checkin fields — delete
