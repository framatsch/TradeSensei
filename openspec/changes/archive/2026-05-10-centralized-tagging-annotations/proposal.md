## Why

The platform currently lacks a structured, reusable system for attaching user-defined metadata to trades and check-ins. Traders need to tag entries with discrete categories (e.g., strategy type, market condition) and annotate them with typed quantitative or qualitative values (e.g., confidence score, stress level) to enable correlation analysis in reporting. Without this, meaningful pattern analysis across behavioral and performance data is impossible.

## What Changes

- Introduce `taxonomies` as named, scoped, reusable discrete tags assignable to trades and/or check-ins, with an optional `icon_identifier` (VARCHAR) for standardized vector-icon references (e.g. `lucide:trending-down`)
- Introduce `annotation_definitions` as typed metadata definitions (int, float, bool, string_enum) with optional scale/enum labels and an optional `icon_identifier` (VARCHAR), assignable to trades and/or check-ins
- Add four assignment tables implementing a strict 2x2 matrix: `trade_taxonomies`, `checkin_taxonomies`, `trade_annotations`, `checkin_annotations`
- Typed-column pattern on annotation assignment tables (instead of JSONB) to support performant SQL-based correlation queries
- Backend CRUD for taxonomy and annotation definitions with smart delete (soft vs. hard based on existing assignments)
- API endpoints for attaching/updating/removing taxonomies and annotations on trades and check-ins
- Scope validation: definitions scoped to `trades` cannot be assigned to check-ins and vice versa
- Scope and type mutation guards: narrowing a scope or changing an annotation type is blocked if assignments exist
- Frontend API client integration for all new endpoints (no UI layout changes)
- Unit tests covering all validation, constraint, and mapping behaviors

## Capabilities

### New Capabilities

- `taxonomy-management`: CRUD for taxonomy definitions with archive/scope/color logic and soft/hard delete
- `annotation-definition-management`: CRUD for annotation definitions with typed columns, scale_labels, and soft/hard delete
- `trade-metadata-assignment`: Endpoints to attach/update/remove taxonomies and annotations on trades
- `checkin-metadata-assignment`: Endpoints to attach/update/remove taxonomies and annotations on check-ins
- `metadata-validation`: Cross-cutting validation logic for scope enforcement, type checking, enum validation, and typed-column mapping

### Modified Capabilities

- `trade-import`: Trade responses should optionally include assigned taxonomies and annotations in GET detail endpoints

## Impact

- **Database**: 6 new tables (`taxonomies`, `annotation_definitions`, `trade_taxonomies`, `checkin_taxonomies`, `trade_annotations`, `checkin_annotations`)
- **Backend**: New models, repositories, services, schemas, and API routers under `app/`
- **Frontend**: New generated API client methods; no visual layout changes
- **Existing trades/checkins routes**: Extended to include metadata in response schemas (opt-in)
- **No data migration**: Greenfield — no existing trade/checkin data needs to be migrated
