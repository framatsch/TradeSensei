## 1. Database Migration

- [ ] 1.1 Create Alembic migration: rename `logical_executions.status` column to `origin`.
- [ ] 1.2 Change `origin` type from enum to `TEXT` with CHECK constraint (`imported`, `manual`, `merged`, `split`).
- [ ] 1.3 Add `logical_executions.deleted` BOOLEAN NOT NULL DEFAULT false.
- [ ] 1.4 Add `logical_executions.user_modified` BOOLEAN NOT NULL DEFAULT false.
- [ ] 1.5 Add `logical_executions.parent_id` INT nullable FK → `logical_executions(id)` ON DELETE SET NULL.
- [ ] 1.6 Add `broker_raw_transactions.suppressed` BOOLEAN NOT NULL DEFAULT false.
- [ ] 1.7 Add index on `logical_executions(trade_id, deleted)` for aggregator query.
- [ ] 1.8 Add index on `logical_executions(parent_id)` for lineage queries.
- [ ] 1.9 Add index on `broker_raw_transactions(suppressed)` for import filter.
- [ ] 1.10 Verify migration is backward-compatible (existing rows: `origin` retains previous status values; `deleted=false`; `user_modified=false`; `parent_id=NULL`; `suppressed=false`).

## 2. Backend Models & Schemas

- [ ] 2.1 Update `LogicalExecution` SQLAlchemy model: rename `status` → `origin`, add `deleted`, `user_modified`, `parent_id` columns.
- [ ] 2.2 Update `BrokerRawTransaction` SQLAlchemy model: add `suppressed` column.
- [ ] 2.3 Update `ExecutionResponse` Pydantic schema: expose `origin`, `deleted`, `user_modified`, `parent_id`.
- [ ] 2.4 Update `ExecutionCreate` / `ExecutionUpdate` Pydantic schemas: `origin` required on create, not patchable; `deleted` / `user_modified` not directly settable by API consumer.
- [ ] 2.5 Update `BrokerRawTransactionResponse` schema: expose `suppressed`.
- [ ] 2.6 Remove all references to `EDITED`, `IGNORED` status enum values from models and schemas.
- [ ] 2.7 Verify `mypy --strict` passes with no new type errors.

## 3. Import Service

- [ ] 3.1 Update import deduplication logic: before creating execution, check `BRT.suppressed` — if true, skip record entirely.
- [ ] 3.2 Update import deduplication logic: if BRT exists and linked execution has `deleted=true`, skip record (do not recreate execution).
- [ ] 3.3 Update import summary schema to report suppressed and skipped-deleted counts.
- [ ] 3.4 Remove any `TransactionExecutionMapping` creation logic from import service.
- [ ] 3.5 Add `PATCH /broker-raw-transactions/{id}/suppress` endpoint (toggle `suppressed` flag).
- [ ] 3.6 Ensure import service sets `origin='imported'` on all created executions.

## 4. Execution Service

- [ ] 4.1 Implement soft-delete: `DELETE /executions/{id}` — if `origin` is `imported|merged|split`, set `deleted=true` and re-aggregate parent trade; if `origin` is `manual`, hard-delete the row.
- [ ] 4.2 Return 200 with execution body on soft-delete; return 204 on hard-delete.
- [ ] 4.3 Return 409 Conflict when `DELETE` is called on an already-deleted execution.
- [ ] 4.4 Implement restore: `POST /executions/{id}/restore` — set `deleted=false`, re-aggregate parent trade.
- [ ] 4.5 Return 400 Bad Request when restore is called on a non-deleted execution.
- [ ] 4.6 Update `PATCH /executions/{id}`: automatically set `user_modified=true` when patching an execution with `origin='imported'`.
- [ ] 4.7 Update split logic: mark original `deleted=true`, create two children with `origin='split'` and `parent_id=original.id`.
- [ ] 4.8 Update merge logic: mark all sources `deleted=true`, create merged execution with `origin='merged'` and `parent_id=primary.id`.
- [ ] 4.9 Ensure re-aggregation is triggered after every delete, restore, split, and merge.

## 5. Trade Service

- [ ] 5.1 Update trade delete: for each child execution, soft-delete (`deleted=true`) if `origin` is `imported|merged|split`; hard-delete if `origin='manual'`.
- [ ] 5.2 Hard-delete the `Trade` row after processing child executions.
- [ ] 5.3 Implement `POST /imports/{account_id}/fresh-start`: in a single DB transaction, delete all `LogicalExecution` rows for account, then all `Trade` rows, then process import file; roll back entirely on any error.
- [ ] 5.4 Add `statement_timeout` guard to fresh-start endpoint (configurable, default 60 s).
- [ ] 5.5 Remove two-stage trade deletion logic, `is_empty`, and `has_conflict` fields if present.

## 6. FIFO Aggregator

- [ ] 6.1 Update aggregator execution query: add `AND deleted=false` filter.
- [ ] 6.2 Verify no other aggregator logic changes are required (all P&L, FIFO, price derivation logic unchanged).
- [ ] 6.3 Run existing aggregator regression test suite — all tests must pass without modification.

## 7. API Endpoints

