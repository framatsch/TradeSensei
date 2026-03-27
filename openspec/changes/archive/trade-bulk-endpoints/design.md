## Context

The frontend `BulkActionToolbar` component and associated hooks (`useBulkDeleteTrades`, `useBulkAssignTags`, `useBulkAssignPlaybook`) were built in `ui-gap-fixes` expecting three backend endpoints. The backend router in `trades.py` has no `/bulk/*` routes. This means bulk operations silently fail or throw network errors for users.

## Goals / Non-Goals

**Goals:**
- Implement `POST /trades/bulk/delete`, `POST /trades/bulk/assign-tags`, `POST /trades/bulk/assign-playbook`
- Enforce per-user ownership: only the authenticated user's trades are modified; foreign-user trade IDs are silently skipped (not an error, for idempotency)
- Return a summary response indicating how many trades were affected
- Handle empty `trade_ids` list gracefully (200, 0 affected)

**Non-Goals:**
- No pagination of bulk results
- No undo/rollback mechanism
- No bulk update of other trade fields (e.g., `symbol`, `pnl`) — that's a separate change
- No changes to frontend code

## Decisions

### POST vs PATCH/DELETE with body

**Decision**: Use `POST /trades/bulk/*` (separate action endpoints).

**Rationale**: REST `DELETE` with a request body is technically valid but not well-supported by all HTTP clients and frameworks. `PATCH /trades/bulk` with an action discriminator field is another option but mixes concerns. Three focused `POST` action endpoints are explicit, match the existing frontend hooks, and follow the pattern used in many production APIs (Stripe, GitHub, Notion). Consistent with what `ui-gap-fixes` already expects.

### Ownership enforcement: error vs silent skip

**Decision**: Silently skip trade IDs that don't belong to the authenticated user (no error, just not counted as affected).

**Rationale**: Bulk operations should be idempotent — re-sending the same request should produce the same result. Raising 403 or 404 for any single unknown ID would make retries fragile. The `affected_count` in the response lets the caller verify results without breaking on partial mismatches.

### Transaction scope

**Decision**: All IDs in a single bulk request are processed in one DB transaction.

**Rationale**: Partial failure (e.g., 5 of 10 deletes succeed, then DB error) leaves data in an inconsistent state. A single transaction ensures all-or-nothing semantics.

## Risks / Trade-offs

- [Large batch size] Sending 10,000 IDs in one request could cause slow queries or timeouts → Add a `MAX_BULK_SIZE = 500` constant; return 422 if exceeded
- [Race condition] Another request deletes a trade while bulk is processing → Acceptable; ownership filter makes it idempotent
- [Tag assignment semantics] Assign-tags replaces all existing tags (not append) → Documented in spec; this matches what the frontend BulkActionToolbar implements
