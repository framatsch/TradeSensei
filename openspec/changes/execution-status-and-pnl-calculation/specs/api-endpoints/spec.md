## ADDED Requirements

### Requirement: DELETE execution endpoint performs soft-delete for transaction-linked executions

The system SHALL modify the DELETE /api/v1/executions/{id} endpoint to perform soft-delete (set status to IGNORED) for executions with transaction links, and hard-delete for MANUAL/MERGED executions.

#### Scenario: DELETE IMPORTED execution returns 200 with soft-delete
- **WHEN** DELETE /api/v1/executions/{id}
- **AND** execution.status is IMPORTED
- **THEN** response status is 200 OK (not 204 No Content)
- **AND** response body contains updated execution with status=IGNORED
- **AND** execution.previous_status is set to IMPORTED
- **AND** execution remains in database (not physically deleted)

```json
DELETE /api/v1/executions/123

Response 200 OK:
{
  "data": {
    "id": 123,
    "status": "ignored",
    "previous_status": "imported",
    "quantity": 100.0,
    "price": 155.25,
    // ... other fields
  }
}
```

#### Scenario: DELETE EDITED execution performs soft-delete
- **WHEN** DELETE /api/v1/executions/{id}
- **AND** execution.status is EDITED
- **THEN** response status is 200 OK
- **AND** execution.status set to IGNORED
- **AND** execution.previous_status set to EDITED

#### Scenario: DELETE SPLIT execution performs soft-delete
- **WHEN** DELETE /api/v1/executions/{id}
- **AND** execution.status is SPLIT
- **THEN** response status is 200 OK
- **AND** execution.status set to IGNORED
- **AND** execution.previous_status set to SPLIT

#### Scenario: DELETE MANUAL execution returns 204 with hard-delete
- **WHEN** DELETE /api/v1/executions/{id}
- **AND** execution.status is MANUAL
- **THEN** response status is 204 No Content
- **AND** execution is physically deleted from database
- **AND** no response body

#### Scenario: DELETE MERGED execution returns 204 with hard-delete
- **WHEN** DELETE /api/v1/executions/{id}
- **AND** execution.status is MERGED
- **THEN** response status is 204 No Content
- **AND** execution is physically deleted from database

#### Scenario: DELETE IGNORED execution returns 403 Forbidden
- **WHEN** DELETE /api/v1/executions/{id}
- **AND** execution.status is IGNORED
- **THEN** response status is 403 Forbidden
- **AND** error body explains cannot delete already-ignored execution

```json
Response 403 Forbidden:
{
  "error": {
    "code": "execution_already_ignored",
    "message": "Cannot delete already-ignored execution. Restore first or delete parent trade.",
    "details": {
      "execution_id": 123,
      "status": "ignored"
    }
  }
}
```

#### Scenario: DELETE execution triggers trade re-aggregation
- **WHEN** DELETE /api/v1/executions/{id} succeeds (soft or hard)
- **THEN** system calls _re_aggregate_trade() for parent trade
- **AND** trade P&L is recalculated
- **AND** trade.has_conflict is rechecked
- **AND** trade.is_empty is computed (if all executions now IGNORED)

### Requirement: POST restore execution endpoint restores IGNORED executions

The system SHALL provide a new endpoint POST /api/v1/executions/{id}/restore that restores soft-deleted executions to their previous status.

#### Scenario: Restore IGNORED execution to IMPORTED
- **WHEN** POST /api/v1/executions/123/restore
- **AND** execution.status is IGNORED
- **AND** execution.previous_status is IMPORTED
- **THEN** response status is 200 OK
- **AND** execution.status set to IMPORTED
- **AND** execution.previous_status set to NULL

```json
POST /api/v1/executions/123/restore

Response 200 OK:
{
  "data": {
    "id": 123,
    "status": "imported",
    "previous_status": null,
    "quantity": 100.0,
    // ... other fields
  }
}
```

#### Scenario: Restore IGNORED execution to EDITED
- **WHEN** POST /api/v1/executions/{id}/restore
- **AND** execution.previous_status is EDITED
- **THEN** execution.status set to EDITED
- **AND** execution.previous_status set to NULL

