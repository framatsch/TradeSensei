## Purpose
Defines the protection mechanisms to prevent user-supplied data (such as metadata and manual edits) from being overwritten during automated data imports or re-aggregations.
## Requirements
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
The raw-pipeline trade rebuild SHALL NOT delete trades whose only remaining execution legs are all `user_modified=True`, and SHALL NOT reassign a `user_modified=True` leg to a different trade during re-aggregation. This protection is independent of `Trade.is_manually_edited`. In addition, the rebuild SHALL NOT delete any trade whose `is_manually_edited=True`, so that trades protected solely by user-supplied metadata (journal, rating, screenshots, tradingview link, playbook, notes, tags, annotations) survive the rebuild even if their legs are not individually `user_modified`.

#### Scenario: Trade backed by a user-modified leg survives the rebuild
- **GIVEN** trade `T` whose only leg `E1a` has `user_modified=true` and `is_manually_edited=false` on `T`
- **WHEN** the raw-pipeline import calls `delete_by_user_account` before re-aggregation
- **THEN** `T` SHALL NOT be deleted
- **THEN** `E1a` SHALL keep `trade_id=T`
- **THEN** trade-level metadata (playbook, tags, notes) SHALL remain unchanged

#### Scenario: Trade protected by metadata alone survives the rebuild
- **GIVEN** trade `T` with `is_manually_edited=true` (set by a metadata mutation) whose legs are all `user_modified=false`
- **WHEN** the raw-pipeline import calls `delete_by_user_account` with `overwrite_manually_edited=false`
- **THEN** `T` SHALL NOT be deleted
- **THEN** `T`'s metadata SHALL remain unchanged

#### Scenario: Aggregated fields recompute from protected legs
- **WHEN** re-aggregation runs over a trade whose legs mix `user_modified=true` and `user_modified=false` rows
- **THEN** the trade's cached fields (`pnl`, `entry_price`, `quantity`, etc.) SHALL reflect the current leg values
 - **THEN** no `user_modified=true` leg SHALL be mutated during re-aggregation

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

### Requirement: Trade cross-import identity uses a stable execution anchor

The system SHALL identify a **non-protected** trade across re-imports by its anchor execution — the chronologically-first non-deleted `LogicalExecution` linked to the trade (earliest `executed_at`, ties broken deterministically by execution `id`) — instead of the `(broker_conid, opened_at)` match-key. On rebuild, a newly computed trade whose anchor execution already backs an existing DB trade SHALL inherit that trade's `id`, preserving all related metadata. The anchor MAY be derived from existing data and SHALL NOT require a schema change.

Anchor resolution SHALL NOT be used to route a metadata-protected trade into the reconcile path. Because a protected trade's executions are excluded from the aggregation input, no rebuilt position can resolve to a protected trade's anchor.

#### Scenario: Trade identity survives FIFO re-slicing

- **GIVEN** a non-protected trade `T` whose entry leg is execution `E`
- **WHEN** a re-import re-aggregates `T`'s history into differently-sliced trades
- **THEN** the trade anchored by `E` SHALL inherit `T`'s `id`
- **THEN** `T`'s metadata SHALL remain attached to that trade

#### Scenario: Identity is stable when opened_at shifts

- **GIVEN** a non-protected trade `T` whose recomputed `opened_at` differs from the prior import (e.g. timestamp normalization)
- **WHEN** the rebuild resolves identity by anchor execution rather than `(broker_conid, opened_at)`
- **THEN** `T` SHALL still be recognized as the same trade and retain its metadata

#### Scenario: Deterministic tie-break for simultaneous fills

- **GIVEN** two entry executions with identical `executed_at`
- **WHEN** the anchor is derived
- **THEN** the anchor SHALL be selected deterministically by execution `id`

#### Scenario: Anchor resolution never targets a protected trade

- **GIVEN** a metadata-protected trade `T`
- **WHEN** the rebuild resolves anchors for the aggregated positions
- **THEN** no aggregated position SHALL resolve to `T`, because `T`'s executions are absent from the aggregation input

---

### Requirement: Metadata carries forward when the anchor execution is removed

