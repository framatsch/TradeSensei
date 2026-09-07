## MODIFIED Requirements

### Requirement: Metadata-protected trades are isolated from the projection rebuild

During a raw-pipeline projection rebuild, the system SHALL treat every **closed** trade
with `is_manually_edited=true` as immutable. Specifically, for a closed protected trade
the system SHALL exclude that trade's non-deleted `LogicalExecution` rows from the
aggregation input (both combo grouping and FIFO matching), SHALL NOT apply any field
update to the trade, and SHALL NOT reassign any of the trade's executions to another
trade during trade-link backfill.

An **open** trade with `is_manually_edited=true` (`closed_at IS NULL`) SHALL instead
participate in the rebuild as a seed lot: its non-deleted `LogicalExecution` rows SHALL
enter the FIFO aggregation input carrying the trade's identifier, so that an incoming
closing execution can be matched against it. The system SHALL NOT create a second trade
row from a seed lot, SHALL NOT mutate the values of the seeded executions, and SHALL NOT
reassign a seeded execution to a different trade. When a seed lot remains unmatched at
the end of aggregation, the trade SHALL remain open and unchanged.

Protected trades remain exempt from deletion as already specified.

For Schwab imports, a zero-insert pass (no newly inserted raw rows, no released raw
rows, no overwrite override) SHALL still run a projection rebuild when at least one
open metadata-protected trade has a non-deleted, unlinked execution on the same
contract that can be absorbed by FIFO matching. Contracts with an unresolved manual
stand-in (`origin='manual'` and `source_id IS NULL`) SHALL be excluded from this
trigger.

#### Scenario: Protected closed trade survives a re-import unchanged

- **GIVEN** a closed, metadata-protected trade `T` with linked opening and closing executions
- **WHEN** a raw-pipeline import runs for `T`'s account
- **THEN** `T.closed_at`, `T.pnl`, and `T.net_pnl` SHALL be unchanged
- **THEN** every execution linked to `T` SHALL still have `trade_id = T.id`
- **THEN** no new trade SHALL be created from `T`'s executions

#### Scenario: Closed protected trade executions do not enter FIFO aggregation

- **GIVEN** a closed metadata-protected trade `T` with two non-deleted executions
- **WHEN** the rebuild collects executions for aggregation
- **THEN** neither execution SHALL appear in the FIFO or combo aggregation input

#### Scenario: Open protected trade enters FIFO as a seed lot

- **GIVEN** an open metadata-protected trade `T` for instrument `I` with one non-deleted opening execution `E1`
- **WHEN** the rebuild collects executions for aggregation
- **THEN** `E1` SHALL appear in the FIFO aggregation input carrying `T`'s identifier
- **THEN** no additional trade row SHALL be created for `E1`

#### Scenario: Unmatched seed lot leaves the trade untouched

- **GIVEN** an open metadata-protected trade `T` seeded into aggregation
- **WHEN** the import contains no closing execution for `T`'s contract
- **THEN** `T.closed_at` SHALL remain `NULL`
- **THEN** `T`'s quantity, entry price, and commission SHALL be unchanged
- **THEN** `E1.trade_id` SHALL still be `T.id`

#### Scenario: Zero-insert Schwab import still heals a previously stuck protected close

- **GIVEN** a Schwab account with an open metadata-protected trade `T` and an unlinked closing execution `E2` on the same `(symbol, conid)`
- **AND** the import payload contributes no newly inserted or released raw rows
- **WHEN** the import runs with `overwrite_manually_edited=false`
- **THEN** the projection rebuild SHALL still run
- **THEN** `E2` SHALL be linked to `T`
- **THEN** `T` SHALL close using broker-derived aggregate fields

#### Scenario: Unresolved manual stand-in does not trigger zero-insert rebuild

- **GIVEN** a contract `C` with an unresolved manual stand-in (`origin='manual'`, `source_id IS NULL`)
- **AND** an unlinked imported execution exists for `C`
- **WHEN** a zero-insert Schwab import runs without overwrite
- **THEN** this condition alone SHALL NOT trigger a projection rebuild

#### Scenario: Backfill refuses to steal a protected trade's execution

