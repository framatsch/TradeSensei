## REMOVED Requirements

### Requirement: Import reconciles new executions onto metadata-protected trades

**Reason**: This requirement caused a confirmed production data-loss incident. It mandated that a resolved metadata-protected trade is *always* reconciled, on the assumption that a structural `exclude_unset` update "never touches metadata columns" and is therefore safe. The assumption holds for metadata but not for structure: `closed_at`, `pnl`, and `net_pnl` are not metadata columns and were overwritten with `NULL` whenever the aggregator could not reconstruct the full position. Independently, the requirement placed no constraint on `_backfill_execution_trade_links`, which re-assigned the protected trade's own executions to newly created trades. Trade `8436a93e` (QQQ vertical, `is_manually_edited=true`) was reverted from closed to open and stripped of both closing legs by exactly this path, despite being protected.

The requirement's scenario "Import never produces an orphaned imported execution" is also deliberately reversed: leaving an execution unlinked and reporting it is now the specified, safe outcome when its target trade is protected.

**Migration**: Superseded by "Metadata-protected trades are isolated from the projection rebuild" and "Unlinkable executions are reported and flagged" below. The orphaned-execution problem this requirement was written to solve is instead addressed by making the outcome explicit and visible (`has_unlinked_executions`, `ImportResult` counts and warnings) rather than by mutating protected trades.

## MODIFIED Requirements

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

## ADDED Requirements

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