#### Scenario: Restore IGNORED with NULL previous_status defaults to IMPORTED
- **WHEN** POST /api/v1/executions/{id}/restore
- **AND** execution.previous_status is NULL (data corruption edge case)
- **THEN** execution.status set to IMPORTED (safe fallback)
- **AND** execution.previous_status remains NULL

#### Scenario: Restore non-IGNORED execution returns 400 Bad Request
- **WHEN** POST /api/v1/executions/{id}/restore
- **AND** execution.status is not IGNORED (e.g., IMPORTED, MANUAL)
- **THEN** response status is 400 Bad Request
- **AND** error message explains execution is not ignored

```json
Response 400 Bad Request:
{
  "error": {
    "code": "execution_not_ignored",
    "message": "Execution is not ignored and cannot be restored.",
    "details": {
      "execution_id": 123,
      "current_status": "imported"
    }
  }
}
```

#### Scenario: Restore triggers trade re-aggregation
- **WHEN** POST /api/v1/executions/{id}/restore succeeds
- **THEN** system calls _re_aggregate_trade() for parent trade
- **AND** trade P&L is recalculated
- **AND** trade.has_conflict is rechecked
- **AND** trade.is_empty is recomputed (now false if was EMPTY)

#### Scenario: Restore execution not found returns 404
- **WHEN** POST /api/v1/executions/999/restore
- **AND** execution with id=999 does not exist
- **THEN** response status is 404 Not Found

### Requirement: DELETE trade endpoint implements two-stage deletion

The system SHALL modify DELETE /api/v1/trades/{id} endpoint to implement two-stage deletion: soft-delete all executions (Stage 1) or permanently delete with tombstones (Stage 2).

#### Scenario: Delete active trade (Stage 1 - archive)
- **WHEN** DELETE /api/v1/trades/456
- **AND** trade has executions with status != IGNORED
- **THEN** response status is 200 OK
- **AND** all active executions soft-deleted (status → IGNORED, previous_status saved)
- **AND** trade.is_empty becomes true (computed)
- **AND** trade remains in database
- **AND** response indicates archived status

```json
DELETE /api/v1/trades/456

Response 200 OK:
{
  "data": {
    "id": 456,
    "symbol": "AAPL",
    "is_empty": true,
    "executions": [
      {"id": 1, "status": "ignored", "previous_status": "imported", ...},
      {"id": 2, "status": "ignored", "previous_status": "edited", ...}
    ]
  },
  "message": "Trade archived. All executions moved to archive."
}
```

#### Scenario: Delete EMPTY trade (Stage 2 - permanent)
- **WHEN** DELETE /api/v1/trades/456
- **AND** trade.is_empty is true (all executions IGNORED)
- **THEN** response status is 204 No Content
- **AND** DeletedExecutionTombstones created for each IGNORED execution with transaction_id
- **AND** trade hard-deleted from database (CASCADE)
- **AND** all IGNORED executions hard-deleted (CASCADE)
- **AND** all TransactionExecutionMappings hard-deleted (CASCADE)
- **AND** journaling data (TradeNotes, TradeTags) orphaned (trade_id → NULL)

```json
DELETE /api/v1/trades/456 (EMPTY trade)

Response 204 No Content
(no body)
```

#### Scenario: Delete trade without executions
- **WHEN** DELETE /api/v1/trades/{id}
- **AND** trade has no executions (edge case, data corruption)
- **THEN** response status is 204 No Content
- **AND** trade hard-deleted immediately (no tombstones needed)

#### Scenario: Delete trade not found returns 404
- **WHEN** DELETE /api/v1/trades/999
- **AND** trade with id=999 does not exist
- **THEN** response status is 404 Not Found

### Requirement: GET trades endpoint supports filtering EMPTY trades

The system SHALL extend GET /api/v1/trades endpoint to support filtering based on is_empty status.

#### Scenario: Default behavior excludes EMPTY trades
- **WHEN** GET /api/v1/trades (no query params)
- **THEN** only trades with is_empty=false are returned
- **AND** EMPTY trades are filtered out by default