When a rebuilt trade's prior anchor execution is no longer present in the active (non-deleted) set, the system SHALL transfer the old trade's metadata (columns `journal`, `user_rating`, `image_urls`, `tradingview_link`, `playbook_id`, and related `trade_notes`, `trade_taxonomies`, `trade_annotations` rows) to the trade anchored by the next-oldest surviving execution of that history, BEFORE the old trade row is deleted by the projection rebuild.

#### Scenario: Metadata follows the surviving execution history

- **GIVEN** a protected trade `T` with anchor execution `E1` and a later execution `E2`, and metadata attached to `T`
- **WHEN** `E1` is removed and a re-import re-anchors the history on `E2`
- **THEN** `T`'s metadata SHALL be transferred to the trade anchored by `E2` before `T` is deleted
- **THEN** no metadata SHALL be lost

#### Scenario: No carry-forward when the anchor persists

- **GIVEN** a protected trade whose anchor execution remains in the active set
- **WHEN** the rebuild runs
- **THEN** identity SHALL be inherited directly (per the anchor-identity requirement) and no carry-forward transfer SHALL occur

---

### Requirement: Import result reports protection-driven outcomes

`ImportResult` SHALL report the number of protected positions skipped, the number of executions left unlinked because their target trade was protected, and SHALL include a human-readable warning identifying each such occurrence (by symbol and date) so protection outcomes are never silent. Each occurrence SHALL additionally be emitted as a `logger.warning` record. These fields SHALL be additive and default such that existing clients are unaffected.

#### Scenario: Skipped protected position is reported

- **WHEN** an import skips a position because its trade is metadata-protected
- **THEN** `ImportResult` SHALL increment the protected-skipped count
- **THEN** the outcome SHALL be visible in the result rather than surfacing as an unexplained `trades_created = 0`

#### Scenario: Unlinked execution is reported

- **WHEN** an import leaves an execution unlinked because its target trade is protected
- **THEN** `ImportResult` SHALL increment the unlinked-execution count
- **THEN** `ImportResult.warnings` SHALL include an entry naming the symbol and execution date
- **THEN** a `logger.warning` record SHALL be emitted for that occurrence

### Requirement: Hard-delete reset of an imported execution releases the re-import guard

The system SHALL provide an explicit "reset to broker state" hard-delete for `origin='imported'` executions, distinct from the default soft-delete. When invoked, the system SHALL physically delete the `LogicalExecution` and, in the same atomic transaction, clear the re-import guard on the linked `BrokerRawTransaction` (`suppressed=False`) so the execution re-materialises unmodified on the next import. The default `DELETE` behaviour (soft-delete for imported legs) SHALL be unchanged when the reset intent is not supplied. The operation SHALL emit an audit event including the released source identifier.

#### Scenario: Reset re-materialises the broker leg on next import

- **GIVEN** an `imported` execution `E` linked to `BrokerRawTransaction` `R`
- **WHEN** the user invokes reset-to-broker-state on `E`
- **THEN** `E` SHALL be physically removed
- **THEN** `R.suppressed` SHALL become `false`
- **THEN** a subsequent import of the same broker data SHALL recreate `E` from `R`

#### Scenario: Default delete still soft-deletes an imported leg

- **WHEN** the user deletes an `imported` execution without the reset intent
- **THEN** the execution SHALL be soft-deleted (`deleted=true`), unchanged from prior behaviour
- **THEN** the linked raw transaction guard SHALL NOT be released

#### Scenario: Reset is audit-logged

- **WHEN** a reset-to-broker-state hard-delete succeeds
- **THEN** an audit event SHALL be recorded including the released source identifier

---

### Requirement: Orphaned imported executions are repaired by data migration

The change SHALL provide an idempotent, data-only Alembic migration that repairs already-orphaned imported executions (`origin='imported'`, `deleted=false`, `trade_id IS NULL`). For each orphan, the migration SHALL resolve the owning open trade by matching `user_id`, `account_id`, `symbol`, complementary direction, and `quantity` against open trades, link the execution's `trade_id`, and recompute the trade's `exit_price`, `closed_at`, `pnl`, `net_pnl`, and `commission` from its now-complete leg set. When zero or more than one candidate trade matches, the migration SHALL skip the orphan and log it rather than guess. The downgrade SHALL be a no-op.

