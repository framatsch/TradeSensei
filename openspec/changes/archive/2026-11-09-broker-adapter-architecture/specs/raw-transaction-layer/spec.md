## ADDED Requirements

### Requirement: Broker-neutral execution grouping and position-effect fields
Each `BrokerRawTransaction` SHALL carry three broker-neutral fields populated by the broker adapter at parse time: `order_id` (nullable string; the broker's order-level grouping key used for combo detection), `net_cash` (nullable decimal; signed cash effect of the execution as reported or derived by the adapter), and `is_mixed_execution` (boolean, default `false`; true when one execution both closes and opens a position, i.e. a position flip). The import pipeline, combo builder and logical-execution creation SHALL read these fields and SHALL NOT read broker-specific keys from `raw_data` for these purposes.

#### Scenario: IBKR execution populates the neutral fields
- **WHEN** the IBKR adapter parses a `<Trade>` element with `brokerageOrderID="123"`, `netCash="-512.30"` and `openCloseIndicator="C;O"`
- **THEN** the resulting raw transaction SHALL have `order_id="123"`, `net_cash=-512.30` and `is_mixed_execution=true`

#### Scenario: Broker without order grouping
- **WHEN** an adapter parses an execution for which the broker supplies no order-level grouping key
- **THEN** `order_id` and `net_cash` SHALL be `NULL` and the execution SHALL NOT participate in combo grouping, exactly as before this change

#### Scenario: Logical execution inherits the mixed flag from the column
- **WHEN** a `LogicalExecution` is materialised from a raw transaction with `is_mixed_execution=true`
- **THEN** the logical execution's `is_mixed_execution` SHALL be `true`, regardless of the contents of `raw_data`

#### Scenario: Existing rows are backfilled
- **WHEN** the migration introducing the fields runs against existing raw transactions
- **THEN** `order_id` SHALL equal `raw_data->>'brokerageOrderID'`, `net_cash` SHALL equal `raw_data->>'netCash'` cast to decimal, and `is_mixed_execution` SHALL be true exactly when `upper(raw_data->>'openCloseIndicator')` contains `C;O` or `O;C`
- **THEN** a subsequent zero-change re-import SHALL produce the same trades, executions and combo groupings as before the migration
