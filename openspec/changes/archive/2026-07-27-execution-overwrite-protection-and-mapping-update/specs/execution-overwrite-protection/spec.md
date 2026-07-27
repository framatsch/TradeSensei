## ADDED Requirements

### Requirement: user_modified marker on execution edit
The system SHALL set `LogicalExecution.user_modified = True` whenever `PATCH /api/v1/executions/{id}` mutates any patchable field of an execution whose `origin` is `imported`, `split`, or `merged`. `origin='manual'` executions SHALL NOT be marked (they are already user-owned by construction). `origin` SHALL remain immutable.

#### Scenario: Editing an imported leg sets the marker
- **WHEN** a user patches the `price` of a leg with `origin='imported'` and `user_modified=false`
- **THEN** the persisted row SHALL have `user_modified=true`
- **THEN** the response body SHALL include `user_modified: true`

#### Scenario: Editing a split child sets the marker
- **WHEN** a user patches the `quantity` of a leg with `origin='split'` and `user_modified=false`
- **THEN** the persisted row SHALL have `user_modified=true`

#### Scenario: Editing a merged execution sets the marker
- **WHEN** a user patches the `pnl` of a leg with `origin='merged'` and `user_modified=false`
- **THEN** the persisted row SHALL have `user_modified=true`

#### Scenario: Manual executions are not re-marked
- **WHEN** a user patches a leg with `origin='manual'`
- **THEN** `user_modified` SHALL remain `false`
- **THEN** the update SHALL still succeed

#### Scenario: No-op patch does not flip the marker
- **WHEN** a PATCH request contains no mutating fields (empty diff)
- **THEN** `user_modified` SHALL remain at its previous value

---

### Requirement: Split-child cleanup preserves user-modified rows
The repository operation that purges split children before re-aggregation (`delete_split_children_for_account`) SHALL exclude any row with `user_modified = True`. The operation that restores soft-deleted imported parents (`restore_split_parents_for_account`) SHALL NOT restore a parent whose surviving split children include a `user_modified = True` row.

#### Scenario: User-modified split child survives re-import
- **GIVEN** a broker file whose re-import triggers `delete_split_children_for_account`
- **GIVEN** an existing split child `E1a` with `origin='split'` and `user_modified=true`
- **WHEN** the import runs the split-children purge
- **THEN** `E1a` SHALL remain in the database
- **THEN** all other split children with `user_modified=false` SHALL be hard-deleted

#### Scenario: Protected parent is not restored
- **GIVEN** an original imported execution `E1` (soft-deleted, `deleted=true`) with a surviving user-modified child `E1a`
- **WHEN** the import runs `restore_split_parents_for_account`
- **THEN** `E1` SHALL remain `deleted=true`
- **THEN** `E1a` SHALL keep its `trade_id`

#### Scenario: Unprotected parent is restored normally
- **GIVEN** an original imported execution `E2` (soft-deleted) whose split children have all been purged (none `user_modified`)
- **WHEN** the import runs `restore_split_parents_for_account`
- **THEN** `E2` SHALL be updated to `deleted=false, trade_id=NULL`

---

### Requirement: Trade rebuild preserves user-modified executions
The raw-pipeline trade rebuild SHALL NOT delete trades whose only remaining execution legs are all `user_modified=True`, and SHALL NOT reassign a `user_modified=True` leg to a different trade during re-aggregation. This protection is independent of `Trade.is_manually_edited`.

#### Scenario: Trade backed by a user-modified leg survives the rebuild
- **GIVEN** trade `T` whose only leg `E1a` has `user_modified=true` and `is_manually_edited=false` on `T`
- **WHEN** the raw-pipeline import calls `delete_by_user_account` before re-aggregation
- **THEN** `T` SHALL NOT be deleted
- **THEN** `E1a` SHALL keep `trade_id=T`
- **THEN** trade-level metadata (playbook, tags, notes) SHALL remain unchanged

#### Scenario: Aggregated fields recompute from protected legs
- **WHEN** re-aggregation runs over a trade whose legs mix `user_modified=true` and `user_modified=false` rows
- **THEN** the trade's cached fields (`pnl`, `entry_price`, `quantity`, etc.) SHALL reflect the current leg values
- **THEN** no `user_modified=true` leg SHALL be mutated during re-aggregation

---