- **GIVEN** an execution `E` linked to a metadata-protected trade `T`
- **WHEN** trade-link backfill computes an assignment that would move `E` to a different trade
- **THEN** the assignment SHALL be discarded and `E.trade_id` SHALL remain `T.id`

---

### Requirement: Unlinkable executions are reported and flagged

The system SHALL leave an incoming broker execution unlinked (`trade_id IS NULL`,
`deleted=false`) rather than creating a substitute trade for it, when the trade it
belongs to is a **closed** metadata-protected trade, and SHALL set
`has_unlinked_executions=true` on the protected trade the execution was associated
with. The flag SHALL be cleared when a subsequent import or re-aggregation finds no
unlinked executions for that trade. `TradeRead` SHALL expose the flag.

A closing execution that is successfully matched against an **open** protected trade's
seed lot SHALL be linked to that trade and SHALL NOT be counted as unlinked.

When an execution is left unlinked because of an unresolved manual stand-in contract,
the system SHALL set `has_unlinked_executions=true` on at least one trade that holds
that contract in the same user/account scope, and SHALL expose that flag through the
trade list filter `has_unlinked_executions=true` so the trading overview can show a
system filter for "needs linking" cases.

#### Scenario: New closing execution for a closed protected trade stays unlinked

- **GIVEN** a closed metadata-protected trade `T` for instrument `I`
- **WHEN** an import brings a new closing execution `E` for `I`
- **THEN** `E.trade_id` SHALL remain `NULL`
- **THEN** no substitute trade SHALL be created for `E`
- **THEN** `T.has_unlinked_executions` SHALL become `true`

#### Scenario: Closing execution for an open protected trade is linked

- **GIVEN** an open metadata-protected trade `T` for instrument `I` with opening execution `E1`
- **WHEN** an import brings a closing execution `E2` for `I` that FIFO-matches `E1`
- **THEN** `E2.trade_id` SHALL be `T.id`
- **THEN** the import's unlinked-execution count SHALL NOT include `E2`
- **THEN** `T.has_unlinked_executions` SHALL be `false`

#### Scenario: Flag clears once the situation is resolved

- **GIVEN** a trade `T` with `has_unlinked_executions=true`
- **WHEN** the user links the outstanding execution to `T` and a re-aggregation runs
- **THEN** `T.has_unlinked_executions` SHALL become `false`

#### Scenario: Manual stand-in unresolved case is visible in trade overview

- **GIVEN** an imported closing execution is left unlinked because a manual stand-in exists for the same contract
- **WHEN** the user requests trades with `has_unlinked_executions=true`
- **THEN** the response SHALL include at least one trade for that contract in the same account
- **THEN** that trade SHALL have `has_unlinked_executions=true`

---

### Requirement: Orphan lot suppression for protected contracts

The FIFO aggregator's sentinel orphan lot (`entry_price = 0.001`) SHALL NOT be created
for a closing execution whose `(symbol, conid)` is held by a **closed**
metadata-protected trade. Such an execution SHALL instead be left unlinked and reported.

A contract held by an **open** protected trade SHALL NOT be treated as suppressed,
because that trade's seed lot is present in the aggregation input and the closing
execution is expected to match it. If such a closing execution still cannot be matched
(for example because the seeded quantity is smaller than the closing quantity), the
unmatched remainder SHALL follow the ordinary orphan-lot rules.

Orphan lot creation for all other unmatched closing executions (e.g. genuinely
transferred-in positions) SHALL be unchanged.

Additionally, the FIFO aggregator's sentinel orphan lot SHALL NOT be created when an
unmatched closing execution belongs to a contract that has an unresolved manual
stand-in candidate in the same user/account scope: at least one non-deleted
`origin='manual'` execution with `source_id IS NULL` and at least one non-deleted
non-manual execution on the same `(symbol, conid)`. In this case the execution SHALL be
left unlinked and reported as an unresolved manual stand-in, so the user can resolve it
by linking the manual leg or deleting one of the duplicate legs.

#### Scenario: No sentinel trade for a contract held by a closed protected trade

- **GIVEN** a closed metadata-protected trade holding contract `C`, whose executions are excluded from the aggregation input
- **WHEN** a closing execution for `C` cannot be FIFO-matched as a result
- **THEN** no trade with `entry_price = 0.001` SHALL be created for it
- **THEN** the execution SHALL be reported as unlinked

