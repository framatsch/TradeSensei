## ADDED Requirements

### Requirement: Execution deletion uses soft-delete pattern to prevent re-import duplicates

The system SHALL implement soft-delete for executions with transaction links (IMPORTED, EDITED, SPLIT) by setting status to IGNORED, while preserving the TransactionExecutionMapping to prevent duplicate imports.

#### Scenario: Delete IMPORTED execution performs soft-delete
- **WHEN** user deletes an execution with status IMPORTED
- **THEN** execution.previous_status is set to IMPORTED
- **AND** execution.status is set to IGNORED
- **AND** execution remains in database (not physically deleted)
- **AND** TransactionExecutionMapping remains intact
- **AND** execution is excluded from trade P&L calculations
- **AND** execution is hidden in UI by default

#### Scenario: Delete EDITED execution performs soft-delete
- **WHEN** user deletes an execution with status EDITED
- **THEN** execution.previous_status is set to EDITED
- **AND** execution.status is set to IGNORED
- **AND** TransactionExecutionMapping remains intact

#### Scenario: Delete SPLIT execution performs soft-delete
- **WHEN** user deletes an execution with status SPLIT
- **THEN** execution.previous_status is set to SPLIT
- **AND** execution.status is set to IGNORED
- **AND** TransactionExecutionMapping remains intact

#### Scenario: Delete MANUAL execution performs hard-delete
- **WHEN** user deletes an execution with status MANUAL
- **AND** execution has no linked transaction (user-created from scratch)
- **THEN** execution is physically removed from database (hard delete)
- **AND** no TransactionExecutionMapping exists (nothing to protect)

#### Scenario: Delete MERGED execution performs hard-delete
- **WHEN** user deletes an execution with status MERGED
- **AND** MERGED execution has no direct transaction link (synthetic)
- **THEN** execution is physically removed from database (hard delete)
- **AND** original executions that were merged remain IGNORED (keep their TX links)

#### Scenario: Attempt to delete IGNORED execution is forbidden
- **WHEN** user attempts to delete an execution with status IGNORED
- **THEN** API returns 403 Forbidden
- **AND** error message: "Cannot delete already-ignored execution. Restore first or delete parent trade."
- **AND** execution remains unchanged

#### Scenario: Soft-deleted execution prevented from re-import
- **WHEN** execution with status IGNORED exists for transaction TX123
- **AND** user imports broker data containing transaction TX123
- **THEN** import service finds existing TransactionExecutionMapping for TX123
- **AND** transaction TX123 is skipped (not imported)
- **AND** IGNORED execution remains unchanged
- **AND** no duplicate execution created

### Requirement: IGNORED executions can be restored to previous status

The system SHALL allow users to restore soft-deleted (IGNORED) executions, returning them to their previous status (IMPORTED, EDITED, or SPLIT).

#### Scenario: Restore IGNORED execution to previous status
- **WHEN** user restores an execution with status IGNORED
- **AND** execution.previous_status is IMPORTED
- **THEN** execution.status is set to IMPORTED
- **AND** execution.previous_status is set to NULL
- **AND** execution becomes visible in UI
- **AND** execution is included in trade P&L calculations
- **AND** trade is re-aggregated

#### Scenario: Restore IGNORED that was EDITED
- **WHEN** user restores an IGNORED execution
- **AND** execution.previous_status is EDITED
- **THEN** execution.status is set to EDITED
- **AND** execution.previous_status is set to NULL
- **AND** execution P&L displays "—" (calculated at trade level)

#### Scenario: Restore IGNORED that was SPLIT
- **WHEN** user restores an IGNORED execution
- **AND** execution.previous_status is SPLIT
- **THEN** execution.status is set to SPLIT
- **AND** execution appears in execution legs table with SPLIT badge

#### Scenario: Restore IGNORED with NULL previous_status defaults to IMPORTED
- **WHEN** user restores an IGNORED execution
- **AND** execution.previous_status is NULL (data corruption or migration artifact)
- **THEN** execution.status is set to IMPORTED (safe fallback)
- **AND** execution.previous_status remains NULL

#### Scenario: Restore triggers trade re-aggregation
- **WHEN** user restores an IGNORED execution
- **THEN** system calls _re_aggregate_trade() for parent trade
- **AND** trade P&L is recalculated
- **AND** trade.has_conflict is rechecked
- **AND** frontend refetches trade data

#### Scenario: Restore can re-create conflict
- **WHEN** trade has MANUAL execution (100 shares)
- **AND** trade has IGNORED execution (100 shares, was IMPORTED)
- **AND** trade.has_conflict is false (only 1 active execution)
- **AND** user restores IGNORED execution
- **THEN** execution becomes IMPORTED again
- **AND** trade has MANUAL (100) + IMPORTED (100) → duplicate
- **AND** trade.has_conflict is set to true
- **AND** conflict banner appears in UI