#### Scenario: Stuck closing execution is linked and its trade closed

- **GIVEN** an orphaned imported closing execution whose complementary open trade uniquely matches on `(user, account, symbol, direction, quantity)`
- **WHEN** the migration runs
- **THEN** the execution SHALL be linked to that trade
- **THEN** the trade SHALL be recomputed as closed with the correct `exit_price`/`closed_at`/`pnl`

#### Scenario: Ambiguous or unmatched orphan is skipped, not guessed

- **GIVEN** an orphaned execution with zero or multiple candidate trades
- **WHEN** the migration runs
- **THEN** the execution SHALL be left unchanged
- **THEN** the migration SHALL log the skipped orphan

#### Scenario: Migration is idempotent

- **WHEN** the migration is run more than once
- **THEN** already-linked executions SHALL be unaffected and no duplicate links or recomputations SHALL occur

---

### Requirement: Trade metadata mutation marks protection

The system SHALL mark a trade and its executions as user-protected whenever the trade acquires or changes any user-supplied metadata. The protected metadata signals are the trade columns `journal`, `user_rating`, `image_urls`, `tradingview_link`, and `playbook_id`, plus the related collections `trade_notes`, `trade_taxonomies` (tags), and `trade_annotations`. When `PATCH /api/v1/trades/{id}` mutates any of the listed columns, the operation SHALL set `Trade.is_manually_edited = True` AND set `LogicalExecution.user_modified = True` on every non-deleted execution linked to that trade. The screenshot add/remove flow, which routes through the same trade-update path, SHALL be covered by this rule. The existing note, tag, and annotation assignment endpoints SHALL continue to mark `Trade.is_manually_edited = True` and SHALL additionally set `user_modified = True` on the trade's non-deleted executions.

#### Scenario: Adding a journal marks the trade and its executions

- **GIVEN** an imported trade `T` with `is_manually_edited=false` and legs all `user_modified=false`
- **WHEN** the user patches `T` with a non-empty `journal`
- **THEN** `T.is_manually_edited` SHALL become `true`
- **THEN** every non-deleted leg of `T` SHALL have `user_modified=true`

#### Scenario: Uploading a screenshot marks protection

- **WHEN** the user adds a screenshot to trade `T` (mutating `image_urls`)
- **THEN** `T.is_manually_edited` SHALL become `true`
- **THEN** every non-deleted leg of `T` SHALL have `user_modified=true`

#### Scenario: Setting a rating or tradingview link marks protection

- **WHEN** the user patches `T` with `user_rating` or `tradingview_link`
- **THEN** `T.is_manually_edited` SHALL become `true`
- **THEN** every non-deleted leg of `T` SHALL have `user_modified=true`

#### Scenario: Assigning a playbook marks protection

- **WHEN** the user patches `T` with a `playbook_id`
- **THEN** `T.is_manually_edited` SHALL become `true`
- **THEN** every non-deleted leg of `T` SHALL have `user_modified=true`

#### Scenario: Assigning a tag marks execution-level protection

- **WHEN** the user assigns a taxonomy (tag) to trade `T`
- **THEN** `T.is_manually_edited` SHALL become `true`
- **THEN** every non-deleted leg of `T` SHALL have `user_modified=true`

#### Scenario: A trade with metadata survives re-import

- **GIVEN** a trade `T` protected by any metadata signal
- **WHEN** a broker re-import rebuilds the account projection with `overwrite_manually_edited=false`
- **THEN** `T` SHALL NOT be deleted
- **THEN** `T`'s metadata (journal, rating, screenshots, tradingview link, playbook, notes, tags, annotations) SHALL remain unchanged

#### Scenario: Non-metadata patch does not mark protection

- **WHEN** the user patches only re-aggregation fields (e.g. `direction`) with no metadata field present
- **THEN** the metadata-marking rule SHALL NOT apply from this requirement (behaviour of those fields is unchanged)

---

### Requirement: Legacy metadata protection backfill migration