#### Scenario: Contract held by an open protected trade is not suppressed

- **GIVEN** an open metadata-protected trade holding contract `C` with an opening quantity of 10
- **WHEN** a closing execution for `C` with quantity 10 is aggregated
- **THEN** the closing execution SHALL be matched against the seed lot
- **THEN** no sentinel orphan lot SHALL be created

#### Scenario: Over-closing an open protected trade produces an ordinary remainder

- **GIVEN** an open metadata-protected trade holding contract `C` with an opening quantity of 3
- **WHEN** a closing execution for `C` with quantity 5 is aggregated
- **THEN** 3 units SHALL be matched against the seed lot
- **THEN** the remaining 2 units SHALL be handled by the ordinary orphan-lot rules
- **THEN** the import SHALL report a warning identifying the contract and the remainder

#### Scenario: Orphan lots still created for unrelated transferred-in positions

- **GIVEN** a closing execution for a contract that is not held by any protected trade and has no matching open lot
- **WHEN** the aggregator processes it
- **THEN** the existing sentinel orphan lot SHALL be created as before

#### Scenario: Manual stand-in suppresses sentinel orphan lot

- **GIVEN** contract `C` has a non-deleted unlinked manual execution (`origin='manual'`, `source_id IS NULL`) and a non-deleted non-manual execution in the same user/account scope
- **WHEN** an imported closing execution for `C` is unmatched by FIFO
- **THEN** no trade with `entry_price = 0.001` SHALL be created for that execution
- **THEN** the execution SHALL remain unlinked and be reported with a warning indicating an unresolved manual stand-in

---

## ADDED Requirements

### Requirement: Trade-level mutations do not mark executions as user-modified

`LogicalExecution.user_modified` SHALL be set only when the user mutates an execution
itself, that is via `PATCH /api/v1/executions/{id}` or an execution merge. Trade-level
mutations SHALL NOT set `user_modified` on any execution. This includes notes, tags,
taxonomy assignments, annotation assignments, journal, user rating, screenshots,
TradingView link, playbook assignment, trade update, and trade merge.

Such trade-level mutations SHALL continue to set `Trade.is_manually_edited = true`,
which alone provides deletion protection for the trade during a projection rebuild.

#### Scenario: Adding a note does not mark the executions

- **GIVEN** an open trade `T` whose legs all have `user_modified=false`
- **WHEN** the user adds a note to `T`
- **THEN** `T.is_manually_edited` SHALL become `true`
- **THEN** every leg of `T` SHALL still have `user_modified=false`

#### Scenario: Adding a tag does not mark the executions

- **GIVEN** an open trade `T` whose legs all have `user_modified=false`
- **WHEN** the user assigns a taxonomy, annotation, or rating to `T`
- **THEN** `T.is_manually_edited` SHALL become `true`
- **THEN** every leg of `T` SHALL still have `user_modified=false`

#### Scenario: Merging two trades does not mark their executions

- **GIVEN** two trades `T1` and `T2` whose legs all have `user_modified=false`
- **WHEN** the user merges `T2` into `T1`
- **THEN** `T1.is_manually_edited` SHALL become `true`
- **THEN** every leg now attached to `T1` SHALL still have `user_modified=false`

#### Scenario: Editing an execution still marks it

- **GIVEN** an imported leg `E` with `user_modified=false`
- **WHEN** the user patches `E`'s price
- **THEN** `E.user_modified` SHALL become `true`

#### Scenario: A documented trade is still protected from deletion

- **GIVEN** an open trade `T` protected only by a note, whose legs all have `user_modified=false`
- **WHEN** a raw-pipeline import calls `delete_by_user_account` with `overwrite_manually_edited=false`
- **THEN** `T` SHALL NOT be deleted
- **THEN** `T`'s note SHALL remain attached to `T`

---

### Requirement: Imports never write user-supplied metadata

A projection rebuild SHALL NOT write any user-supplied metadata field of an existing
trade. This applies to `journal`, `user_rating`, `image_urls`, `tradingview_link`,
`playbook_id`, and `is_manually_edited`, and to the related rows `trade_notes`,
`trade_taxonomies`, and `trade_annotations`. Only broker-derived and aggregate-derived
fields — `quantity`, `entry_price`, `exit_price`, `opened_at`, `closed_at`, `pnl`,
`pnl_eur`, `net_pnl`, `net_pnl_eur`, `commission`, `direction`, `asset_class`,
`multiplier`, `currency`, `broker_conid`, `broker_order_id`, `position_id`,
`is_combo`, `has_conflict`, `has_unlinked_executions` — SHALL be written.

