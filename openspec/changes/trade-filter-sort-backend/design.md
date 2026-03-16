## Context

`TradeRepository.list_cursor` currently accepts only `user_id`, `limit`, and `cursor` (a `closed_at`-based timestamp cursor). All 10 filter/sort options in the frontend `TradeFilterBar` are applied in JavaScript after fetching data. With 1,000+ trades, this means loading megabytes of JSON and filtering in-browser.

## Goals / Non-Goals

**Goals:**
- Add `TradeFilterParams` and `TradeSortParams` as typed Pydantic models (not inline query params)
- Extend `list_cursor` in `TradeRepository` to conditionally apply WHERE clauses and ORDER BY based on these models
- Update `TradeService` and the `GET /trades` route handler accordingly
- Update the frontend `useTrades` hook + `TradeFilterBar` to pass filter/sort state to the API

**Non-Goals:**
- Full-text search over trade notes or symbols
- Filter by multiple tag IDs simultaneously (single tag filter only for v1)
- Aggregation counts for filter facets (e.g., "12 trades matching AAPL")
- Changes to pagination mechanism (cursor stays `closed_at`-based)

## Decisions

### Pydantic model vs inline Query params

**Decision**: Use `TradeFilterParams` and `TradeSortParams` as dedicated Pydantic models injected as FastAPI `Depends`.

**Rationale**: Keeps the route handler signature clean, allows the repository to accept a typed object, is testable independently, and matches the pattern used in other projects with complex filter logic. Alternative (flat `Query(...)` parameters inline) creates a 15-parameter function signature.

### Cursor compatibility with sort

**Decision**: When a non-default sort field is active, cursor-based pagination falls back to offset-based pagination (using `skip` parameter instead of `cursor`).

**Rationale**: True cursor pagination requires the cursor to encode the sort key. `closed_at` cursor only works correctly when sorting by `closed_at`. Rather than encoding multi-field cursors (complex), we use offset pagination as a pragmatic fallback for sorted views. Most sorted views are also filtered to short result sets where offset performance is acceptable.

### Index strategy

**Decision**: Add a composite index on `(user_id, symbol)` and `(user_id, asset_class)` via a new Alembic migration.

**Rationale**: The most common filter patterns will be by symbol or asset class scoped to a user. Without these indexes, filtered queries perform a full table scan. Adding them now avoids future performance issues.

## Risks / Trade-offs

- [Offset pagination fallback] Using offset for sorted views means deep pagination is O(n) → Acceptable for now; sorted views are typically used on filtered (small) result sets
- [Cursor invalidation] If a trade's `closed_at` changes, existing cursors may skip or repeat records → Existing risk in current implementation; unchanged by this feature
- [Migration required] Adding indexes means a new Alembic migration → Must be applied to production before deploying; reversible (DROP INDEX)
