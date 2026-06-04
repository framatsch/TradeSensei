# Tasks: checkin-metadata-ui

## Phase 1 — Backend: Generic Annotation Filter utility

- [ ] 1.1 Create `backend/app/repositories/_annotation_filter.py` — extract `_annotation_value_column_and_value` and `_annotation_operator_expression` helpers from `mcp.py`; add support for `logic: AND | OR` chaining
- [ ] 1.2 Add `AnnotationFilterItem` Pydantic schema to `backend/app/schemas/` (fields: `annotation_definition_id`, `operator`, `value`, `logic`)
- [ ] 1.3 Extend `DailyCheckinRepository.list_by_user` with `taxonomy_ids` and `annotation_filters` params using the shared utility
- [ ] 1.4 Extend `TradeRepository.list_trades` with `annotation_filters` param using the shared utility
- [ ] 1.5 Pass new params through `DailyCheckinService` and `TradeService`
- [ ] 1.6 Expose `taxonomy_ids` and `annotation_filters` as query params on `GET /api/v1/checkins`
- [ ] 1.7 Expose `annotation_filters` as query param on `GET /api/v1/trades`
- [ ] 1.8 Expose `annotation_filters` on the Workspace filter endpoint (if applicable)

## Phase 2 — Frontend: Check-in Form

- [ ] 2.1 Create `frontend/components/checkin/AnnotationEditor.tsx` — renders a typed input per AnnotationDefinition; calls assign/update/remove endpoints on change; buffers for new check-ins
- [ ] 2.2 Update `CheckinForm.tsx` — add Tags multi-select section (assign/remove via taxonomy endpoints, buffer for new check-ins)
- [ ] 2.3 Update `CheckinForm.tsx` — add Annotations section using `AnnotationEditor`

## Phase 3 — Frontend: Shared AnnotationFilterRows component

- [ ] 3.1 Create `frontend/components/ui/AnnotationFilterRows.tsx` — definition selector, type-aware operator dropdown, typed value input, AND/OR toggle, add/remove row controls
- [ ] 3.2 Wire up `useAnnotationDefinitions` hook (or extend existing) to fetch definitions by scope for the filter UI

## Phase 4 — Frontend: Filter bars

- [ ] 4.1 Extend `CheckinFilterContext` and `useCheckinParams` — add `taxonomy_ids` and `annotation_filters` to filter state and URL params
- [ ] 4.2 Extend `useCheckins` hook — pass new params to the API call
- [ ] 4.3 Update `CheckinFilterBar` — add Tags multi-select filter and `AnnotationFilterRows` section
- [ ] 4.4 Update `TradeFilterBar` — add `AnnotationFilterRows` section
- [ ] 4.5 Update `WorkspaceFilterBar` — add `AnnotationFilterRows` section
- [ ] 4.6 Extend `SavedCheckinFilter` schema to persist `annotation_filters` and `taxonomy_ids` in `filter_config`

## Phase 5 — OpenAPI sync & Regenerate client

- [ ] 5.1 Run `openapi-sync` skill to regenerate frontend types after backend changes