The change SHALL provide an Alembic data-migration (no schema change) that retroactively protects trades edited before this protection shipped. The migration SHALL set `Trade.is_manually_edited = True` for every trade that carries any metadata signal: `journal IS NOT NULL AND journal <> ''`, `user_rating IS NOT NULL`, `image_urls <> '[]'`, `tradingview_link IS NOT NULL`, `playbook_id IS NOT NULL`, or the existence of at least one related `trade_notes`, `trade_taxonomies`, or `trade_annotations` row. For every trade so marked, the migration SHALL set `LogicalExecution.user_modified = True` on all of that trade's non-deleted executions. The migration SHALL additionally set `user_modified = True` on any `origin='imported'` execution whose `price`, `quantity`, or `commission` differs (beyond a Decimal tolerance) from its linked `BrokerRawTransaction` (matched via `source_id`); `symbol` differences SHALL be ignored because corporate-action remaps legitimately change the symbol. The migration SHALL NOT mark `origin` values `split`, `merged`, or `manual` en masse. The downgrade SHALL be a no-op (the backfilled boolean values are not reverted, since the pre-migration state is unrecoverable and reverting would re-expose the data-loss path).

#### Scenario: Legacy trade with a journal is backfilled

- **GIVEN** a trade `T` with a non-empty `journal`, `is_manually_edited=false`, and legs `user_modified=false`, created before this change
- **WHEN** the migration runs
- **THEN** `T.is_manually_edited` SHALL become `true`
- **THEN** every non-deleted leg of `T` SHALL have `user_modified=true`

#### Scenario: Legacy trade with only notes is backfilled

- **GIVEN** a trade `T` with at least one `trade_notes` row and no other metadata
- **WHEN** the migration runs
- **THEN** `T.is_manually_edited` SHALL become `true`
- **THEN** every non-deleted leg of `T` SHALL have `user_modified=true`

#### Scenario: Divergent imported leg is backfilled

- **GIVEN** an `origin='imported'` execution `E` with `source_id='R'` whose `price` differs from `BrokerRawTransaction R.price` beyond tolerance
- **WHEN** the migration runs
- **THEN** `E.user_modified` SHALL become `true`

#### Scenario: Symbol-only divergence is not treated as an edit

- **GIVEN** an `origin='imported'` execution `E` whose `symbol` differs from its BRT (corporate-action remap) but whose `price`, `quantity`, and `commission` match
- **WHEN** the migration runs
- **THEN** `E.user_modified` SHALL remain `false` (unless another rule marks it)

#### Scenario: Clean imported trade is not marked

- **GIVEN** a trade `T` with no metadata and legs matching their BRTs exactly
- **WHEN** the migration runs
- **THEN** `T.is_manually_edited` SHALL remain `false`
- **THEN** its legs SHALL remain `user_modified=false`

---

### Requirement: Import guard clause on zero inserts

When a raw-pipeline import inserts exactly zero new `BrokerRawTransaction` rows and the request's `overwrite_manually_edited` flag is `false`, the import SHALL skip the split-child purge (`delete_split_children_for_account`), the parent restore (`restore_split_parents_for_account`), and the full trade-projection rebuild. The import SHALL still complete successfully and report `raw_transactions_created = 0`. When `overwrite_manually_edited` is `true`, the rebuild SHALL run even on zero inserts (preserving the explicit reset semantics of the override).

#### Scenario: Re-uploading an already-imported file is a no-op rebuild

- **GIVEN** an account whose broker file has already been imported
- **WHEN** the same file is re-uploaded with `overwrite_manually_edited=false` and yields zero new raw rows
- **THEN** the split purge, parent restore, and projection rebuild SHALL NOT run
- **THEN** all existing trades and their metadata SHALL remain unchanged
- **THEN** the import response SHALL report `raw_transactions_created=0`

#### Scenario: Override forces rebuild even with zero inserts

- **WHEN** a zero-insert import runs with `overwrite_manually_edited=true`
- **THEN** the split purge and projection rebuild SHALL run
- **THEN** user-modified rows SHALL be subject to the override as defined by "Overwrite user modifications override"

#### Scenario: Non-zero inserts run the rebuild as before

- **WHEN** an import inserts one or more new raw rows
- **THEN** the split purge, parent restore, and rebuild SHALL run as today

---

### Requirement: Execution symbol change re-aggregates all affected trades