```json
GET /api/v1/trades

Response 200 OK:
{
  "data": [
    {"id": 1, "symbol": "AAPL", "is_empty": false, ...},
    {"id": 2, "symbol": "TSLA", "is_empty": false, ...}
    // EMPTY trade id=3 not included
  ],
  "pagination": {...}
}
```

#### Scenario: Include EMPTY trades with query param
- **WHEN** GET /api/v1/trades?include_empty=true
- **THEN** both active and EMPTY trades are returned
- **AND** is_empty field is true for EMPTY trades

```json
GET /api/v1/trades?include_empty=true

Response 200 OK:
{
  "data": [
    {"id": 1, "symbol": "AAPL", "is_empty": false, ...},
    {"id": 2, "symbol": "TSLA", "is_empty": false, ...},
    {"id": 3, "symbol": "MSFT", "is_empty": true, ...}
  ]
}
```

#### Scenario: Show only EMPTY trades (archive view)
- **WHEN** GET /api/v1/trades?include_empty=true&only_empty=true
- **THEN** only trades with is_empty=true are returned
- **AND** active trades are filtered out

```json
GET /api/v1/trades?include_empty=true&only_empty=true

Response 200 OK:
{
  "data": [
    {"id": 3, "symbol": "MSFT", "is_empty": true, ...}
  ]
}
```

#### Scenario: Conflicting params defaults to only_empty
- **WHEN** GET /api/v1/trades?include_empty=false&only_empty=true
- **THEN** only_empty takes precedence
- **AND** only EMPTY trades returned

### Requirement: GET trade detail includes is_empty field

The system SHALL include is_empty computed property in Trade response schemas.

#### Scenario: Active trade has is_empty=false
- **WHEN** GET /api/v1/trades/456
- **AND** trade has 1+ executions with status != IGNORED
- **THEN** response includes is_empty: false

```json
GET /api/v1/trades/456

Response 200 OK:
{
  "data": {
    "id": 456,
    "symbol": "AAPL",
    "is_empty": false,
    "executions": [
      {"id": 1, "status": "imported", ...},
      {"id": 2, "status": "ignored", ...}  // Has active + ignored
    ]
  }
}
```

#### Scenario: EMPTY trade has is_empty=true
- **WHEN** GET /api/v1/trades/456
- **AND** all executions have status IGNORED
- **THEN** response includes is_empty: true

```json
Response 200 OK:
{
  "data": {
    "id": 456,
    "symbol": "AAPL",
    "is_empty": true,
    "executions": [
      {"id": 1, "status": "ignored", ...},
      {"id": 2, "status": "ignored", ...}
    ]
  }
}
```

### Requirement: GET executions includes IGNORED by default (frontend filters)

The system SHALL include IGNORED executions in GET /api/v1/trades/{id}/executions response, allowing frontend to implement show/hide toggle.

#### Scenario: Executions endpoint returns IGNORED executions
- **WHEN** GET /api/v1/trades/456/executions
- **THEN** response includes all executions (including IGNORED)
- **AND** frontend is responsible for filtering display

```json
GET /api/v1/trades/456/executions

Response 200 OK:
{
  "data": [
    {"id": 1, "status": "imported", "quantity": 100.0, ...},
    {"id": 2, "status": "ignored", "previous_status": "edited", "quantity": 50.0, ...}
  ]
}
```

**Rationale:** Frontend needs access to IGNORED executions for show/hide toggle. Backend doesn't filter; frontend handles visibility.

#### Scenario: No separate endpoint for only IGNORED executions
- **WHEN** client needs only IGNORED executions (e.g., archive view)
- **THEN** client filters response where status="ignored"
- **AND** no backend API endpoint needed (client-side filter sufficient)

### Requirement: PATCH execution transitions IMPORTED to EDITED automatically

The system SHALL automatically set status to EDITED when updating an IMPORTED execution (already implemented, documented here for completeness).

#### Scenario: Update IMPORTED execution price sets EDITED status
- **WHEN** PATCH /api/v1/executions/123
- **AND** execution.status is IMPORTED
- **AND** request body contains {"price": 156.00}
- **THEN** response status is 200 OK
- **AND** execution.status is set to EDITED (auto-transition)
- **AND** execution.price is updated to 156.00