#### Scenario: Closing a documented open trade preserves its documentation

- **GIVEN** an open protected trade `T` with a journal entry, a rating, a playbook, a note, and a tag
- **WHEN** an import brings a closing execution that matches `T`'s seed lot
- **THEN** `T.closed_at`, `T.exit_price`, `T.pnl`, and `T.net_pnl` SHALL be updated
- **THEN** `T.journal`, `T.user_rating`, `T.image_urls`, `T.tradingview_link`, and `T.playbook_id` SHALL be unchanged
- **THEN** `T`'s note, taxonomy assignment, and annotation assignment SHALL still reference `T`
- **THEN** `T.is_manually_edited` SHALL remain `true`

#### Scenario: Updating an unprotected trade also preserves metadata

- **GIVEN** an unprotected trade `T` that carries a journal entry
- **WHEN** a rebuild updates `T` from recomputed aggregate values
- **THEN** `T.journal` SHALL be unchanged

---

### Requirement: Falsely-set user-modified markers are cleared

The change SHALL provide an idempotent, data-only Alembic migration that clears
`LogicalExecution.user_modified` for every row that provably was not edited by the user.
A row qualifies when its `origin` is not `manual` and either its `source_id` resolves to
a `BrokerRawTransaction` whose `quantity`, `price`, `direction` and `executed_at` all
equal the execution's values, or its `origin` is `split` and it has a `parent_id`. Rows
that do not qualify SHALL be left unchanged and logged. `Trade.is_manually_edited` SHALL
NOT be modified by the migration.

#### Scenario: Marker matching broker data is cleared

- **GIVEN** an execution with `origin='imported'`, `user_modified=true`, whose values equal its broker raw transaction
- **WHEN** the migration runs
- **THEN** the execution SHALL have `user_modified=false`

#### Scenario: Marked split child is cleared

- **GIVEN** an execution with `origin='split'`, `parent_id` set, and `user_modified=true`
- **WHEN** the migration runs
- **THEN** the execution SHALL have `user_modified=false`

#### Scenario: Genuinely edited execution is preserved

- **GIVEN** an execution with `origin='imported'` and `user_modified=true` whose price differs from its broker raw transaction
- **WHEN** the migration runs
- **THEN** the execution SHALL still have `user_modified=true`
- **THEN** the migration SHALL log the skipped row

#### Scenario: Trade protection is untouched

- **GIVEN** a trade `T` with `is_manually_edited=true` whose legs are all cleared by the migration
- **WHEN** the migration runs
- **THEN** `T.is_manually_edited` SHALL still be `true`

#### Scenario: Migration is idempotent

- **WHEN** the migration runs a second time
- **THEN** no row SHALL change

---

### Requirement: A manual closing leg suppresses the sentinel orphan lot for its contract

The FIFO aggregator SHALL NOT create a sentinel orphan lot (`entry_price = 0.001`) for
an unmatched closing execution whose contract `(symbol, conid)` is held by a trade
carrying a **manual stand-in leg** — a `LogicalExecution` with `origin='manual'` and
`source_id IS NULL`, which represents a broker fill that has not been imported yet. Such
an unmatched execution SHALL instead be left unlinked (`trade_id IS NULL`,
`deleted=false`) and reported, exactly as for a closed protected contract.

Suppression SHALL be keyed on the presence of the stand-in leg, not on
`Trade.is_manually_edited`, so that it applies regardless of whether the trade was
closed via the full-close or the partial-close path and regardless of whether the user
documented it.

The system SHALL NOT attempt to determine whether the unlinked execution and the manual
stand-in describe the same broker fill. Resolution is a user action: deleting the manual
leg, or linking it to its broker raw transaction via
`POST /api/v1/executions/{id}/link`. Once either action is taken and a re-aggregation
runs, the situation SHALL resolve without further intervention.

#### Scenario: Broker close for a hand-closed position creates no sentinel trade