When `PATCH /api/v1/executions/{id}` changes an execution's `symbol`, the service SHALL read the previous `symbol` before applying the update, then re-aggregate the execution's own trade (its `trade_id` is unchanged by the patch — the leg is not moved to a different trade), and SHALL additionally re-aggregate every other trade in the account whose `symbol` still matches the old value, as a safety net against those trades having gone stale. A patch that does not change `symbol` SHALL re-aggregate only the affected trade as today.

> **NOTE**: This is not a two-chain split of one moved leg. `Trade.symbol` is never updated by this code path; the execution's trade keeps re-aggregating under its (now-changed) `symbol`. The old-symbol sweep only touches *other*, pre-existing trades that happen to share the old symbol string — it does not construct or correct a "new-symbol trade" for the moved leg. Whether `Trade.symbol` should retarget instead is an open design question..

#### Scenario: Symbol change re-aggregates the execution's trade and sweeps other old-symbol trades

- **GIVEN** an execution `E` on trade `T` with `symbol='AAA'`
- **WHEN** the user patches `E.symbol` to `'BBB'`
- **THEN** `E.user_modified` SHALL become `true` (per the existing marker rule)
- **THEN** re-aggregation SHALL run for `T` (now containing the `'BBB'`-symbol leg)
- **THEN** re-aggregation SHALL run for every other account trade whose `symbol` is still `'AAA'`

#### Scenario: Non-symbol patch re-aggregates only the affected trade

- **WHEN** the user patches `E.price` without changing `symbol`
- **THEN** only `E`'s current trade SHALL be re-aggregated

---

### Requirement: Trade list filter by execution state

`GET /api/v1/trades` SHALL accept an optional repeatable query parameter `execution_state` whose values are drawn from `manual`, `edited`, and `imported`. The filter SHALL be implemented with `EXISTS` subqueries against `logical_executions`. A trade SHALL be returned when at least one of its non-deleted executions matches at least one requested state (OR semantics across the provided values). The state predicates are: `manual` → an execution with `origin='manual'`; `edited` → an execution with `user_modified=True`; `imported` → an execution with `origin='imported'` and `user_modified=False`. When `execution_state` is omitted, the trade list SHALL be unfiltered by execution state.

#### Scenario: Filter by edited returns trades with a user-modified leg

- **GIVEN** trades `T1` (has a `user_modified=true` leg) and `T2` (all legs `user_modified=false`)
- **WHEN** the client requests `GET /api/v1/trades?execution_state=edited`
- **THEN** the response SHALL include `T1`
- **THEN** the response SHALL NOT include `T2`

#### Scenario: Filter by manual returns trades with a manual leg

- **WHEN** the client requests `GET /api/v1/trades?execution_state=manual`
- **THEN** only trades with at least one `origin='manual'` leg SHALL be returned

#### Scenario: Filter by imported returns trades with an unmodified imported leg

- **WHEN** the client requests `GET /api/v1/trades?execution_state=imported`
- **THEN** only trades with at least one `origin='imported'` and `user_modified=false` leg SHALL be returned

#### Scenario: Multiple states use OR semantics

- **WHEN** the client requests `GET /api/v1/trades?execution_state=manual&execution_state=edited`
- **THEN** a trade SHALL be returned if it has a manual leg OR an edited leg

#### Scenario: Omitting the parameter does not filter by state

- **WHEN** the client requests `GET /api/v1/trades` with no `execution_state`
- **THEN** the execution-state filter SHALL NOT restrict the result set

---

### Requirement: Trade table UI exposes the execution-state filter

The trades list filter panel (`TradeFilterBar`) SHALL provide a control for the execution-state filter with the selectable values `Manual`, `Edited`, and `Imported`, allowing zero or more to be active at once (multi-select). The selected values SHALL be carried on the client `TradeFilters` object as `execution_state`, sent to `GET /api/v1/trades` by the trades query hook, serialized to and read from the URL query string for shareable/saved views, counted in the active-filter badge, and cleared by "Clear Filters". When no value is selected, the client SHALL omit the parameter.

#### Scenario: Selecting a state filters the table

- **WHEN** the user activates the `Edited` value in the trade filter panel
- **THEN** the trades query SHALL send `execution_state=edited`
- **THEN** the table SHALL show only trades with at least one edited leg