```json
PATCH /api/v1/executions/123
{
  "price": 156.00
}

Response 200 OK:
{
  "data": {
    "id": 123,
    "status": "edited",  // Auto-transitioned from imported
    "price": 156.00,
    // ... other fields
  }
}
```

#### Scenario: Update MANUAL execution does not change status
- **WHEN** PATCH /api/v1/executions/123
- **AND** execution.status is MANUAL
- **AND** request body contains {"price": 156.00}
- **THEN** execution.status remains MANUAL (no auto-transition)

#### Scenario: Update IGNORED execution returns 400 Bad Request
- **WHEN** PATCH /api/v1/executions/123
- **AND** execution.status is IGNORED
- **THEN** response status is 400 Bad Request
- **AND** error message: "Cannot update ignored execution. Restore first."

```json
Response 400 Bad Request:
{
  "error": {
    "code": "execution_ignored",
    "message": "Cannot update ignored execution. Restore first.",
    "details": {"execution_id": 123}
  }
}
```

### Requirement: Error responses follow consistent schema

The system SHALL use consistent error response schema for all execution and trade endpoint errors.

#### Scenario: Error response structure
```json
{
  "error": {
    "code": "error_code_snake_case",
    "message": "Human-readable error message",
    "details": {
      // Optional: Additional context
    }
  }
}
```

#### Scenario: Error codes for execution operations
```
execution_not_found          - 404: Execution ID does not exist
execution_already_ignored    - 403: Cannot delete IGNORED execution
execution_not_ignored        - 400: Cannot restore non-IGNORED execution
execution_ignored            - 400: Cannot update IGNORED execution
trade_not_found              - 404: Trade ID does not exist
validation_error             - 422: Input validation failed (e.g., excess decimals)
```

## Definition of Done

### Backend API Implementation

**File:** `backend/app/api/v1/executions.py`

- Endpoint: `DELETE /api/v1/executions/{id}`
  - Modify to return 200 OK with body for soft-delete
  - Return 204 No Content for hard-delete
  - Return 403 for IGNORED execution
  - Call ExecutionService.delete_execution()
- Endpoint: `POST /api/v1/executions/{id}/restore` (NEW)
  - Return 200 OK with restored execution
  - Return 400 if not IGNORED
  - Return 404 if not found
  - Call ExecutionService.restore_execution()
- Endpoint: `PATCH /api/v1/executions/{id}`
  - Add validation: reject updates to IGNORED executions (400)
  - Existing auto-transition logic unchanged

**File:** `backend/app/api/v1/trades.py`

- Endpoint: `DELETE /api/v1/trades/{id}`
  - Implement two-stage logic (Stage 1: 200 OK, Stage 2: 204 No Content)
  - Call TradeService.delete_trade()
- Endpoint: `GET /api/v1/trades`
  - Add query params: include_empty (bool), only_empty (bool)
  - Filter based on is_empty computed property
- Endpoint: `GET /api/v1/trades/{id}`
  - Include is_empty in response schema
- Endpoint: `GET /api/v1/trades/{id}/executions`
  - Return all executions including IGNORED (no filtering)

### Service Layer

**File:** `backend/app/services/execution.py`

- Method: `delete_execution(execution_id: int) -> Execution | None`
  - Implement soft-delete logic (IMPORTED/EDITED/SPLIT → IGNORED)
  - Implement hard-delete logic (MANUAL/MERGED → physical delete)
  - Raise 403 for IGNORED
  - Call _re_aggregate_trade() after delete
  - Return updated execution for soft-delete, None for hard-delete
- Method: `restore_execution(execution_id: int) -> Execution` (NEW)
  - Set status = previous_status
  - Clear previous_status (set to NULL)
  - Handle NULL previous_status (default to IMPORTED)
  - Raise 400 if not IGNORED
  - Call _re_aggregate_trade() after restore
  - Return restored execution

**File:** `backend/app/services/trade.py`

- Method: `delete_trade(trade_id: int) -> Trade | None`
  - Stage 1: Soft-delete all active executions if not is_empty
  - Stage 2: Create tombstones, hard-delete if is_empty
  - Return updated trade for Stage 1, None for Stage 2
- Property: `is_empty` in Trade model
  - Computed property: all(e.status == IGNORED for e in executions)
