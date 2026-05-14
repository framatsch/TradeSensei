## 0. Pre-Conditions Gate (verify before starting any task)

- [x] 0.1 Confirm `tags` table is empty in the target environment (run `SELECT COUNT(*) FROM tags`)
- [x] 0.2 Confirm `market_phase_definitions` table is empty
- [x] 0.3 Confirm `checkin_field_definitions` and `daily_checkin_values` tables are empty
- [x] 0.4 Confirm Check-in form no longer depends on `/api/v1/market-phases` (phase selection migrated)
- [x] 0.5 Confirm `metadata-library-consolidation` change is deployed and verified

## 1. Backend — Remove Legacy Tag Stack

- [x] 1.1 Delete `backend/app/api/v1/tags.py`
- [x] 1.2 Delete `backend/app/models/tag.py` and `backend/app/models/trade_tag.py`
- [x] 1.3 Delete `backend/app/repositories/tag_repository.py` and `backend/app/services/tag_service.py`
- [x] 1.4 Remove tag-related schema fields from `backend/app/schemas/trade.py` (tag list in TradeRead/TradeUpdate)
- [x] 1.5 Remove tag import and router registration from `backend/app/api/v1/router.py`
- [x] 1.6 Remove `Tag`, `TradeTag` imports from `backend/app/models/__init__.py`
- [x] 1.7 Update `backend/app/repositories/trade_repository.py` — remove tag join/eager-load logic
- [x] 1.8 Update `backend/app/services/trade_service.py` — remove tag assignment logic

## 2. Backend — Remove Legacy Market Phase Stack

- [x] 2.1 Delete `backend/app/api/v1/market_phases.py`
- [x] 2.2 Delete or clean `backend/app/models/` market phase definition model (if in separate file; else remove from shared file)
- [x] 2.3 Delete `backend/app/repositories/market_phase_definition_repository.py`
- [x] 2.4 Delete `backend/app/services/market_phase_definition_service.py`
- [x] 2.5 Remove market phase imports/router from `backend/app/api/v1/router.py`

## 3. Backend — Remove Legacy Checkin Field Stack

- [x] 3.1 Delete `backend/app/api/v1/checkin_fields.py`
- [x] 3.2 Delete checkin field definition model (remove from ORM / delete file)
- [x] 3.3 Delete `backend/app/repositories/checkin_field_definition_repository.py`
- [x] 3.4 Delete `backend/app/services/checkin_field_definition_service.py`
- [x] 3.5 Remove checkin field imports/router from `backend/app/api/v1/router.py`
- [x] 3.6 Remove `CheckinFieldDefinition` from `backend/app/models/__init__.py`

## 4. Backend — Update Analytics to Use Taxonomies

- [x] 4.1 Update `backend/app/repositories/analytics_repository.py` — replace `trade_tags`/`tags` joins with `trade_taxonomies`/`taxonomies` joins
- [x] 4.2 Update `backend/app/repositories/attribution_repository.py` — same replacement
- [x] 4.3 Update `backend/app/services/analytics_service.py` — replace any tag-specific logic with taxonomy equivalents
- [x] 4.4 Update `backend/app/schemas/analytics.py` — replace `TagRead` references with `TaxonomyRead` or equivalent

## 5. Backend — Alembic Migration (Drop Legacy Tables)

- [x] 5.1 Write Alembic migration that checks all legacy tables are empty before dropping; abort with error if not
- [x] 5.2 Add DROP TABLE statements for: `trade_tags`, `tags`, `market_phase_definitions`, `checkin_field_definitions`, `daily_checkin_values`

## 6. Backend — Delete Test Files

- [x] 6.1 Delete `backend/tests/test_tag_service.py`
- [x] 6.2 Delete `backend/tests/test_tag_ownership.py`
- [x] 6.3 Delete `backend/tests/test_market_phases_api.py`
- [x] 6.4 Delete `backend/tests/test_checkin_fields.py`
- [x] 6.5 Run full backend test suite and fix any remaining failures from legacy references

## 7. Frontend — Regenerate OpenAPI Client

- [x] 7.1 Run `openapi-sync` to regenerate the TypeScript client after backend endpoints are removed
- [x] 7.2 Fix any TypeScript compile errors caused by removed types (tag-related fields in TradeRead, etc.)

## 8. Frontend — Delete Dead Files and Update Components

- [x] 8.1 Delete `frontend/hooks/useTags.ts`
- [x] 8.2 Remove `useMarketPhases`, `useCreateMarketPhase`, `useUpdateMarketPhase`, `useCheckinFields`, `useCreateCheckinField`, `useUpdateCheckinField` exports from `frontend/hooks/useCheckinDefinitions.ts`
- [x] 8.3 Delete `frontend/components/tags/TagList.tsx`
- [x] 8.4 Delete `frontend/components/tags/TagBadge.tsx` (or repurpose as a taxonomy badge if still used elsewhere)
- [x] 8.5 Update any component that imports `TagBadge` (e.g. `TradeRow`, `TradeFilterBar`) to use a taxonomy badge component
- [x] 8.6 Run `npm run build` and fix all TypeScript/import errors

## 9. Frontend — Rewrite CheckinSettings Unit Test

- [x] 9.1 Rewrite `frontend/__tests__/components/settings/CheckinSettings.test.tsx` — mock only `useMarketIndexes`, `useCreateMarketIndex`, `useUpdateMarketIndex`, `useDeleteMarketIndex`; assert Market Phases and Custom Metrics sections are absent
- [x] 9.2 Add a test case: clicking add button opens the market index form with symbol/name/URL inputs
- [x] 9.3 Add a test case: delete market index calls the delete hook

## 10. Frontend — Update Playwright Tests

- [x] 10.1 Update `frontend/tests/global-setup.ts` — replace legacy tag seeding with taxonomy seeding via `POST /api/v1/taxonomies` with `scope=trades`
- [x] 10.2 Update TC-077 in `frontend/tests/specs/trades.spec.ts` to interact with the taxonomy multi-select instead of the legacy tag picker
- [x] 10.3 Verify TC-094 in `frontend/tests/specs/topbar-navigation.spec.ts` still passes (URL redirect unchanged)
- [x] 10.4 Run the full Playwright suite and fix any remaining legacy references