### Requirement: Trade becomes EMPTY when all executions are IGNORED

The system SHALL compute trade.is_empty as true when all executions have status IGNORED, without storing this state in the database.

#### Scenario: Trade with all IGNORED executions is EMPTY
- **WHEN** trade has 3 executions
- **AND** all 3 executions have status IGNORED
- **THEN** trade.is_empty property returns true
- **AND** trade is excluded from performance metrics
- **AND** trade appears in "Archive" view instead of main trade list

#### Scenario: Trade with mixed statuses is not EMPTY
- **WHEN** trade has 3 executions
- **AND** 2 executions have status IGNORED
- **AND** 1 execution has status IMPORTED
- **THEN** trade.is_empty property returns false
- **AND** trade appears in main trade list
- **AND** trade included in performance metrics (using only non-IGNORED executions)

#### Scenario: Restoring execution removes EMPTY status
- **WHEN** trade is EMPTY (all executions IGNORED)
- **AND** user restores one IGNORED execution
- **THEN** trade.is_empty changes to false (computed property)
- **AND** trade moves from archive to main trade list (frontend filter)
- **AND** no database update needed (is_empty not stored)

#### Scenario: EMPTY trade displays in archive view
- **WHEN** GET /api/v1/trades with include_empty=true&only_empty=true
- **THEN** response includes only trades where is_empty=true
- **AND** each trade shows "Empty" badge in UI
- **AND** performance metrics show "—" or "N/A"

### Requirement: Trade deletion is two-stage (soft then hard)

The system SHALL implement two-stage trade deletion: first delete moves trade to EMPTY (soft-deletes all executions), second delete permanently removes trade and creates tombstones.

#### Scenario: Delete trade with active executions (Stage 1)
- **WHEN** user deletes a trade
- **AND** trade has executions with status != IGNORED
- **THEN** all active executions are soft-deleted (status → IGNORED, previous_status saved)
- **AND** trade.is_empty becomes true
- **AND** trade moves to archive view
- **AND** API returns 200 OK with message "Trade archived"
- **AND** trade remains in database

#### Scenario: Delete EMPTY trade (Stage 2 - permanent)
- **WHEN** user deletes a trade
- **AND** trade.is_empty is true (all executions IGNORED)
- **THEN** system creates DeletedExecutionTombstone for each IGNORED execution with transaction_id
- **AND** tombstone records transaction_id, account_id, deleted_at, deleted_by
- **AND** trade is hard-deleted from database (CASCADE)
- **AND** all IGNORED executions are hard-deleted (CASCADE)
- **AND** all TransactionExecutionMappings are hard-deleted (CASCADE)
- **AND** API returns 200 OK with message "Trade permanently deleted"

#### Scenario: Trade without executions can be deleted immediately
- **WHEN** user deletes a trade
- **AND** trade has no executions (data corruption or edge case)
- **THEN** trade is hard-deleted immediately (no tombstones needed)

#### Scenario: EMPTY trade deletion protects journaling data
- **WHEN** user deletes EMPTY trade
- **AND** trade has TradeNotes, TradeTags, or TradePlaybooks
- **THEN** journaling records have trade_id set to NULL (FK: ON DELETE SET NULL)
- **AND** journaling records remain in database (orphaned)
- **AND** journaling can be re-linked later (deferred to Change 3)

### Requirement: Tombstones prevent re-import of permanently deleted transactions

The system SHALL create tombstone records before permanently deleting IGNORED executions, ensuring that deleted transactions are not re-imported in future broker imports.

#### Scenario: Tombstone created on EMPTY trade deletion
- **WHEN** EMPTY trade is permanently deleted
- **AND** IGNORED execution has transaction_id = TX123
- **THEN** DeletedExecutionTombstone is created with transaction_id=TX123
- **AND** tombstone records account_id (scoped to account)
- **AND** tombstone records deleted_at timestamp
- **AND** tombstone records deleted_by user_id (audit trail)
- **AND** tombstone optionally records original_trade_id, symbol, execution_date (debugging)

#### Scenario: Import skips transactions with tombstones
- **WHEN** user imports broker data containing transaction TX123
- **AND** DeletedExecutionTombstone exists for TX123 in this account
- **THEN** import service skips TX123 (does not create execution)
- **AND** import summary shows "X transactions skipped (previously deleted)"

#### Scenario: Import checks both mappings and tombstones
- **WHEN** import service processes transaction TX123
- **THEN** check 1: TransactionExecutionMapping.exists(TX123)? → Skip
- **AND** check 2: DeletedExecutionTombstone.exists(TX123, account_id)? → Skip
- **AND** if both checks false: Import transaction (create execution)