#### Scenario: Multiple selected states are sent together

- **WHEN** the user activates both `Manual` and `Edited`
- **THEN** the trades query SHALL send both values
- **THEN** the table SHALL show trades matching either state (OR semantics)

#### Scenario: The filter round-trips through the URL

- **WHEN** the user selects `Imported` and reloads the page (or opens a saved view carrying the value)
- **THEN** the `Imported` value SHALL be restored as active in the filter panel
- **THEN** the table SHALL reflect the filter

#### Scenario: Active-filter badge and clear

- **WHEN** at least one execution-state value is active
- **THEN** the filter badge count SHALL include the execution-state filter
- **WHEN** the user clicks "Clear Filters"
- **THEN** the execution-state selection SHALL be cleared and the parameter omitted

### Requirement: Metadata-protected trades are isolated from the projection rebuild

During a raw-pipeline projection rebuild, the system SHALL treat every trade with `is_manually_edited=true` as immutable. Specifically, the system SHALL exclude that trade's non-deleted `LogicalExecution` rows from the aggregation input (both combo grouping and FIFO matching), SHALL NOT apply any field update to the trade, and SHALL NOT reassign any of the trade's executions to another trade during trade-link backfill. Protected trades remain exempt from deletion as already specified.

#### Scenario: Protected closed trade survives a re-import unchanged

- **GIVEN** a closed, metadata-protected trade `T` with linked opening and closing executions
- **WHEN** a raw-pipeline import runs for `T`'s account
- **THEN** `T.closed_at`, `T.pnl`, and `T.net_pnl` SHALL be unchanged
- **THEN** every execution linked to `T` SHALL still have `trade_id = T.id`
- **THEN** no new trade SHALL be created from `T`'s executions

#### Scenario: Protected trade executions do not enter FIFO aggregation

- **GIVEN** a metadata-protected trade `T` with two non-deleted executions
- **WHEN** the rebuild collects executions for aggregation
- **THEN** neither execution SHALL appear in the FIFO or combo aggregation input

#### Scenario: Backfill refuses to steal a protected trade's execution

- **GIVEN** an execution `E` linked to a metadata-protected trade `T`
- **WHEN** trade-link backfill computes an assignment that would move `E` to a different trade
- **THEN** the assignment SHALL be discarded and `E.trade_id` SHALL remain `T.id`

---

### Requirement: Unlinkable executions are reported and flagged

When an incoming broker execution cannot be linked because the trade it belongs to is metadata-protected, the system SHALL leave the execution unlinked (`trade_id IS NULL`, `deleted=false`) rather than creating a substitute trade for it, and SHALL set `has_unlinked_executions=true` on the protected trade the execution was associated with. The flag SHALL be cleared when a subsequent import or re-aggregation finds no unlinked executions for that trade. `TradeRead` SHALL expose the flag.

#### Scenario: New closing execution for a protected trade stays unlinked

- **GIVEN** a metadata-protected trade `T` for instrument `I`
- **WHEN** an import brings a new closing execution `E` for `I` that would belong to `T`
- **THEN** `E.trade_id` SHALL remain `NULL`
- **THEN** no substitute trade SHALL be created for `E`
- **THEN** `T.has_unlinked_executions` SHALL become `true`

#### Scenario: Flag clears once the situation is resolved

- **GIVEN** a trade `T` with `has_unlinked_executions=true`
- **WHEN** the user links the outstanding execution to `T` and a re-aggregation runs
- **THEN** `T.has_unlinked_executions` SHALL become `false`

---

### Requirement: Orphan lot suppression for protected contracts

The FIFO aggregator's sentinel orphan lot (`entry_price = 0.001`) SHALL NOT be created for a closing execution whose `(symbol, conid)` is held by a metadata-protected trade. Such an execution SHALL instead be left unlinked and reported. Orphan lot creation for all other unmatched closing executions (e.g. genuinely transferred-in positions) SHALL be unchanged.

#### Scenario: No sentinel trade for a protected contract

- **GIVEN** a metadata-protected trade holding contract `C`, whose executions are excluded from the aggregation input
- **WHEN** a closing execution for `C` cannot be FIFO-matched as a result
- **THEN** no trade with `entry_price = 0.001` SHALL be created for it
- **THEN** the execution SHALL be reported as unlinked