### Requirement: Overwrite user modifications override
When the caller sets `overwrite_manually_edited=True` on an import request (form field on `POST /api/v1/imports/upload`, body field on `POST /api/v1/imports/flex`), the protection gates defined by "Split-child cleanup preserves user-modified rows" and "Trade rebuild preserves user-modified executions" SHALL be bypassed for that import: user-modified split children SHALL be hard-deleted and their parents restored, and user-modified trade legs SHALL be subject to normal rebuild. The frontend import dialog SHALL label the corresponding checkbox "Overwrite user modifications".

#### Scenario: Override wipes user-modified split children
- **GIVEN** a user-modified split child `E1a`
- **WHEN** an import runs with `overwrite_manually_edited=true`
- **THEN** `E1a` SHALL be hard-deleted
- **THEN** its parent `E1` SHALL be restored (`deleted=false`)
- **THEN** re-aggregation SHALL produce the pristine broker projection

#### Scenario: Default import protects user modifications
- **WHEN** an import runs with `overwrite_manually_edited=false` (default)
- **THEN** the protection gates SHALL apply

#### Scenario: UI checkbox label
- **WHEN** a user opens the import dialog
- **THEN** the override control SHALL be labelled "Overwrite user modifications"
- **THEN** the control's help text SHALL explain that manually edited executions and trades will be replaced by broker data

---

### Requirement: Manual execution to broker transaction link
The system SHALL provide an endpoint `POST /api/v1/executions/{execution_id}/link-broker-transaction` that links a `LogicalExecution` with `origin='manual'` to an existing `BrokerRawTransaction` owned by the same user. On success the endpoint SHALL set `LogicalExecution.source_id` to the raw transaction ID and set `BrokerRawTransaction.suppressed = True` in the same database transaction.

#### Scenario: Successful link
- **GIVEN** a manual execution `M` owned by user `U` and an unlinked BRT `R` also owned by `U`
- **WHEN** the user calls `POST /executions/M/link-broker-transaction` with body `{"raw_transaction_id": "R"}`
- **THEN** the response SHALL return `200 OK`
- **THEN** `M.source_id` SHALL equal `R.id`
- **THEN** `R.suppressed` SHALL be `true`

#### Scenario: Subsequent import skips the suppressed raw transaction
- **GIVEN** a linked manual execution `M` and its suppressed BRT `R`
- **WHEN** an import re-processes a file containing the same broker transaction id as `R`
- **THEN** no new `LogicalExecution` SHALL be created for `R`
- **THEN** `M` SHALL remain unchanged

#### Scenario: Reject non-manual origin
- **WHEN** the endpoint is called for an execution whose `origin` is not `manual`
- **THEN** the response SHALL be `409 Conflict`
- **THEN** the raw transaction's `suppressed` flag SHALL NOT change

#### Scenario: Reject cross-user link
- **WHEN** the endpoint is called with a `raw_transaction_id` owned by a different user
- **THEN** the response SHALL be `404 Not Found`

#### Scenario: Reject if raw transaction is already linked to a different logical execution
- **WHEN** the target BRT is already referenced by another `LogicalExecution.source_id`
- **THEN** the response SHALL be `409 Conflict` with an error message identifying the existing link

---

### Requirement: Manual execution deletion releases linked broker transaction
When `DELETE /api/v1/executions/{execution_id}` is called for a `LogicalExecution` with `origin='manual'` and a non-null `source_id`, the operation SHALL atomically (a) set `BrokerRawTransaction.suppressed = False` on the linked raw transaction and (b) hard-delete the logical execution. Both writes SHALL commit together or roll back together. Manual executions with `source_id = NULL` SHALL be deleted as today (no BRT update).

#### Scenario: Linked manual delete releases the BRT
- **GIVEN** a manual execution `M` with `source_id='R'` and `R.suppressed=true`
- **WHEN** the user deletes `M`
- **THEN** `M` SHALL be hard-deleted
- **THEN** `R.suppressed` SHALL become `false`
- **THEN** both changes SHALL be persisted in the same database transaction

#### Scenario: Follow-up import re-materialises the original execution
- **GIVEN** a released BRT `R` (previously linked, now `suppressed=false`)
- **WHEN** the next import re-processes a file containing `R`'s broker transaction id
- **THEN** a new `LogicalExecution` with `origin='imported'` and `source_id='R'` SHALL be created
- **THEN** the FIFO aggregator SHALL assign it to a trade normally

#### Scenario: Unlinked manual delete is unchanged
- **GIVEN** a manual execution `M2` with `source_id=NULL`
- **WHEN** the user deletes `M2`
- **THEN** `M2` SHALL be hard-deleted
- **THEN** no BRT SHALL be updated