- **GIVEN** a trade `T` closed by a manual leg `E2` (`origin='manual'`, `source_id IS NULL`) on contract `C`
- **WHEN** an import brings the broker's closing execution `E3` for `C` that cannot be FIFO-matched
- **THEN** no trade with `entry_price = 0.001` SHALL be created
- **THEN** `E3.trade_id` SHALL remain `NULL`
- **THEN** the account's trade row count SHALL be unchanged

#### Scenario: The unresolved stand-in is surfaced

- **GIVEN** the situation above
- **WHEN** the import completes
- **THEN** `T.has_unlinked_executions` SHALL be `true`
- **THEN** `ImportResult` SHALL count `E3` as an unlinked execution
- **THEN** `ImportResult` SHALL include a warning naming the symbol and execution time

#### Scenario: Deleting the manual leg resolves it

- **GIVEN** a trade `T` with `has_unlinked_executions=true` and an unresolved manual stand-in `E2`
- **WHEN** the user deletes `E2` and a re-aggregation runs
- **THEN** the broker execution SHALL be matched and linked to `T`
- **THEN** `T.has_unlinked_executions` SHALL be `false`
- **THEN** `T.exit_price` SHALL be the broker's price

#### Scenario: Linking the manual leg resolves it

- **GIVEN** a trade `T` with an unresolved manual stand-in `E2` and an unlinked broker execution `E3`
- **WHEN** the user links `E2` to `E3`'s broker raw transaction and a re-aggregation runs
- **THEN** `E2.source_id` SHALL reference that raw transaction
- **THEN** no duplicate leg SHALL remain on `T`
- **THEN** `T.has_unlinked_executions` SHALL be `false`

#### Scenario: Suppression does not depend on trade protection

- **GIVEN** a trade closed by a manual leg whose `is_manually_edited` is `false`
- **WHEN** an unmatchable broker closing execution for its contract is aggregated
- **THEN** no sentinel orphan lot SHALL be created

#### Scenario: Linked manual legs do not suppress

- **GIVEN** a trade whose manual leg has `source_id` set, i.e. it is already linked to its broker transaction
- **WHEN** an unmatchable closing execution for that contract is aggregated
- **THEN** the ordinary sentinel orphan lot SHALL be created as before

---

### Requirement: Import result distinguishes protected closes from unlinked executions

`ImportResult` SHALL report the number of executions that were linked to an open
protected trade via its seed lot, separately from the number of executions left
unlinked. When the number of created trades is zero but executions were linked to
protected trades, the result SHALL still convey that the import changed data.

#### Scenario: Closing a protected position is reported

- **GIVEN** an import that closes exactly one open protected trade and creates no new trades
- **WHEN** the import completes
- **THEN** `ImportResult` SHALL report one protected position closed
- **THEN** `ImportResult` SHALL report zero unlinked executions

#### Scenario: Unlinked executions are still reported

- **GIVEN** an import that brings a closing execution for a closed protected trade
- **WHEN** the import completes
- **THEN** `ImportResult` SHALL report one unlinked execution
- **THEN** `ImportResult` SHALL include a warning naming the affected symbol and execution time

---

### Requirement: Trade chart classification prioritizes open_close markers

When rendering execution legs in the trade chart, explicit `open_close` markers SHALL
be treated as authoritative where present. Direction-based inference remains a fallback
only when `open_close` is absent.

#### Scenario: Open marker is treated as entry

- **GIVEN** an execution leg with `open_close='O'`
- **WHEN** the trade chart classifies it
- **THEN** the leg SHALL be classified as an entry leg regardless of direction fallback

#### Scenario: Close marker is treated as exit

- **GIVEN** an execution leg with `open_close='C'`
- **WHEN** the trade chart classifies it
- **THEN** the leg SHALL be classified as an exit leg regardless of direction fallback

### Requirement: Option trades suppress generic entry/exit price lines in trade chart

The trade chart SHALL NOT render generic horizontal entry/exit price lines for option
trades, including trades identified as option at trade level or by any option execution
leg.

#### Scenario: Option trade renders without generic entry/exit lines

- **GIVEN** a trade that is option-class at trade level or has at least one option leg
- **WHEN** the trade chart renders with trade lines enabled
- **THEN** no generic horizontal entry/exit price line SHALL be drawn
