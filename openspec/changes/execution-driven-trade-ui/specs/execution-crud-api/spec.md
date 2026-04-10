## ADDED Requirements

### Requirement: LogicalExecution Pydantic Schemas
The backend SHALL provide `LogicalExecutionRead` and `LogicalExecutionCreate` Pydantic v2 schemas in `app/schemas/execution.py` for serializing execution data to/from the API.

#### Scenario: Read schema fields
- **WHEN** a `LogicalExecutionRead` is serialized from an ORM instance
- **THEN** it MUST include: `id`, `trade_id`, `symbol`, `conid`, `asset_class`, `direction`, `quantity`, `price`, `commission`, `executed_at`, `pnl`, `pnl_eur`, `currency`, `multiplier`, `status`, `created_at`, `updated_at`

#### Scenario: Create schema validation
- **WHEN** a `LogicalExecutionCreate` payload is submitted
- **THEN** the system MUST require `direction`, `quantity` (> 0), `price` (>= 0), and `executed_at` (timezone-aware UTC)
- **AND** `commission` MUST default to 0 if omitted
- **AND** `pnl` MUST be optional (null for opening legs)

### Requirement: List Executions for a Trade
The system SHALL provide a `GET /api/v1/trades/{trade_id}/executions` endpoint that returns all `LogicalExecution` records assigned to the specified trade, ordered by `executed_at` ascending.

#### Scenario: Listing executions for a closed trade
- **WHEN** a user requests `GET /api/v1/trades/{trade_id}/executions` for a trade with 3 execution legs
- **THEN** the system MUST return all 3 `LogicalExecutionRead` objects sorted chronologically by `executed_at`
- **AND** the response MUST use the standard response envelope `{"data": [...], "meta": {}}`

#### Scenario: Listing executions for a trade with no executions
- **WHEN** a user requests executions for a trade that has no `LogicalExecution` records
- **THEN** the system MUST return an empty array `{"data": [], "meta": {}}`

#### Scenario: Authorization check
- **WHEN** a user requests executions for a trade they do not own
- **THEN** the system MUST return HTTP 404

### Requirement: Create Manual Execution
The system SHALL provide a `POST /api/v1/trades/{trade_id}/executions` endpoint that creates a new `LogicalExecution` with `status: manual` and triggers re-aggregation of the parent trade.

#### Scenario: Adding a sell execution to close part of a position
- **WHEN** a user submits a valid `LogicalExecutionCreate` payload with `direction: SHORT` (for a LONG trade)
- **THEN** the system MUST create a `LogicalExecution` record with `status: manual`
- **AND** the system MUST re-aggregate the parent trade (recalculate quantity, VWAP entry/exit, PnL, commission, opened_at, closed_at)
- **AND** the response MUST include both the created `LogicalExecutionRead` and the updated `TradeRead`

#### Scenario: Adding an entry execution to scale into a position
- **WHEN** a user submits a valid `LogicalExecutionCreate` payload with the same direction as the trade
- **THEN** the system MUST create the execution and re-aggregate the parent trade

#### Scenario: Invalid execution data
- **WHEN** a user submits a payload with `quantity: 0` or missing `executed_at`
- **THEN** the system MUST return HTTP 422 with validation errors

### Requirement: Update Execution
The system SHALL provide a `PATCH /api/v1/executions/{execution_id}` endpoint for updating mutable fields on a `LogicalExecution`, triggering re-aggregation.

#### Scenario: Editing an execution price
- **WHEN** a user submits `{"price": "380.00"}` to `PATCH /api/v1/executions/{id}`
- **THEN** the system MUST update the execution record
- **AND** the system MUST re-aggregate the parent trade
- **AND** the response MUST include the updated `LogicalExecutionRead` and `TradeRead`

#### Scenario: Updating an execution the user does not own
- **WHEN** a user tries to update an execution owned by a different user
- **THEN** the system MUST return HTTP 404

### Requirement: Delete Execution
The system SHALL provide a `DELETE /api/v1/executions/{execution_id}` endpoint that removes a `LogicalExecution` and triggers re-aggregation.

#### Scenario: Deleting an execution from a trade with multiple legs
- **WHEN** a user deletes one of three execution legs
- **THEN** the system MUST remove the `LogicalExecution` record
- **AND** the system MUST re-aggregate the parent trade from the remaining executions
- **AND** the response MUST return HTTP 200 with the updated `TradeRead`

#### Scenario: Deleting the last execution from a trade
- **WHEN** a user deletes the only remaining execution leg of a trade
- **THEN** the system MUST delete the `LogicalExecution` record
- **AND** the system MUST delete the now-empty parent trade
- **AND** the response MUST return HTTP 200 with `{"deleted_trade": true}`

### Requirement: Re-Aggregation After Mutation
The system SHALL re-aggregate the parent trade every time a `LogicalExecution` is created, updated, or deleted.

#### Scenario: Re-aggregation updates trade values
- **WHEN** a new SELL execution is added to a LONG trade
- **THEN** the trade's `exit_price` MUST be recalculated as the VWAP of all SELL executions
- **AND** the trade's `pnl` MUST be recalculated
- **AND** the trade's `closed_at` MUST be set to the latest closing execution's `executed_at` if the position is fully closed

### Requirement: Frontend TypeScript Types
The frontend SHALL define `LogicalExecution`, `LogicalExecutionCreate`, and execution status types in `lib/types.ts`.

#### Scenario: Type availability
- **WHEN** a frontend component imports from `@/lib/types`
- **THEN** `LogicalExecution`, `LogicalExecutionCreate`, and `ExecutionStatus` types MUST be available

### Requirement: Frontend React Query Hooks
The frontend SHALL provide `useTradeExecutions`, `useCreateExecution`, `useUpdateExecution`, and `useDeleteExecution` hooks using React Query.

#### Scenario: Execution list hook
- **WHEN** `useTradeExecutions(tradeId)` is called
- **THEN** it MUST fetch `GET /api/v1/trades/{tradeId}/executions`
- **AND** it MUST invalidate the trade query cache on any execution mutation

#### Scenario: Create execution hook invalidation
- **WHEN** `useCreateExecution` succeeds
- **THEN** it MUST invalidate both the executions list and the trade detail query caches
