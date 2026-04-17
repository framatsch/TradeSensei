## Context

`isolated-raw-layer-architecture` established `BrokerRawTransaction.composite_id` as the deduplication anchor — BRT rows are an immutable, append-only log of what the broker reported.

Four pending changes wanted to extend the execution status to 6 states and add a tombstone table, conflating two orthogonal concerns:
- **Provenance** — where did this execution come from?
- **Mutation intent** — has the user acted on it (edited, deleted)?

Mixing these into a single status column produces a combinatorial explosion. This design separates them.

## Goals

1. Soft-delete without losing the BRT link, so re-import cannot resurrect deleted executions.
2. Track user edits separately from origin so import logic stays simple.
3. Support split/merge lineage without an n:m junction table.
4. Enable fresh-start per account without touching BRTs.
5. Keep the FIFO aggregator unchanged except for a single filter predicate.

---

## Decision 1: Two Fields Instead of Six States

**Problem**: A 6-value status enum (`IMPORTED`, `EDITED`, `DELETED`, `MERGED`, `SPLIT`, `IGNORED`) conflates three independent facts about an execution.

**Decision**: Split into three orthogonal fields:

| Field | Type | Meaning | Mutable? |
|---|---|---|---|
| `origin` | TEXT CHECK | Where did this execution come from? | No — set once at creation |
| `user_modified` | BOOLEAN | Has the user changed price/qty/commission? | Yes |
| `deleted` | BOOLEAN | Has the user soft-deleted this execution? | Yes (restore possible) |

**Trade-off**: Lose single-column `WHERE status='EDITED'`; gain composable, readable queries and no state-machine transitions to maintain.

---

## Decision 2: BRT as Re-Import Anchor (No Tombstone Table)

**Problem**: A tombstone table is required when the original record is hard-deleted. If we keep the execution row (with `deleted=true`), the BRT link is preserved and the import check is trivial.

**Decision**: BRT rows are never deleted. Import logic:

```
if BRT.suppressed      → skip unconditionally
elif exec.deleted      → skip (user intent preserved)
elif exec exists       → skip (idempotent)
else                   → create BRT + execution
```

**Fresh-start variant**: Delete all `LogicalExecution` + `Trade` rows for the account (within one transaction) *before* processing the file. BRTs are left untouched. On re-import, executions are created fresh from the existing BRTs.

**BRT suppression**: A `suppressed=true` flag on the BRT row permanently silences a transaction across all future imports. Used for erroneous or unwanted broker entries.

**Trade-off**: BRT table grows over time; future purge feature can address this. Tombstone table eliminated.

---

## Decision 3: `parent_id` FK for Split/Merge Lineage

**Problem**: An n:m junction table for split/merge requires joining three tables to reconstruct lineage and adds a migration surface.

**Decision**: Single nullable `parent_id INT REFERENCES logical_executions(id)`.

- **Split**: mark original `deleted=true`; create 2 children with `origin='split'`, `parent_id=original.id`.
- **Merge**: mark all sources `deleted=true`; create merged execution with `origin='merged'`, `parent_id=primary_source.id`.

**Trade-off**: For N>2 merges, only the primary source is stored as parent. Full source set is recoverable by querying deleted executions with matching `trade_id` + `deleted_at` timestamp proximity — acceptable for MVP.

---

## Decision 4: Soft-Delete Behaviour by Origin

| origin | Delete action | Restore possible? | Reason |
|---|---|---|---|
| `imported` | `deleted=true` | Yes | BRT link must be preserved |
| `merged` | `deleted=true` | Yes | Lineage must be preserved |
| `split` | `deleted=true` | Yes | Lineage must be preserved |
| `manual` | Hard delete (row removed) | No | No BRT; restore has no anchor |

**Trade-off**: Manual execution deletion is permanent. Frontend must show a confirmation dialog making this clear.

---

## Decision 5: Aggregator Change is One Filter Predicate

**Decision**: The only change to the FIFO aggregator is adding `AND deleted=false` to the execution query for a given trade. All aggregation logic (FIFO matching, P&L calculation, entry/exit price derivation) is unchanged.

**Trade-off**: None. The aggregator already operates on a filtered set of executions; this just narrows the filter.

---

## Decision 6: Fresh Start via Account-Scoped Delete

**Decision**: `POST /imports/{account_id}/fresh-start` runs in a single DB transaction:
1. Delete all `LogicalExecution` rows for the account.
2. Delete all `Trade` rows for the account.
3. Process the uploaded import file normally.
4. Commit — or roll back entirely on any error.

BRTs are never touched in step 1 or 2.

**Trade-off**: Large accounts with many trades may hit transaction timeouts. A timeout guard (configurable `statement_timeout`) is set for this endpoint. A future streaming implementation can replace this if needed.

**UI requirement**: Fresh-start is a destructive action — the import dialog must require explicit acknowledgement ("I understand this will delete all trades and executions for this account") before the endpoint is called.

---

## Decision 7: `user_modified` Replaces EDITED Status

**Decision**: When `PATCH /executions/{id}` is called on an execution with `origin='imported'`, the service sets `user_modified=true` automatically. The import service checks `exec.deleted`, not `user_modified` — a user-modified execution is still protected from resurrection.

**Trade-off**: `user_modified` is never reset to `false` (even if the user patches back to the original values). This is intentional: the flag means "a human touched this", which is a fact about history, not about current values.

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Hard-delete of manual executions surprises user | Confirmation dialog in frontend |
| Incomplete merge lineage for N>2 merges | Documented as known limitation; acceptable MVP scope |
| Fresh-start slowness with large datasets | `statement_timeout` guard on endpoint |
| BRT table grows unbounded | Acceptable; future purge feature |
| Suppressed BRT is hard to discover | UI surface in trade detail context menu |
