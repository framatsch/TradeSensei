# corporate-action-lifecycle Specification

## Purpose
TBD - created by archiving change corporate-action-lifecycle. Update Purpose after archive.
## Requirements
### Requirement: Canonical Split Adjustment Semantics

The system SHALL apply corporate action ratios through exactly one shared implementation, using the holding-period rule defined below. Every code path that adjusts execution values — FIFO aggregation, trade re-aggregation, and read-time chart alignment — SHALL call that implementation rather than reimplementing the arithmetic.

The holding-period rule: a corporate action adjusts a position's entry values **only if the position was open across the action's effective date**, that is `opened_at < action.date AND (closed_at IS NULL OR closed_at >= action.date)`. A position that was opened and fully closed before the effective date was never subject to the action and SHALL remain unadjusted.

The effective date boundary: an execution occurring **on** the effective date counts as post-split and is never adjusted. The comparison SHALL use the calendar date of the execution at the exchange where it took place, not the UTC calendar date. An after-hours execution on the evening before an effective date is pre-split even though its UTC timestamp already falls on the effective date.

Adjustment arithmetic is `quantity *= ratio` and `price /= ratio`. Commission is a currency amount and SHALL NEVER be adjusted by a split ratio in any code path.

#### Scenario: Position closed before the effective date is not adjusted

- **WHEN** a trade was opened on 2023-05-22 and fully closed on 2023-05-24, and a 1:20 reverse split for the same symbol has effective date 2024-03-13
- **THEN** the trade's persisted `quantity` and `entry_price` remain at their raw values and no ratio is applied

#### Scenario: Position open across the effective date is adjusted

- **WHEN** a trade was opened on 2024-01-10, a 1:20 reverse split has effective date 2024-03-13, and the closing execution occurs on 2024-06-01
- **THEN** the entry quantity is multiplied by 0.05 and the entry price divided by 0.05, while the closing execution — already reported post-split by the broker — is left unadjusted

#### Scenario: Execution on the effective date counts as post-split

- **WHEN** an execution has an exchange-local execution date equal to the corporate action's effective date
- **THEN** no ratio is applied to that execution

#### Scenario: After-hours execution before the effective date is pre-split

- **WHEN** an execution occurs during extended hours on the evening before the effective date, so that its UTC timestamp falls on the effective date while its exchange-local date is the day before
- **THEN** the execution is treated as pre-split and the ratio is applied to it

#### Scenario: Commission is never scaled

- **WHEN** any corporate action is applied to a position in any code path
- **THEN** the position's `commission` and `source_commission` are unchanged, and the resulting `net_pnl` reflects the commission actually paid

#### Scenario: Both engines produce identical results

- **WHEN** the same set of executions and corporate actions is processed once through FIFO aggregation during import and once through trade re-aggregation
- **THEN** the resulting `quantity`, `entry_price`, `exit_price`, `commission`, and `net_pnl` are identical

### Requirement: Trade Projection Is Rebuilt From Logical Executions Only

The system SHALL rebuild the trade projection exclusively from immutable `LogicalExecution` records. Pre-loading already-persisted, already-adjusted open lots as FIFO seed input SHALL NOT occur, because seeded lots carry adjusted quantities and would have historical ratios applied a second time.

All broker parsers SHALL supply raw transaction records so that every import path uses this rebuild. The seed-lot aggregation fallback SHALL be removed rather than kept as an alternative path, so that no code path exists in which a persisted, already-adjusted lot can be fed back into ratio application.

#### Scenario: Import rebuilds from the logical layer

- **WHEN** an incremental import runs for an account that already holds open positions in the database
- **THEN** FIFO aggregation is seeded from the account's `LogicalExecution` history rather than from persisted open `Trade` rows, and no corporate action is applied more than once to any lot

#### Scenario: A previously split-adjusted open lot is not adjusted twice

- **WHEN** an open position was adjusted by a 1:20 reverse split during an earlier import and a later import adds a closing execution
- **THEN** the position's quantity reflects exactly one application of the 0.05 ratio

### Requirement: Persisted Trade Values Use the Historical Basis

The system SHALL persist to the `Trade` model the values that reflect what actually happened in the account — quantity and price on the historical basis defined by the holding-period rule. These are the values used for realised PnL, performance metrics, and all database-side aggregation.

#### Scenario: Broker import persists historical-basis values for open lots

- **WHEN** an import produces an open lot that has crossed a corporate action's effective date
- **THEN** the adjusted `quantity` and `entry_price` are written to the `Trade` row even though the position is still unmatched

#### Scenario: Realised PnL is unaffected by a later split

- **WHEN** a corporate action is created with an effective date after a trade was already closed
- **THEN** that trade's `pnl` and `net_pnl` are unchanged

### Requirement: Trade Values Are Exposed on Both Bases

The system SHALL expose, alongside the historical-basis values, the chart-adjusted counterparts of a trade's quantity and prices. The chart-adjusted basis applies every corporate action whose effective date is later than the execution, mirroring how market data providers retroactively restate historical bars.

Both bases SHALL be internally consistent: the execution legs of a trade sum to that trade's header values **on the same basis**. A client SHALL NOT need to mix values from different bases to render a trade.

