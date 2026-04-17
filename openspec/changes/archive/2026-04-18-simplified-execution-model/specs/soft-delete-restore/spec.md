## Requirements

### Requirement: Execution soft-delete sets `deleted=true` by origin

The system SHALL soft-delete executions with `origin` of `imported`, `merged`, or `split` by setting `deleted=true`. Manual executions (`origin='manual'`) SHALL be hard-deleted (row physically removed) because they have no BRT anchor.

#### Scenario: DELETE imported execution → soft-delete
- **WHEN** `DELETE /executions/{id}` is called on an execution with `origin='imported'`
- **THEN** the response is `200 OK` with the execution body (including `deleted=true`)
- **AND** the execution row remains in the database with `deleted=true`
- **AND** the parent trade is re-aggregated (excluding the deleted execution)

#### Scenario: DELETE manual execution → hard-delete
- **WHEN** `DELETE /executions/{id}` is called on an execution with `origin='manual'`
- **THEN** the response is `204 No Content`
- **AND** the execution row is physically removed from the database

#### Scenario: DELETE already-deleted execution returns 409
- **WHEN** `DELETE /executions/{id}` is called on an execution that already has `deleted=true`
- **THEN** the response is `409 Conflict`

---

### Requirement: Deleted executions can be restored

The system SHALL provide a restore endpoint that sets `deleted=false` on a soft-deleted execution and re-aggregates the parent trade.

#### Scenario: Restore deleted execution
- **WHEN** `POST /executions/{id}/restore` is called on an execution with `deleted=true`
- **THEN** the response is `200 OK` with the updated execution body (`deleted=false`)
- **AND** the parent trade is re-aggregated to include the restored execution

#### Scenario: Restore non-deleted execution returns 400
- **WHEN** `POST /executions/{id}/restore` is called on an execution with `deleted=false`
- **THEN** the response is `400 Bad Request`

---

### Requirement: Deleted executions are excluded from aggregation

The FIFO aggregator SHALL exclude executions with `deleted=true` from all P&L, entry/exit price, quantity, and holding period calculations.

#### Scenario: Deleted execution excluded from P&L
- **WHEN** a trade has one deleted and one active execution
- **THEN** the trade's P&L, quantity, and price fields reflect only the active execution
- **AND** the deleted execution does not appear in FIFO matching

#### Scenario: Restoring execution updates trade P&L
- **WHEN** a previously deleted execution is restored
- **THEN** the parent trade is re-aggregated
- **AND** the trade's P&L reflects the restored execution

---

### Requirement: Trade deletion soft-deletes all child executions

The system SHALL, upon trade deletion, soft-delete all `imported|merged|split` child executions (set `deleted=true`), hard-delete all `manual` child executions, and hard-delete the `Trade` row. BRT rows are never touched.

#### Scenario: Delete trade with imported executions
- **WHEN** `DELETE /trades/{id}` is called on a trade with imported executions
- **THEN** all child executions with `origin` in `imported|merged|split` are set to `deleted=true`
- **AND** all child executions with `origin='manual'` are hard-deleted
- **AND** the `Trade` row is hard-deleted
- **AND** BRT rows linked to the affected executions remain unchanged

#### Scenario: Re-import after trade deletion skips affected transactions
- **WHEN** a trade was deleted as above and the same import file is re-imported
- **THEN** all transactions linked to the now-deleted executions are skipped (BRTs exist, executions have `deleted=true`)
- **AND** no new trades or executions are created for those transactions
