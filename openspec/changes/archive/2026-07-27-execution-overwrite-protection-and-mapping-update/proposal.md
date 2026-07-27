## Why

Two related defects allow silent data loss during broker re-imports. First, when a user edits an execution leg that was created as a split child (`origin='split'`), the next raw-pipeline import hard-deletes it in `delete_split_children_for_account` and restores the pristine parent — wiping the edit and any downstream metadata implications. Second, when a user creates a manual replacement execution (`origin='manual'`) for a broken imported fill without linking it to the original broker transaction, subsequent syncs re-insert the raw transaction and duplicate the position.

The root cause is architectural: protection today is trade-level only (`Trade.is_manually_edited`), and the `LogicalExecution.user_modified` flag is written on PATCH but never read by the import pipeline. A parallel spec drift exists — the `raw-transaction-layer` spec demands a `transaction_execution_mappings` junction table that the codebase deliberately abandoned in favour of `LogicalExecution.source_id` + `BrokerRawTransaction.suppressed`.

## What Changes

- Extend `PATCH /api/v1/executions/{id}` so it sets `user_modified=True` for all editable origins (`imported`, `split`, `merged`) — today it only marks `imported`.
- Add an execution-level protection gate in `delete_split_children_for_account` and `restore_split_parents_for_account`: rows with `user_modified=True` are skipped, not deleted or restored.
- Repurpose the existing `overwrite_manually_edited` import flag to also override the new execution-level gate; rename the UI checkbox to "Overwrite user modifications" for clarity.
- Add a new endpoint that links a `manual` execution to a `BrokerRawTransaction`, setting `suppressed=True` on the raw record so future imports skip it.
- Make `delete_execution` symmetric: when a linked manual execution is hard-deleted, atomically flip the linked BRT back to `suppressed=False` so the next import can re-materialise the original imported execution.
- Add a `Trade.has_conflict` column (with Alembic migration) and set it to `True` when the FIFO aggregator detects an unlinked duplicate of a manual execution — a safety net for users who forget to link.
- **BREAKING (spec-only)**: deprecate the "Transaction Execution Mapping" requirement in the `raw-transaction-layer` spec; codify `LogicalExecution.source_id` as the canonical 1:1 link. No code change (the code already behaves this way).

## Capabilities

### New Capabilities
- `execution-overwrite-protection`: Repository- and service-level rules that preserve user-modified `LogicalExecution` rows across broker re-imports, plus the manual-link lifecycle that keeps BRT `suppressed` state in sync with the manual execution that replaces it.

### Modified Capabilities
- `raw-transaction-layer`: Deprecate the junction-table requirement; declare `LogicalExecution.source_id` the canonical raw-to-logical link.

## Impact

- **Backend models**: `Trade` gains a `has_conflict` boolean; `LogicalExecution.user_modified` semantics broadened.
- **Backend services / repos**: `execution.py` (`update_execution`, `delete_execution`), `execution.py` repository (`delete_split_children_for_account`, `restore_split_parents_for_account`), `import_service.py` (FIFO conflict detection).
- **Backend API**: new `POST /api/v1/executions/{id}/link-broker-transaction` endpoint; existing `PATCH /executions/{id}` behaviour extended.
- **Frontend**: import dialog checkbox renamed to "Overwrite user modifications"; manual-execution editor gains a "link broker transaction" affordance; trade views surface a `has_conflict` banner.
- **Database**: one Alembic migration adds `trades.has_conflict`.
- **Specs**: `raw-transaction-layer` gets a deprecation notice; a new `execution-overwrite-protection` spec is introduced.
- **Tests**: new backend unit tests for repo gates and cascade; new Playwright specs `re-import-protection.spec.ts` and `pnl-conflict-banner.spec.ts`.
- **No breaking API changes**: existing endpoints keep their contracts; only additive behaviour.