- [ ] 7.1 `DELETE /executions/{id}` — simplified per Decision 4 (soft vs hard by origin).
- [ ] 7.2 `POST /executions/{id}/restore` — new endpoint.
- [ ] 7.3 `DELETE /trades/{id}` — simplified per task 5.1–5.2.
- [ ] 7.4 `GET /executions` — add optional `include_deleted` boolean query param (default false).
- [ ] 7.5 `POST /imports/{account_id}/fresh-start` — new endpoint.
- [ ] 7.6 `PATCH /broker-raw-transactions/{id}/suppress` — new endpoint.
- [ ] 7.7 Update OpenAPI annotations for all changed/new endpoints (response_model, status_code, summary, tags, error responses, field descriptions + examples per `openapi-docs` agent rules).

## 8. Frontend

- [ ] 8.1 Add `ExecutionOrigin` type: `'imported' | 'manual' | 'merged' | 'split'`.
- [ ] 8.2 Update `ExecutionResponse` interface: add `origin`, `deleted`, `user_modified`, `parent_id`.
- [ ] 8.3 Implement `ExecutionStatusBadge` component: derive badge from `origin` + `deleted` + `user_modified` per badge table in spec (`imported`→blue, `edited`→amber, `manual`→violet, `merged`→orange, `split`→cyan, `deleted`→gray 50% opacity). No dark: modifier — semantic tokens only.
- [ ] 8.4 Update `ExecutionLegsTable`: hide deleted executions by default; add "Show deleted" toggle; show deleted rows at 50% opacity with `[Restore]` button.
- [ ] 8.5 Wire Restore action: call `POST /executions/{id}/restore`, invalidate React Query cache for trade + execution keys.
- [ ] 8.6 Add Fresh Start option to Import dialog: gated behind explicit acknowledgement checkbox; calls `POST /imports/{account_id}/fresh-start`.
- [ ] 8.7 Regenerate OpenAPI TypeScript client after backend changes are complete.
- [ ] 8.8 Verify dual-theme rendering: no hardcoded colors, no `dark:` modifiers in new components.
- [ ] 8.9 Implement `SplitExecutionModal`: dialog to split one execution into two. Fields: qty-A + qty-B (pre-filled 50/50, must sum to original qty), price for each (pre-filled to original), executed_at for each (pre-filled to original). Preview table shows both resulting rows before confirmation. Confirm → calls backend task 4.7 endpoint. Add "Split" option to `ExecutionRow` context menu (only available when execution is not `deleted` and `origin` is `imported` or `manual`).
- [ ] 8.10 Remove `is_empty` / EMPTY-trade UI artifacts introduced by `execution-driven-trade-ui`: delete EMPTY badge from `TradeCard`, remove "Archive" tab from `TradeListTabs`, drop `include_empty`/`only_empty` params from trade list hook and filter UI. These concepts are obsolete — trades with all executions `deleted=true` are simply trades with a zero-quantity aggregation.
- [ ] 8.11 Remove conflict-resolution UI introduced by `execution-driven-trade-ui`: delete `ConflictBanner` component, remove `has_conflict` warning badge from `TradeRow`, remove "Needs Review" system filter from sidebar and delete its seed data row. `has_conflict` is removed from the trade model in task 5.5.

## 9. Tests

- [ ] 9.1 Unit test: soft-delete imported execution → `deleted=true`, trade re-aggregated.
- [ ] 9.2 Unit test: hard-delete manual execution → row removed, 204 returned.
- [ ] 9.3 Unit test: delete already-deleted execution → 409 returned.
- [ ] 9.4 Unit test: restore deleted execution → `deleted=false`, trade re-aggregated.
- [ ] 9.5 Unit test: restore non-deleted execution → 400 returned.
- [ ] 9.6 Unit test: PATCH imported execution → `user_modified=true` set automatically.
- [ ] 9.7 Unit test: PATCH manual execution → `user_modified` stays false.
- [ ] 9.8 Unit test: split execution → original `deleted=true`, children `origin='split'`, `parent_id` set.
- [ ] 9.9 Unit test: merge executions → sources `deleted=true`, merged `origin='merged'`, `parent_id` set.
- [ ] 9.10 Unit test: aggregator excludes `deleted=true` executions from P&L.
- [ ] 9.11 Unit test: restoring execution → trade P&L updates.
- [ ] 9.12 Unit test: import skips BRT with `suppressed=true`.
- [ ] 9.13 Unit test: re-import skips BRT whose linked execution has `deleted=true`.
- [ ] 9.14 Unit test: re-import of unchanged execution is idempotent.
- [ ] 9.15 Unit test: fresh-start deletes trades + executions, keeps BRTs, creates new executions on re-import.
- [ ] 9.16 Unit test: fresh-start rolls back entirely on import error.
- [ ] 9.17 Integration test: full import → delete → re-import cycle against real DB.
- [ ] 9.18 Integration test: fresh-start endpoint against real DB.
- [ ] 9.19 E2E (Playwright): import trades → delete execution → verify excluded from P&L → restore → verify P&L restored.
- [ ] 9.20 E2E (Playwright): open `SplitExecutionModal` on an imported execution, enter quantities, confirm → verify two rows with `split` badge appear in `ExecutionLegsTable` and original row appears as `deleted` when "Show deleted" toggle is active.

## 10. Cleanup & Archival

- [ ] 10.1 Update `AGENTS.md` iteration status to reflect merged scope.
- [ ] 10.2 Run `ruff check`, `mypy --strict`, `pytest` — all must pass.
- [ ] 10.3 Request code review via `.opencode/agents/code-reviewer.md` workflow.
- [ ] 10.4 Add CHANGELOG entries under `[Unreleased]` via `.opencode/agents/changelog-writer.md`.