- Method: `get_trades(include_empty: bool, only_empty: bool) -> List[Trade]`
  - Apply filters based on is_empty

**File:** `backend/app/services/tombstone.py` (NEW)

- Method: `create_tombstone(transaction_id, account_id, user_id, ...)`
  - Insert into deleted_execution_tombstones
  - Handle unique constraint (idempotent)
- Method: `tombstone_exists(transaction_id, account_id) -> bool`
  - Query deleted_execution_tombstones

### Schemas (Pydantic)

**File:** `backend/app/schemas/execution.py`

- Update ExecutionStatus enum: add EDITED, IGNORED
- Update ExecutionResponse: add previous_status (Optional[ExecutionStatus])
- Add ExecutionRestoreResponse schema (same as ExecutionResponse)

**File:** `backend/app/schemas/trade.py`

- Update TradeResponse: add is_empty (bool)
- Update TradeListParams: add include_empty (bool), only_empty (bool)

**File:** `backend/app/schemas/error.py`

- Add error codes: execution_already_ignored, execution_not_ignored, execution_ignored

### OpenAPI Documentation

**File:** Route docstrings in `backend/app/api/v1/executions.py`

```python
@router.delete("/{id}", response_model=ExecutionResponse, status_code=200)
async def delete_execution(id: int):
    """
    Delete an execution (soft-delete for IMPORTED/EDITED/SPLIT, hard-delete for MANUAL/MERGED).
    
    **Soft-Delete (status → IGNORED):**
    - IMPORTED, EDITED, SPLIT executions
    - Returns 200 OK with updated execution
    - Preserves transaction mapping to prevent re-import duplicates
    
    **Hard-Delete (physical removal):**
    - MANUAL, MERGED executions
    - Returns 204 No Content
    
    **Forbidden:**
    - IGNORED executions (already soft-deleted)
    - Returns 403 Forbidden
    """

@router.post("/{id}/restore", response_model=ExecutionResponse, status_code=200)
async def restore_execution(id: int):
    """
    Restore a soft-deleted (IGNORED) execution to its previous status.
    
    - Returns execution with status restored to previous_status (IMPORTED, EDITED, or SPLIT)
    - Returns 400 Bad Request if execution is not IGNORED
    - Triggers trade re-aggregation
    """
```

### Integration Tests

**File:** `backend/tests/integration/test_execution_api.py`

- Test: `test_delete_imported_returns_200_soft_delete()`
  - DELETE /executions/{id} on IMPORTED
  - Assert 200 OK, status=ignored, previous_status=imported
- Test: `test_delete_manual_returns_204_hard_delete()`
  - DELETE /executions/{id} on MANUAL
  - Assert 204 No Content, execution physically deleted
- Test: `test_delete_ignored_returns_403()`
  - DELETE /executions/{id} on IGNORED
  - Assert 403 Forbidden
- Test: `test_restore_ignored_returns_200()`
  - POST /executions/{id}/restore on IGNORED
  - Assert 200 OK, status=previous_status, previous_status=null
- Test: `test_restore_non_ignored_returns_400()`
  - POST /executions/{id}/restore on IMPORTED
  - Assert 400 Bad Request

**File:** `backend/tests/integration/test_trade_api.py`

- Test: `test_delete_active_trade_returns_200_archived()`
  - DELETE /trades/{id} on active trade
  - Assert 200 OK, is_empty=true, executions all IGNORED
- Test: `test_delete_empty_trade_returns_204_permanent()`
  - DELETE /trades/{id} on EMPTY trade
  - Assert 204 No Content, trade not found in DB
- Test: `test_get_trades_default_excludes_empty()`
  - GET /trades (no params)
  - Assert only is_empty=false trades returned
- Test: `test_get_trades_archive_view()`
  - GET /trades?include_empty=true&only_empty=true
  - Assert only is_empty=true trades returned

### Coverage Requirements

- Integration tests: ≥80% coverage for execution and trade API endpoints
- All new endpoints tested (DELETE, POST restore)
- All query params tested (include_empty, only_empty)
- All error cases tested (403, 400, 404)
- OpenAPI spec generated and validated (no schema errors)
