## Why

Four pending changes (`execution-soft-delete-tombstone-protection`, `execution-status-and-pnl-calculation`, `fresh-start-import-mode`, `orphaned-journaling-management`) collectively introduce 711 tasks, a complex 6-state status machine, a separate tombstone table, a `previous_status` column, and a two-stage trade deletion flow.

The root problem they all try to solve is one sentence: **re-import must not resurrect executions the user has deleted.** Everything else is overengineering.

This change replaces all four with a minimal schema and behaviour set that solves the real problem.

## What Changes

- **REPLACES** `execution-soft-delete-tombstone-protection`, `execution-status-and-pnl-calculation`, `fresh-start-import-mode`, `orphaned-journaling-management` — those four changes are archived.
- **Schema — one additive migration** (no table drops, no destructive renames):
  - `logical_executions.status` enum column → `origin` TEXT with CHECK (`imported | manual | merged | split`) — immutable, set once at creation.
  - Add `logical_executions.deleted` BOOLEAN DEFAULT false — user soft-delete intent.
  - Add `logical_executions.user_modified` BOOLEAN DEFAULT false — user changed price/qty/commission from broker original.
  - Add `logical_executions.parent_id` INT nullable FK → `logical_executions(id)` — lineage for split/merge.
  - Add `broker_raw_transactions.suppressed` BOOLEAN DEFAULT false — permanent per-transaction suppression.
- **No new tables** — no `deleted_execution_tombstones`, no `TransactionExecutionMapping`.
- **Behaviour**:
  - Soft-delete with origin-aware hard-delete for manual executions.
  - Restore endpoint for soft-deleted executions.
  - `user_modified` flag set automatically when patching an imported execution.
  - FIFO aggregator filters to `deleted=false`.
  - Fresh-start mode deletes all trades + executions for an account (BRTs untouched) in one transaction before processing a new import file.
  - Suppressed BRT flag skips that transaction unconditionally on all future imports.

## Capabilities

### New Capabilities
- `execution-soft-delete` — soft-delete imported/merged/split executions; hard-delete manual ones.
- `import-deduplication` — BRT-anchored deduplication that respects deleted and suppressed flags.
- `fresh-start` — account-scoped wipe of trades + executions before a clean re-import.

### Modified Capabilities
- `execution-edit-tracking` — `user_modified` boolean replaces the EDITED status value.
- `execution-split-merge` — `parent_id` FK replaces the n:m junction table for lineage.

## Impact

- **Database**: `logical_executions` (rename column, add 4 columns); `broker_raw_transactions` (add 1 column); one Alembic migration.
- **Backend models**: `LogicalExecution`, `BrokerRawTransaction` SQLAlchemy + Pydantic schemas.
- **Services**: `ExecutionService`, `TradeService`, `ImportService`.
- **API endpoints**: `/executions` (DELETE, PATCH, GET), `/executions/{id}/restore` (POST), `/trades` (DELETE), `/imports/{account_id}/fresh-start` (POST), `/broker-raw-transactions/{id}/suppress` (PATCH).
- **Frontend**: `ExecutionResponse` interface, `ExecutionStatusBadge` component, `ExecutionLegsTable` (filter toggle, Restore button), Import dialog (Fresh Start option), OpenAPI client regeneration.
- **Tests**: unit (services), integration (repositories/endpoints), E2E (Playwright critical paths).
