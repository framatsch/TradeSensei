## ADDED Requirements

### Requirement: Split-aware FIFO aggregation
The `aggregate_executions_fifo` function SHALL accept an optional list of `CorporateAction` objects. When provided, it SHALL apply split adjustments to open lots at the correct chronological point before matching closing executions.

#### Scenario: Simple 2:1 forward split between buy and sell
- **WHEN** a user bought 100 shares at $10.00, then a 2:1 split occurred, then the user sold 200 shares at $6.00 (with PnL)
- **THEN** the aggregator SHALL adjust the open lot to 200 shares at $5.00 before matching the sell
- **THEN** the resulting closed trade SHALL show `quantity=200`, `entry_price=5.00`, `exit_price=6.00`

#### Scenario: 1:20 Reverse split with conid change (OTLK case)
- **WHEN** a user bought 100 shares of OTLK with `conid="357194941"` at $1.00, then a 1:20 reverse split occurred mapping `old_conid="357194941"` to `new_conid="690184975"`, then the user sold 5 shares with `conid="690184975"` at $15.00
- **THEN** the aggregator SHALL apply ratio `0.05` to the open lot: `quantity = 100 * 0.05 = 5`, `entry_price = 1.00 / 0.05 = 20.00`
- **THEN** the resulting closed trade SHALL show `quantity=5`, `entry_price=20.00`, `exit_price=15.00`, `broker_conid="690184975"`

#### Scenario: Fractional shares after reverse split
- **WHEN** a user held 15 shares and a 1:20 reverse split occurred
- **THEN** the aggregator SHALL produce an open lot of `quantity=0.75` (Decimal, not rounded)

#### Scenario: No corporate actions provided
- **WHEN** `aggregate_executions_fifo` is called without corporate actions
- **THEN** the behaviour SHALL be identical to the current implementation (backward compatible)

#### Scenario: Corporate action for a symbol not in the open lots queue
- **WHEN** a split event exists for symbol "XYZ" but no open lots for "XYZ" are in the queue at that time
- **THEN** the aggregator SHALL ignore the event without error

---

### Requirement: Import service loads corporate actions before aggregation
The `ImportService` SHALL query all `CorporateAction` records for the importing user and pass them to the parser/aggregator before any execution matching takes place.

#### Scenario: Import with a matching corporate action in DB
- **WHEN** a user has a `CorporateAction` for OTLK in their DB and imports an IBKR XML containing OTLK buy and sell executions spanning that split
- **THEN** the import SHALL produce a correctly closed trade for OTLK with mathematically correct entry price and quantity

#### Scenario: Import with no corporate actions
- **WHEN** a user has no corporate actions and imports a file
- **THEN** the import SHALL behave identically to the previous implementation
