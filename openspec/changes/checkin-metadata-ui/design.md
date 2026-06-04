# Design: checkin-metadata-ui

## Architecture decisions

### A. Market Phase stays as `market_phase` string field

The existing `market_phase` field is kept unchanged. A separate Tags field is added to the form that uses the proper `checkin_annotations` relation via assign/remove endpoints. This avoids a breaking migration and keeps the semantic distinction clear: Market Phase = single structural label; Tags = free multi-select metadata.

### B. Generic Annotation Filter utility

The annotation filter query logic from `mcp.py` (`_annotation_value_column_and_value`, `_annotation_operator_expression`) is extracted into `backend/app/repositories/_annotation_filter.py`. Both `daily_checkin_repository.py` and `trade_repository.py` import from it. This prevents code duplication across three filter paths (checkins, trades, workspace).

### C. AND/OR per filter entry — chained logic

Each `AnnotationFilterItem` carries an optional `logic: "AND" | "OR"` field. The backend processes the list in order:
- Entry 1: always applied (starts the WHERE clause)
- Entry N: combined with the accumulated condition using its own `logic` operator

This matches familiar query-builder UX (similar to Notion or Airtable filter groups).

### D. Frontend — Annotation Filter UI pattern

Each annotation filter row shows:
1. Annotation definition selector (dropdown)
2. Operator selector (filtered by type of the selected definition)
3. Value input (typed by definition type)
4. AND/OR toggle (hidden for first row)
5. Remove row button

This pattern is shared between `CheckinFilterBar`, `TradeFilterBar`, and `WorkspaceFilterBar` as a new `AnnotationFilterRows` component in `frontend/components/ui/`.

## Data flow — Check-in Form Annotations

```
CheckinForm
  └── renders AnnotationEditor (new component)
        ├── useAnnotationDefinitions(scope="checkins")  ← lists available definitions
        ├── existing entry.annotation_assignments       ← current values
        └── on change: calls assign/update/remove annotation endpoint
              (separate from the main form save, immediate effect)
```

Tags follow the same immediate-effect pattern using the taxonomy assign/remove endpoints.

For **new** check-ins (not yet saved), tag and annotation changes are buffered in local state and applied after the initial create call.

## Backend changes

| File | Change |
|---|---|
| `repositories/_annotation_filter.py` | New — shared annotation filter helpers |
| `repositories/daily_checkin_repository.py` | Add `taxonomy_ids` and `annotation_filters` params to `list_by_user` |
| `repositories/trade_repository.py` | Add `annotation_filters` param to `list_trades` |
| `services/daily_checkin_service.py` | Pass new filter params through |
| `services/trade_service.py` | Pass annotation_filters through |
| `api/v1/checkins.py` | Add `taxonomy_ids` and `annotation_filters` query params |
| `api/v1/trades.py` | Add `annotation_filters` query params |
| `schemas/checkin_filter.py` | Add `AnnotationFilterItem` schema |

## Frontend changes

| File | Change |
|---|---|
| `components/ui/AnnotationFilterRows.tsx` | New — shared annotation filter UI rows |
| `components/checkin/CheckinFilterBar.tsx` | Add taxonomy_ids multi-select + AnnotationFilterRows |
| `components/checkin/CheckinFilterContext.tsx` | Add taxonomy_ids and annotation_filters to filter state |
| `hooks/useCheckinParams.ts` | Add taxonomy_ids and annotation_filters URL params |
| `hooks/useCheckins.ts` | Pass new filter params to API |
| `components/checkin/CheckinForm.tsx` | Add Tags section + Annotations section |
| `components/checkin/AnnotationEditor.tsx` | New — renders typed annotation inputs |
| `components/trades/TradeFilterBar.tsx` | Add AnnotationFilterRows section |
| `components/workspace/WorkspaceFilterBar.tsx` | Add AnnotationFilterRows section |