#### Scenario: Tombstone unique per transaction
- **WHEN** system attempts to create tombstone for transaction TX123
- **AND** tombstone already exists for TX123
- **THEN** database constraint prevents duplicate (UNIQUE on transaction_id)
- **AND** operation succeeds idempotently (no error)

#### Scenario: Tombstone scoped to account
- **WHEN** Account A deletes trade with transaction TX123
- **AND** tombstone created for TX123 in Account A
- **AND** Account B imports transaction TX123
- **THEN** Account B's import succeeds (tombstone scoped to Account A)
- **AND** no cross-account interference

### Requirement: IGNORED executions are excluded from aggregation and display

The system SHALL exclude executions with status IGNORED from all P&L calculations, position aggregations, and default UI displays.

#### Scenario: IGNORED excluded from trade P&L calculation
- **WHEN** trade has 3 executions: IMPORTED (50 shares), IMPORTED (50 shares), IGNORED (100 shares)
- **AND** system calculates trade P&L
- **THEN** only 2 IMPORTED executions are used (total 100 shares)
- **AND** IGNORED execution (100 shares) is excluded
- **AND** trade shows net position: 100 shares (not 200)

#### Scenario: IGNORED excluded from performance metrics
- **WHEN** system calculates portfolio performance metrics
- **THEN** only trades with is_empty=false are included
- **AND** within each trade, only non-IGNORED executions are counted
- **AND** win rate, profit factor, Sharpe ratio exclude EMPTY trades

#### Scenario: IGNORED hidden in UI by default
- **WHEN** user views trade details page
- **AND** trade has 2 IMPORTED and 1 IGNORED execution
- **THEN** execution legs table shows only 2 IMPORTED executions
- **AND** IGNORED execution is not visible
- **AND** info banner shows "1 ignored execution hidden" with [Show] button

#### Scenario: User toggles visibility of IGNORED executions
- **WHEN** user clicks "Show ignored executions" button
- **THEN** IGNORED execution appears in table with:
  - 50% opacity (visual distinction)
  - "Ignored" badge (status indicator)
  - Strikethrough on P&L values
  - [Restore] button instead of [...] overflow menu
- **AND** table header shows "2 active, 1 ignored"

#### Scenario: Corporate action inherits IGNORED status
- **WHEN** execution with status IGNORED undergoes stock split (2:1)
- **THEN** new execution created with status IGNORED (inherited)
- **AND** original execution remains IGNORED
- **AND** both IGNORED executions excluded from P&L
- **AND** both hidden in UI by default

## Definition of Done

### Database Migrations

**File:** `backend/alembic/versions/XXX_add_ignored_status.py`
- Migration adds "edited" and "ignored" to execution_status_enum
- No data migration (existing rows unchanged)
- Tested on staging with production data clone

**File:** `backend/alembic/versions/XXX_add_previous_status.py`
- Migration adds previous_status column (NULLABLE)
- Column defaults to NULL for existing rows
- Tested with backward compatibility (old code ignores new column)

**File:** `backend/alembic/versions/XXX_create_tombstones.py`
- Migration creates deleted_execution_tombstones table
- Indexes on transaction_id, account_id, deleted_at
- UNIQUE constraint on transaction_id
- Tested with concurrent inserts (idempotency)

**File:** `backend/alembic/versions/XXX_update_journaling_fk.py`
- Migration changes FK constraints to ON DELETE SET NULL
- Applied to trade_notes, trade_tags, trade_playbooks
- Tested with cascade behavior

### Unit Tests (Backend)

**File:** `backend/tests/unit/test_execution_service_soft_delete.py`

- Test: `test_delete_imported_execution_soft_deletes()`
  - Verify IMPORTED → IGNORED, previous_status saved, mapping intact
- Test: `test_delete_edited_execution_soft_deletes()`
  - Verify EDITED → IGNORED, previous_status saved
- Test: `test_delete_split_execution_soft_deletes()`
  - Verify SPLIT → IGNORED
- Test: `test_delete_manual_execution_hard_deletes()`
  - Verify MANUAL → physical delete, no mapping
- Test: `test_delete_merged_execution_hard_deletes()`
  - Verify MERGED → physical delete
- Test: `test_delete_ignored_execution_forbidden()`
  - Verify returns 403, execution unchanged
- Test: `test_restore_ignored_to_imported()`
  - Verify IGNORED → IMPORTED when previous_status=IMPORTED
- Test: `test_restore_ignored_to_edited()`
  - Verify IGNORED → EDITED when previous_status=EDITED
- Test: `test_restore_triggers_trade_reaggregation()`
  - Verify _re_aggregate_trade() called after restore
- Test: `test_restore_rechecks_conflict()`
  - Verify has_conflict updated after restore