#### Scenario: Rollback preserves both rows
- **WHEN** the release-and-delete transaction fails partway
- **THEN** both `M` and `R.suppressed=true` SHALL remain unchanged

---

### Requirement: Unlinked manual duplicate conflict flag
The system SHALL add a boolean column `trades.has_conflict` (default `false`) and manage its value via the FIFO aggregator's post-aggregation duplicate-detection pass. On every trade rebuild, the aggregator SHALL recompute `has_conflict` from the trade's current legs: `true` when at least one duplicate pair exists, `false` otherwise. A duplicate pair is defined as an imported leg and a manual leg on the same trade sharing `symbol`, `executed_at` (equal to the second), `direction`, `quantity`, and `price`, and where neither is linked to the other via `source_id`. Setting or clearing the flag SHALL NOT prevent the import from completing; it is a surfacing signal only.

#### Scenario: Duplicate detection sets the flag
- **GIVEN** a trade `T` with a manual leg `M` (`source_id=NULL`, `symbol='AAPL'`, `executed_at='2026-01-01T15:30:00Z'`, `direction='LONG'`, `quantity=100`, `price=190.00`)
- **WHEN** an import creates an imported leg `I` on `T` with the same five values
- **THEN** `T.has_conflict` SHALL become `true`
- **THEN** both legs SHALL remain in the database

#### Scenario: Linked manual replacement does not flag
- **GIVEN** a manual leg `M` with `source_id='R'` (already linked)
- **WHEN** an import processes `R`'s broker file
- **THEN** the imported leg SHALL be skipped (BRT is suppressed)
- **THEN** `T.has_conflict` SHALL NOT be set

#### Scenario: Different price is not a duplicate
- **GIVEN** a manual leg at `price=190.00` and an imported leg at `price=190.05` on the same trade
- **WHEN** the aggregator runs
- **THEN** `T.has_conflict` SHALL remain `false`

#### Scenario: Flag is exposed in the trade read response
- **WHEN** a client requests `GET /api/v1/trades/{id}`
- **THEN** the response body SHALL include `has_conflict: <boolean>`

#### Scenario: Deleting the duplicating leg auto-clears the flag
- **GIVEN** a trade `T` with `has_conflict=true` caused by duplicate pair `(I, M)`
- **WHEN** the user deletes `I` (or `M`) and the resulting trade re-aggregation runs
- **THEN** the aggregator SHALL recompute the flag from the remaining legs
- **THEN** `T.has_conflict` SHALL become `false` if no other duplicate pair remains

#### Scenario: Linking the manual leg auto-clears the flag
- **GIVEN** a trade `T` with `has_conflict=true` caused by duplicate pair `(I, M)` where `M` is manual and unlinked
- **WHEN** the user calls the manual-link endpoint on `M` to point at `I`'s BRT and re-aggregation runs
- **THEN** the aggregator SHALL treat `(I, M)` as linked (no longer a duplicate)
- **THEN** `T.has_conflict` SHALL become `false` if no other duplicate pair remains

#### Scenario: New duplicate on a rebuilt trade re-raises the flag
- **GIVEN** a trade `T` with `has_conflict=false`
- **WHEN** a subsequent import introduces a new duplicate pair on `T` and re-aggregation runs
- **THEN** `T.has_conflict` SHALL become `true`

---

### Requirement: Conflict pair is discoverable from trade legs
The trade executions endpoint SHALL return enough information for the client to identify which two legs form the duplicate pair without adding a new API field. Specifically, when `trade.has_conflict = true`, the response for `GET /api/v1/trades/{id}/executions` SHALL contain at least one pair of legs matching the duplicate key (`symbol`, `executed_at` to the second, `direction`, `quantity`, `price`), one with `origin='imported'` and the other with `origin='manual'` and `source_id=NULL`.

#### Scenario: Client can compute the highlighted pair from the leg list
- **GIVEN** a trade with `has_conflict=true` and legs `[I (imported), M (manual, source_id=NULL), X (imported, unrelated)]` where `I` and `M` share the five-field key
- **WHEN** the client requests `GET /trades/{id}/executions`
- **THEN** the response SHALL include all three legs
- **THEN** the client SHALL be able to identify `(I, M)` as the duplicate pair by matching the five-field key locally
- **THEN** the frontend trade detail page SHALL render a warning banner and visually mark both `I` and `M` in the executions table