#### Scenario: Trade header and its legs agree on each basis

- **WHEN** a client fetches a trade and its execution legs for a symbol affected by a 1:20 reverse split
- **THEN** the sum of the legs' historical-basis quantities equals the trade's historical-basis quantity, and the sum of the legs' chart-adjusted quantities equals the trade's chart-adjusted quantity

#### Scenario: Chart markers align with adjusted price bars

- **WHEN** a trade closed before a reverse split is rendered on a price chart whose bars are provider-adjusted
- **THEN** the execution markers are positioned using the chart-adjusted price, and the historical raw price remains available for display alongside it

### Requirement: Corporate Action Impact Is Visible on Affected Trades

The system SHALL mark every trade whose symbol is affected by at least one corporate action, and SHALL identify which actions apply. Clients use this marker to disclose that the displayed values and the price chart rest on different bases.

#### Scenario: Affected trade carries a marker

- **WHEN** a trade's symbol has a corporate action whose effective date is later than the trade's opening execution
- **THEN** the trade read model reports that it is affected and identifies the applicable corporate actions

#### Scenario: Marker clears when the action is removed

- **WHEN** the last corporate action for a symbol is deleted
- **THEN** the affected trades no longer report a corporate action impact

### Requirement: Market Data Cache Invalidation on Corporate Action Change

The system SHALL discard cached `ohlc_prices` bars for a symbol whenever a corporate action for that symbol is created, updated, or deleted. Cached bars retrieved before an action took effect carry the pre-split basis and would otherwise never be replaced, producing a discontinuity in the chart at the effective date.

Invalidation SHALL delete the affected symbol's cached bars so the next chart request refetches them on the provider's current adjustment basis.

#### Scenario: Creating a corporate action invalidates cached bars

- **WHEN** a user creates a corporate action for a symbol that has cached price bars
- **THEN** the cached bars for that symbol are deleted and the next chart request refetches them from the upstream provider

#### Scenario: Deleting a corporate action invalidates cached bars

- **WHEN** a user deletes a corporate action
- **THEN** the cached bars for the affected symbol are deleted

### Requirement: Corporate Actions Are Unique per Symbol and Date

The system SHALL permit at most one corporate action per user, symbol, and effective date, enforced by a database constraint. The uniqueness key SHALL NOT include the ratio: a mistyped ratio must fail as a conflict rather than create a second record whose ratio is then applied on top of the first.

A manual create that collides with an existing action SHALL be rejected with a conflict response identifying the existing record, so the user edits it instead of adding a duplicate.

An import that encounters an existing action for the same user, symbol, and effective date SHALL update that record rather than insert a new one. The broker file is the authoritative source; the user can review and adjust the result afterwards.

#### Scenario: Manual creation of a duplicate is rejected

- **WHEN** a user creates a corporate action for a symbol and effective date that already has one
- **THEN** the request is rejected with a conflict response identifying the existing action, and no second record is created

#### Scenario: Duplicate ratios cannot compound

- **WHEN** the same 1:15 reverse split is submitted twice with slightly different ratio values
- **THEN** only one record exists and the ratio is applied exactly once to any affected position

#### Scenario: Import updates an existing action

- **WHEN** a broker import reports a corporate action for a symbol and effective date that already exists
- **THEN** the existing record is updated with the values from the file rather than duplicated

### Requirement: Recalculation Is Atomic and Idempotent

The system SHALL treat a corporate action change and its consequences — trade recalculation and price-cache invalidation — as one atomic unit. Either all of it is applied or none of it. A failure SHALL NOT leave the action persisted alongside partially recalculated trades.

Recalculation SHALL be idempotent: recomputing a trade derives its values from the immutable `LogicalExecution` records and the current set of corporate actions, never by mutating previously computed values. Running it any number of times yields the same result, so a retry after a failure is always safe.

#### Scenario: Failure during recalculation rolls back the corporate action

- **WHEN** trade recalculation fails partway through after a corporate action was created
- **THEN** the corporate action is not persisted, no trade retains a partially applied value, and the user can retry

#### Scenario: Repeated recalculation is stable

- **WHEN** recalculation runs repeatedly for the same symbol with an unchanged set of corporate actions
- **THEN** every trade's `quantity`, `entry_price`, `exit_price`, `commission`, and `net_pnl` are identical after each run

### Requirement: Automatic Trade Recalculation on Corporate Action Change

The system SHALL recalculate all affected trades when a corporate action is created, updated, or deleted, so that users are never shown stale values and never have to run a broker import to repair them.

Recalculation SHALL apply the holding-period rule, and SHALL therefore leave trades untouched that were fully closed before the effective date.

#### Scenario: User creates a split manually

- **WHEN** a user creates a corporate action in the UI
- **THEN** all trades of that symbol that were open across the effective date are recalculated, and trades closed before that date are left unchanged

#### Scenario: User corrects the effective date of an existing action

- **WHEN** a user changes a corporate action's effective date
- **THEN** trades are recalculated against the new date, and trades that fall outside the new holding-period window are restored to their unadjusted values

#### Scenario: User deletes a split

- **WHEN** a user deletes a corporate action
- **THEN** all trades previously adjusted by it are recalculated without that ratio

