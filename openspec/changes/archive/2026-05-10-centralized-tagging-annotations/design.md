## Context

The Trade Sensei platform's existing trade and check-in models carry hardcoded metadata fields (e.g., tags as a simple string array, fixed psychological fields). This prevents users from defining their own taxonomies and quantitative annotations, and makes cross-entity reporting impossible. The goal is to introduce a generalized, reusable metadata system built on two distinct primitives — discrete tags (taxonomies) and typed key-value annotations — that both trades and check-ins can consume.

The system is built greenfield: no migration of existing trade or checkin data is needed. The new tables coexist alongside existing ones without altering current schemas beyond adding optional response fields.

## Goals / Non-Goals

**Goals:**
- Define a clean 2×2 matrix: {Trades, Check-ins} × {Taxonomies, Annotations}
- Store annotation values in typed columns (`value_int`, `value_float`, `value_bool`, `value_string`) to enable efficient SQL aggregation and correlation queries
- Enforce scoping: a `trades`-only definition cannot be assigned to a check-in and vice versa
- Smart-delete: soft-delete (archive) definitions with existing assignments, hard-delete otherwise
- Block dangerous mutations: type changes and scope narrowing are rejected when assignments exist
- API-first: all functionality is exposed via REST endpoints; frontend consumes generated client
- Provide unit test coverage for all validation, constraint, and mapping behaviors

**Non-Goals:**
- UI redesign of trade/check-in detail pages (deferred to a separate frontend spec)
- Migration of existing trade tags or checkin psychological fields into the new schema
- Reporting/correlation endpoints (the typed-column schema is the enabler; query endpoints come later)
- Real-time subscription or webhook events on metadata changes

## Decisions

### D1: Typed Columns over JSONB for Annotation Values

**Decision**: Use four nullable typed columns (`value_int`, `value_float`, `value_bool`, `value_string`) with a CHECK constraint enforcing exactly one is non-null.

**Rationale**: JSONB requires casting at query time, preventing index use for range filters and aggregate functions. Typed columns allow direct `AVG(value_float)`, `COUNT WHERE value_bool = true`, and indexed range queries — essential for future correlation reports. A CHECK constraint (`num_nonnulls(...) = 1`) enforces single-type integrity at the DB level, not just application level.

**Alternative considered**: Single `value JSONB` column — rejected due to poor aggregate performance and inability to enforce type constraints at the DB layer.

### D2: Soft vs. Hard Delete for Definitions

**Decision**: DELETE on a taxonomy or annotation_definition checks for existing assignments:
- 0 assignments → hard delete (physical row removal)
- ≥1 assignments → soft delete (`is_archived = true`)

**Rationale**: Preserves data integrity (referenced definitions must not disappear) while keeping the DB clean when definitions are unused. Archived definitions are hidden from list endpoints but still returned in trade/checkin detail responses so historical assignments remain readable.

**Alternative considered**: Always soft-delete — rejected because it leaves orphaned rows when no assignments reference the definition, cluttering the namespace.

### D3: Scope Stored on Definition, Validated at Assignment

**Decision**: `scope` is an enum (`trades`, `checkins`, `both`) on the definition table. The assignment service validates scope compatibility before inserting.

**Rationale**: Storing scope on the definition keeps the assignment tables simple (no scope column needed there). The service layer enforces the rule rather than a DB trigger, keeping logic testable and explicit.

### D4: Scope and Type Mutation Guards in the Service Layer

**Decision**: PUT/PATCH on definitions rejects:
- Any `type` change for `annotation_definitions` (always, unconditionally)
- Any `scope` narrowing (e.g., `both` → `trades`) when assignments exist in the table being excluded

**Rationale**: Changing the type of an annotation would silently corrupt existing typed-column values. Narrowing the scope would leave orphaned assignments in the excluded table. Both are detected server-side and return 422 with a descriptive error.

### D5: Layered Architecture — Repository / Service / Router

**Decision**: Follow the existing Trade Sensei layered pattern: SQLAlchemy async repositories → service classes → FastAPI routers. No business logic in routers; no DB queries in services.

**Rationale**: Consistency with the existing codebase. Services can be unit-tested by mocking repositories without a real DB.

### D6: Frontend — API Client Only, No UI Changes

**Decision**: Frontend work is limited to regenerating the OpenAPI TypeScript client and wiring existing data-fetching hooks. No component or layout changes.

**Rationale**: Scoped per the user's requirements: visual layout of the 2×2 matrix on trade/checkin detail pages is a separate design effort.

## Risks / Trade-offs

- **CHECK constraint races**: Concurrent inserts into annotation assignment tables could theoretically violate the CHECK if application code misroutes the value. Mitigation: the service's `map_value_to_column` function is the single code path for all assignments; it is unit-tested exhaustively.
- **Archived definition leak**: A definition archived while in-flight requests are pending could create assignments against an archived definition. Mitigation: the assignment service loads the definition (including `is_archived`) and rejects assignments to archived definitions with a 422.
- **Scope guard circumvention**: A concurrent assignment insert could slip in between the scope-check query and the mutation guard check. Mitigation: the mutation guard performs a fresh count inside the same transaction; the assignment service also validates scope before insert. Acceptable risk for this scale.
- **Trade-off — no JSONB flexibility**: Typed columns require knowing the annotation type at definition creation time. Users cannot "recast" a field without deleting and recreating it. This is intentional and enforced.

## Migration Plan

1. Generate Alembic migration for all 6 new tables with constraints
2. Deploy backend with new routers (additive — no existing endpoints change)
3. Run `openapi-sync` to regenerate frontend TypeScript client
4. Wire frontend data-fetching hooks to new endpoints
5. No rollback complexity: all new tables; dropping them reverts the change cleanly

## Open Questions

- Should `scale_labels` for non-`string_enum` types support optional `min`/`max` bounds (e.g., for int/float range enforcement)? **Current decision**: yes — the service reads `scale_labels.min` and `scale_labels.max` if present for int/float types and validates the submitted value falls within bounds.
- Should list endpoints support filtering by `scope`? **Current decision**: yes, optional `?scope=` query param on taxonomy and annotation-definition list endpoints.
