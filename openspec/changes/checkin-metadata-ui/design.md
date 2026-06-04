# Design: checkin-metadata-ui

## Architecture decisions

### A. market_phase → "Market Regime" string_enum Annotation

The `market_phase` column on `daily_checkins` is kept in the DB to avoid a destructive migration and to preserve existing data. The UI and filter simply stop using it. A new `AnnotationDefinition("Market Regime", type="string_enum")` is added to `seed_defaults` and rendered by the generic AnnotationEditor — no special-casing needed. The field is now effectively soft-deprecated.

### B. Generic Annotation Filter utility

The annotation filter query helpers (`_annotation_value_column_and_value`, `_annotation_operator_expression`) are extracted from `mcp.py` into `backend/app/repositories/_annotation_filter.py`. All three filter paths (checkins, trades, workspace) import from it. AND/OR chaining is controlled by a `logic` field on each `AnnotationFilterItem`.

### C. AND/OR per filter entry — chained logic

Each `AnnotationFilterItem` carries `logic: Literal["AND", "OR"] = "AND"`. The backend processes the list in order: entry 1 is always applied unconditionally; entry N is combined with the accumulated predicate using its own `logic` value. This mirrors familiar query-builder UX (Notion, Airtable).

### D. Shared AnnotationFilterRows frontend component

A single `frontend/components/ui/AnnotationFilterRows.tsx` is used by `CheckinFilterBar`, `TradeFilterBar`, and `WorkspaceFilterBar`. Props:
- `definitions: AnnotationDefinitionResponse[]`
- `value: AnnotationFilterItem[]`
- `onChange: (items: AnnotationFilterItem[]) => void`

Each row renders: definition dropdown → type-scoped operator dropdown → typed value input → AND/OR toggle (hidden on row 0) → remove button.

### E. MCP tool design — list_checkins

Returns paginated check-ins with full annotation and taxonomy assignments. Supports `date_from`, `date_to`, `taxonomy_ids`, `annotation_filters` — mirrors the UI filter capability exactly. This allows AI agents to: (1) call `get_metadata_schema` to discover available definitions/tags, (2) build a filter, (3) call `list_checkins` with that filter.

### F. New check-in annotation buffering

For new check-ins (not yet saved), tag and annotation changes are buffered in local state. After the initial `POST /checkins`, the form applies buffered changes via the assign/update endpoints in sequence. This avoids a schema change to `DailyCheckinCreate`.

## Backend changes

| File | Change |
|---|---|
| `repositories/_annotation_filter.py` | New — shared annotation filter helpers extracted from mcp.py |
| `repositories/annotation_definition_repository.py` | Add "Market Regime" to `seed_defaults` |
| `repositories/daily_checkin_repository.py` | Add `taxonomy_ids` and `annotation_filters` to `list_by_user`; remove `market_phase`/`regime` param |
| `repositories/trade_repository.py` | Add `annotation_filters` param |
| `services/daily_checkin_service.py` | Pass new filter params; remove regime param |
| `services/trade_service.py` | Pass annotation_filters |
| `api/v1/checkins.py` | Add `taxonomy_ids` + `annotation_filters`; remove `regime` query param |
| `api/v1/trades.py` | Add `annotation_filters` query param |
| `api/mcp.py` | Add `list_checkins` tool; add `sync_checkin_metadata` tool; extend `search_trades_advanced` with `annotation_filters` |
| `schemas/annotation_filter.py` | New — `AnnotationFilterItem` schema |

## Frontend changes

| File | Change |
|---|---|
| `components/ui/AnnotationFilterRows.tsx` | New — shared annotation filter rows component |
| `components/checkin/AnnotationEditor.tsx` | New — typed annotation input per definition |
| `components/checkin/CheckinForm.tsx` | Remove Market Phase section; add Tags + Annotations sections |
| `components/checkin/CheckinFilterBar.tsx` | Remove `regime` select; add Tags multi-select + AnnotationFilterRows |
| `components/checkin/CheckinFilterContext.tsx` | Remove regime; add `taxonomy_ids` + `annotation_filters` |
| `hooks/useCheckinParams.ts` | Remove regime; add `taxonomy_ids` + `annotation_filters` URL params |
| `hooks/useCheckins.ts` | Pass new filter params to API |
| `components/trades/TradeFilterBar.tsx` | Add AnnotationFilterRows section |
| `components/workspace/WorkspaceFilterBar.tsx` | Add AnnotationFilterRows section |

## Test strategy

| Layer | Coverage |
|---|---|
| Backend unit | `_annotation_filter.py` helpers: operator expressions, AND/OR chaining, type dispatch |
| Backend integration | `list_by_user` with taxonomy_ids and annotation_filters; `list_trades` with annotation_filters |
| Backend integration | MCP `list_checkins` and `sync_checkin_metadata` tools |
| Frontend unit | `AnnotationFilterRows`: renders correct operator options per type; onChange fires correctly |
| Frontend unit | `AnnotationEditor`: renders each type correctly; calls endpoints on change |
| Playwright E2E | Assign tag on check-in form; assign annotation; filter by tag; filter by annotation value |
| Playwright E2E | Filter trades by annotation value in TradeFilterBar |