**File:** `backend/tests/unit/test_trade_service_empty.py`

- Test: `test_trade_is_empty_when_all_ignored()`
  - Verify computed property returns true
- Test: `test_trade_not_empty_when_mixed_statuses()`
  - Verify returns false when 1+ active execution
- Test: `test_delete_active_trade_soft_deletes_executions()`
  - Verify Stage 1: all executions → IGNORED, trade.is_empty=true
- Test: `test_delete_empty_trade_creates_tombstones()`
  - Verify Stage 2: tombstones created, hard delete
- Test: `test_delete_empty_trade_cascades_to_executions()`
  - Verify IGNORED executions deleted (CASCADE)
- Test: `test_delete_empty_trade_orphans_journaling()`
  - Verify TradeNote.trade_id = NULL after delete

**File:** `backend/tests/unit/test_tombstone_service.py`

- Test: `test_create_tombstone()`
  - Verify tombstone record created with all fields
- Test: `test_tombstone_unique_per_transaction()`
  - Verify duplicate tombstone fails gracefully (UNIQUE constraint)
- Test: `test_tombstone_scoped_to_account()`
  - Verify Account A tombstone doesn't affect Account B

**File:** `backend/tests/unit/test_import_service_tombstones.py`

- Test: `test_import_skips_transaction_with_mapping()`
  - Verify existing mapping → skip
- Test: `test_import_skips_transaction_with_tombstone()`
  - Verify existing tombstone → skip
- Test: `test_import_creates_execution_when_no_mapping_or_tombstone()`
  - Verify both checks false → import
- Test: `test_import_summary_shows_tombstone_skips()`
  - Verify summary: "X transactions skipped (previously deleted)"

**File:** `backend/tests/unit/test_aggregator_ignores_ignored.py`

- Test: `test_trade_pnl_excludes_ignored_executions()`
  - Verify P&L calculation skips IGNORED
- Test: `test_performance_metrics_exclude_empty_trades()`
  - Verify metrics skip trades where is_empty=true
- Test: `test_position_calculation_excludes_ignored()`
  - Verify net position excludes IGNORED executions

### Integration Tests (Backend)

**File:** `backend/tests/integration/test_soft_delete_workflow.py`

- Test: `test_full_soft_delete_and_restore_workflow()`
  - Create IMPORTED → delete (soft) → verify IGNORED → restore → verify IMPORTED
- Test: `test_empty_trade_deletion_with_tombstones()`
  - Delete all executions → trade EMPTY → delete trade → verify tombstones created
- Test: `test_reimport_after_soft_delete()`
  - Delete execution → import same data → verify no duplicate
- Test: `test_reimport_after_permanent_delete()`
  - Delete EMPTY trade → import same data → verify tombstone blocks import

### E2E Tests (Playwright)

**File:** `frontend/tests/e2e/execution-soft-delete.spec.ts`

- Test: `should soft-delete imported execution and show ignored badge`
  - Navigate to trade with IMPORTED executions
  - Delete execution via overflow menu
  - Verify execution disappears from visible list
  - Click "Show ignored" → verify execution visible with 50% opacity
  - Verify "Ignored" badge displayed
- Test: `should restore ignored execution to previous status`
  - Setup trade with IGNORED execution (previous_status=EDITED)
  - Click "Show ignored"
  - Click [Restore] button on IGNORED execution
  - Verify execution returns to visible list with "Edited" badge
  - Verify execution no longer in ignored list

**File:** `frontend/tests/e2e/empty-trade-management.spec.ts`

- Test: `should mark trade as empty when all executions deleted`
  - Create trade with 2 executions
  - Delete both executions
  - Verify trade shows "Empty" badge
  - Verify trade moves to Archive tab
- Test: `should restore trade from archive when execution restored`
  - Navigate to Archive tab
  - Open EMPTY trade
  - Click "Show ignored"
  - Restore one execution
  - Verify trade moves back to main trade list
- Test: `should permanently delete empty trade with confirmation`
  - Setup EMPTY trade in archive
  - Click delete on EMPTY trade
  - Verify warning dialog: "This will permanently delete the trade"
  - Confirm deletion
  - Verify trade removed from archive

**File:** `frontend/tests/e2e/reimport-after-delete.spec.ts`

- Test: `should not create duplicate after soft-delete and reimport`
  - Create trade with imported executions
  - Delete one execution (soft-delete)
  - Re-import same broker file
  - Verify no duplicate execution created
  - Verify trade has same number of visible executions

### Coverage Requirements

- Unit tests: ≥85% coverage for execution service, trade service, import service, aggregator
- Integration tests: All soft-delete → restore → re-import workflows covered
- E2E tests: All user-facing scenarios (delete, restore, EMPTY trade, archive) covered
- All tests must pass before merge
- No regression in existing tests
