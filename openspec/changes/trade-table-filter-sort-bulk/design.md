## Context

The trades table (`TradeTable` + `TradeRow`) is a read-only paginated list with cursor-based pagination. The backend `GET /api/v1/trades` currently supports only one optional filter (`account_id`) and a hard-coded sort order (`opened_at DESC, id DESC`). There are no bulk mutation endpoints.

The cursor is a base64-encoded composite key `"<opened_at ISO>|<uuid>"` — it is currently tightly coupled to the fixed sort order. Adding variable sort requires the cursor to carry the sort field and direction as well, or alternatively a simpler approach: any filter/sort change always resets to page 1 (which the user confirmed is acceptable).

The frontend hook `useTrades` passes only `cursor` and `limit`. The `TradeTable` component has no selection state, no filter state, and no sort state.

## Goals / Non-Goals

**Goals:**
- Extend `GET /api/v1/trades` with full filter + sort query parameters (all optional, backward-compatible)
- Add three new bulk endpoints (`bulk-delete`, `bulk-assign-tags`, `bulk-assign-playbook`) with ownership validation
- Rebuild the frontend trade table with: filter bar (always visible), sortable column headers, row checkboxes, and a bulk action toolbar
- Regenerate the TypeScript OpenAPI client after backend changes

**Non-Goals:**
- Saved/named filter presets (a future capability)
- Column visibility toggles or column reordering
- Export (CSV/PDF) of filtered results
- Real-time / streaming updates to the table
- Pagination state preserved across browser refreshes

## Decisions

### Decision 1: Sort-aware cursor vs. reset-on-sort

**Chosen:** Reset to page 1 whenever filters or sort change.

**Rationale:** Making the cursor sort-aware requires encoding the sort field, direction, and the sort-field's value for each row — increasing complexity significantly (especially for nullable fields like `pnl` or `closed_at`). Since the user confirmed "reset to page 1" is acceptable, we keep the cursor simple: it always encodes `(opened_at, id)` or `(sort_value, id)` for the current sort only, but any sort/filter change resets `cursor = null`.

**Alternative rejected:** Fully sort-aware cursors — overly complex for this iteration.

### Decision 2: Sort field in cursor encoding

**Chosen:** When `sort_by != opened_at`, the cursor encodes `(sort_field_value, id)` using the same base64 scheme, but the sort value is serialized as a string. The repository `list_cursor` reconstructs the WHERE clause from the sort params passed alongside the cursor.

**Why not a pure offset:** Offset pagination breaks when rows are inserted/deleted mid-browse. Keyset is correct here.

### Decision 3: Tag filter AND/OR mode

**Chosen:** `tag_filter_mode: "and" | "or"` query param (default `"and"`). Backend implements:
- `AND`: Use `HAVING COUNT(DISTINCT tag_id) = N` after joining on all requested tag UUIDs
- `OR`: Simple `WHERE tag_id = ANY(:ids)` join on `trade_tags`

### Decision 4: Bulk endpoints as separate POST routes (not DELETE with body)

**Chosen:** `POST /api/v1/trades/bulk-delete`, `POST /api/v1/trades/bulk-assign-tags`, `POST /api/v1/trades/bulk-assign-playbook`.

**Rationale:** `DELETE` with a request body is technically allowed but violates common HTTP client expectations and is not supported by some proxies. Dedicated `POST` endpoints with `bulk-` prefix are explicit, self-documenting, and easy to mock in tests.

**Route order:** These three `POST /trades/bulk-*` routes must be registered **before** the `POST /trades` (create) route in FastAPI to avoid path conflicts — or use distinct path prefixes. We'll use `/api/v1/trades/bulk/delete`, `/api/v1/trades/bulk/assign-tags`, `/api/v1/trades/bulk/assign-playbook` to avoid any ambiguity.

### Decision 5: Bulk tag assignment is additive (not replacement)

**Chosen:** `mode: "add" | "remove"` in the request body. `"add"` inserts rows in `trade_tags` for each `(trade_id, tag_id)` pair that doesn't already exist (ON CONFLICT DO NOTHING). `"remove"` deletes those rows.

**Rationale:** User confirmed "additiv hinzufügen". Additive is the safe default — it avoids accidentally wiping tags from trades that had different existing tags.

### Decision 6: Frontend filter state management

**Chosen:** Filter state lives in a `useTradeFilters` custom hook with `useState` + `useCallback`, passed down via props to `TradeFilterBar` and `TradeTable`. No global store (Zustand) needed — the filter is page-scoped.

**Rationale:** Keeps state local to the trades page, no unnecessary global state. URL query params (for shareable filtered URLs) is a future enhancement.

### Decision 7: `TradeTable` checkbox state

**Chosen:** `selectedIds: Set<string>` managed in the trades page component (parent of both `TradeSelectionToolbar` and `TradeTable`). "Select all" selects all trade IDs in the **current page** only (not across all pages).

**Rationale:** Cross-page selection requires fetching all matching IDs, which adds significant complexity. Selecting within the current page is intuitive and safe.

## Risks / Trade-offs

- **Sort cursor complexity**: Sorting by nullable fields (`closed_at`, `pnl`, `exit_price`) requires NULL-aware cursor comparisons. Mitigation: Use `NULLS LAST` ordering and encode NULL as an empty string in the cursor; handle in repository.
- **Bulk ownership check N+1**: Fetching each trade to verify `user_id` before bulk delete would be N queries. Mitigation: Use a single `SELECT id FROM trades WHERE id = ANY(:ids) AND user_id = :user_id` to get the valid subset, operate only on those.
- **Tag AND filter correctness**: Using HAVING on a JOIN can be tricky with the cursor WHERE clause. Mitigation: Subquery approach — `WHERE id IN (SELECT trade_id FROM trade_tags WHERE tag_id = ANY(:ids) GROUP BY trade_id HAVING COUNT(DISTINCT tag_id) = :n)`.
- **React re-renders on filter input**: Symbol text input with immediate state update causes re-renders on every keystroke. Mitigation: 300ms debounce before updating the query key.

## Migration Plan

1. Deploy backend changes (new query params are optional, defaults preserve current behavior — zero breaking changes)
2. Regenerate TypeScript OpenAPI client from updated spec
3. Deploy frontend changes
4. No database schema changes required; no migration needed

## Open Questions

- None — all decisions confirmed by user.