#### Scenario: Orphan lots still created for unrelated transferred-in positions

- **GIVEN** a closing execution for a contract that is not held by any protected trade and has no matching open lot
- **WHEN** the aggregator processes it
- **THEN** the existing sentinel orphan lot SHALL be created as before

---

### Requirement: Trade merge marks protection

When the user merges two or more trades, the system SHALL mark the surviving trade `is_manually_edited=true` and SHALL mark every non-deleted `LogicalExecution` linked to the survivor `user_modified=true`, so the merge result is protected by both the trade-level and the execution-level gate.

#### Scenario: Merged trade is protected against rebuild

- **WHEN** the user merges trades `A` and `B` into survivor `S`
- **THEN** `S.is_manually_edited` SHALL be `true`
- **THEN** every non-deleted execution linked to `S` SHALL have `user_modified=true`

#### Scenario: Merged trade survives a subsequent import intact

- **GIVEN** a merged trade `S` produced from broker-imported executions
- **WHEN** a raw-pipeline import runs for `S`'s account
- **THEN** `S` SHALL retain its identity, its structural fields, and all of its linked executions

---

### Requirement: Execution merge marks protection

When the user merges two or more executions into a single merged execution, the system SHALL mark the resulting merged execution `user_modified=true` and its owning trade `is_manually_edited=true`.

#### Scenario: Merged execution is protected

- **WHEN** the user merges executions into a merged leg `M` on trade `T`
- **THEN** `M.user_modified` SHALL be `true`
- **THEN** `T.is_manually_edited` SHALL be `true`

---

### Requirement: Trade list filter by unlinked executions

`GET /api/v1/trades` SHALL accept an optional boolean filter that restricts results to trades with `has_unlinked_executions=true`. The parameter SHALL be additive and optional so existing clients and saved views are unaffected. The trades-table filter panel SHALL expose a matching control that round-trips through the URL and saved views and participates in the active-filter count and "Clear Filters".

#### Scenario: Filter returns only flagged trades

- **GIVEN** an account with flagged and unflagged trades
- **WHEN** the client requests trades with the unlinked-executions filter enabled
- **THEN** only trades with `has_unlinked_executions=true` SHALL be returned

#### Scenario: Omitting the parameter preserves existing behaviour

- **WHEN** a client omits the parameter
- **THEN** results SHALL be identical to the behaviour before this change

#### Scenario: Saved views without the key remain valid

- **GIVEN** a saved view stored before this change
- **WHEN** it is loaded
- **THEN** the filter SHALL be inactive and the view SHALL apply unchanged

---

### Requirement: Protection applies to every ingestion entry point

The execution-overwrite protections — protected-trade rebuild isolation, orphan-lot suppression for protected contracts, backfill link guarding, and protection reporting — SHALL hold for every path by which broker data enters the system, including file upload, scheduled account sync, and direct broker API pull. No ingestion path may reach trade persistence without passing through the protected-trade isolation.

This requirement exists because the protections were implemented in `ImportService` while the IBKR Flex sync used a separate implementation. A protected trade was correctly preserved while the sync simultaneously created phantom sentinel trades shadowing the same contracts, so the account was corrupted despite the protection working exactly as specified.

#### Scenario: Protected trade survives an API sync

- **GIVEN** a metadata-protected trade `T`
- **WHEN** trade data covering `T`'s contracts arrives through a broker API sync rather than a file upload
- **THEN** `T`'s structural fields SHALL be unchanged
- **THEN** `T`'s executions SHALL remain linked to `T`
- **THEN** no sentinel orphan trade SHALL be created for a contract held by `T`

#### Scenario: Protection uses execution identity on every path

- **WHEN** any ingestion path determines whether a trade is protected
- **THEN** it SHALL use the protected-execution snapshot
- **THEN** it SHALL NOT use the `(broker_conid, opened_at)` match key, which does not survive FIFO re-slicing

#### Scenario: Protection outcomes are reported on every path

- **WHEN** a protection-driven skip or unlinked execution occurs during any ingestion
- **THEN** the outcome SHALL appear in the result returned to the caller and in the application log

