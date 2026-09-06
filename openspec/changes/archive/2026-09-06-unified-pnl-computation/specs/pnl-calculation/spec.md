## ADDED Requirements

### Requirement: Dynamic Gross PnL Calculation
The system SHALL calculate the Gross PnL for a closed position dynamically from execution
prices, matched quantity, and contract multiplier, rather than from broker-provided
aggregated PnL fields.

#### Scenario: Long Position Closed
- **WHEN** a closing execution matches an open long lot
- **THEN** the matched Gross PnL SHALL be calculated as `(Exit Price - Entry Price) * Match Quantity * Multiplier`

#### Scenario: Short Position Closed
- **WHEN** a closing execution matches an open short lot
- **THEN** the matched Gross PnL SHALL be calculated as `(Entry Price - Exit Price) * Match Quantity * Multiplier`

### Requirement: Dynamic Net PnL Calculation
The system SHALL calculate the Net PnL of a position by subtracting the matched commissions
from the dynamically calculated Gross PnL.

#### Scenario: Net PnL Deducts Commissions
- **WHEN** a closing execution matches an open lot
- **THEN** the matched Net PnL SHALL be calculated as `Gross PnL - (Matched Lot Commission + Matched Execution Commission)`

#### Scenario: Commission Is Never Deducted Twice
- **WHEN** a `Trade` PnL is derived from its executions by any code path
- **THEN** the stored `pnl` SHALL be a gross value
- **AND** the stored `net_pnl` SHALL be that gross value minus the trade's total commission exactly once

### Requirement: Broker-Reported PnL Is Never Used As A Value
No code path that derives an aggregated `Trade`'s `pnl` or `net_pnl` SHALL read the numeric
value of `LogicalExecution.pnl`. Broker-reported PnL is retained as provenance metadata only.

#### Scenario: Batched Execution Match
- **WHEN** an execution matches multiple open lots with varying entry prices
- **THEN** the system SHALL NOT split or distribute the broker's reported PnL
- **AND** the system SHALL calculate Gross and Net PnL per match from execution prices and multipliers

#### Scenario: Broker Reports PnL Net Of Commission
- **WHEN** a broker's reported per-leg PnL is net of commission, as Interactive Brokers' `fifoPnlRealized` is
- **THEN** the system SHALL ignore that value entirely when computing `Trade.pnl`
- **AND** the resulting `Trade.pnl` SHALL be gross, independent of what the broker reported

#### Scenario: Broker Reports No PnL At All
- **WHEN** a broker does not report realised PnL, as Charles Schwab does not
- **THEN** the absence of a value SHALL NOT cause the trade's PnL to become zero, null, or otherwise degraded
- **AND** the trade's PnL SHALL be derived from execution prices exactly as for any other broker

#### Scenario: Split Execution Carrying Unprorated Broker PnL
- **WHEN** an execution that carries a broker-reported PnL is split into children
- **AND** a child retains the parent's full unprorated PnL value
- **THEN** the aggregated `Trade` PnL SHALL be unaffected by that retained value

### Requirement: Broker PnL Presence As A Closing-Leg Signal Is Aggregator-Internal
Components other than the FIFO aggregator SHALL NOT infer opening/closing semantics, or the
availability of a broker-reported value, from the presence or absence of
`LogicalExecution.pnl`. The FIFO aggregator MAY use that presence to distinguish a closing
leg from an opening leg.

#### Scenario: Parser Emits A Presence-Only Sentinel
- **WHEN** a broker parser sets `pnl` to a fixed sentinel such as `Decimal("0")` purely to mark a closing leg
- **THEN** the FIFO aggregator SHALL treat it as a closing-leg marker
- **AND** every other consumer SHALL treat it as carrying no numeric meaning

#### Scenario: Re-Aggregation Encounters A Sentinel
- **WHEN** a trade is re-aggregated and one of its executions carries a sentinel `pnl`
- **THEN** the sentinel SHALL NOT be interpreted as a broker-reported PnL of zero
- **AND** the trade's PnL SHALL be derived from execution prices

### Requirement: Positions Without A Derivable Entry Price
The system SHALL handle a position that has no entry-side execution explicitly, rather than
by falling back to broker-reported PnL. Such a position has no price-derivable Gross PnL.

#### Scenario: Orphaned Closing Leg
- **WHEN** a trade's opening execution lies outside the imported period and the entry price is a placeholder
- **THEN** the system SHALL NOT compute a price-derived PnL from the placeholder
- **AND** the system SHALL mark the PnL as not derivable rather than emitting a misleading number
