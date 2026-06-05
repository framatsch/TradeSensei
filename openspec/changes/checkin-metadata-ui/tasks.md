# Tasks: checkin-metadata-ui

## Phase 1 — Backend: Generic Annotation Filter utility + Market Regime seed

- [x] 1.1 Create `backend/app/repositories/_annotation_filter.py` — extract `_annotation_value_column_and_value` and `_annotation_operator_expression` from `mcp.py`; add `logic: AND|OR` chaining
- [x] 1.2 Add `AnnotationFilterItem` Pydantic schema to `backend/app/schemas/annotation_filter.py`
- [x] 1.3 Add "Market Regime" `string_enum` default to `AnnotationDefinitionRepository.seed_defaults` (options: Bull, Bear, Chop, Sideways)
- [x] 1.4 Extend `DailyCheckinRepository.list_by_user` — add `taxonomy_ids` and `annotation_filters`; remove `market_phase`/`regime` param
- [x] 1.5 Extend `TradeRepository.list_trades` — add `annotation_filters` using shared utility
- [x] 1.6 Pass new params through `DailyCheckinService` (remove regime) and `TradeService`
- [x] 1.7 Expose `taxonomy_ids` + `annotation_filters` on `GET /api/v1/checkins`; remove `regime` query param
- [x] 1.8 Expose `annotation_filters` on `GET /api/v1/trades`

## Phase 2 — Backend: MCP tools

- [x] 2.1 Add `list_checkins` MCP tool — date range, taxonomy_ids, annotation_filters, pagination; returns taxonomy + annotation assignments per check-in
- [x] 2.2 Add `sync_checkin_metadata` MCP tool — bulk assign taxonomy_ids and annotation values to a list of checkin_ids (upsert)
- [x] 2.3 Extend `search_trades_advanced` MCP tool — add `annotation_filters` input schema and pass to query handler

## Phase 3 — Frontend: Shared components

- [x] 3.1 Create `frontend/components/ui/AnnotationFilterRows.tsx` — definition selector, type-scoped operator dropdown, typed value input (toggle/dropdown/number), AND/OR logic toggle, add/remove row
- [x] 3.2 Create `frontend/components/checkin/AnnotationEditor.tsx` — renders one typed input per AnnotationDefinition (scope=checkins|both); calls assign/update/remove endpoints; buffers for new check-ins

## Phase 4 — Frontend: Check-in Form

- [x] 4.1 Update `CheckinForm.tsx` — remove Market Phase section; add Tags multi-select (assign/remove via taxonomy endpoints, buffer for new)
- [x] 4.2 Update `CheckinForm.tsx` — add Annotations section using `AnnotationEditor`

## Phase 5 — Frontend: Filter bars

- [x] 5.1 Update `CheckinFilterContext.tsx` + `useCheckinParams.ts` — remove regime; add taxonomy_ids + annotation_filters
- [x] 5.2 Update `useCheckins.ts` — pass new filter params to API call
- [x] 5.3 Update `CheckinFilterBar.tsx` — remove regime select; add Tags multi-select + AnnotationFilterRows
- [x] 5.4 Update `TradeFilterBar.tsx` — add AnnotationFilterRows section
- [x] 5.5 Update `WorkspaceFilterBar.tsx` — add AnnotationFilterRows section
- [x] 5.6 Extend `SavedCheckinFilter` schema and `CheckinFilterContext` to persist taxonomy_ids + annotation_filters in saved views

## Phase 6 — OpenAPI sync

- [x] 6.1 Run `openapi-sync` skill to regenerate frontend client types

## Phase 7 — Tests

- [ ] 7.1 Backend unit tests: `_annotation_filter.py` helpers — operator expressions, AND/OR chaining, all 4 type dispatches
- [ ] 7.2 Backend integration tests: `list_by_user` with taxonomy_ids; `list_by_user` with annotation_filters; `list_trades` with annotation_filters
- [ ] 7.3 Backend integration tests: MCP `list_checkins` tool; `sync_checkin_metadata` tool
- [ ] 7.4 Frontend unit tests: `AnnotationFilterRows` — correct operators per type, onChange
- [ ] 7.5 Frontend unit tests: `AnnotationEditor` — renders per type, fires endpoints
- [ ] 7.6 Playwright E2E: assign tag + annotation on check-in form; filter check-ins by tag; filter check-ins by annotation; filter trades by annotation
