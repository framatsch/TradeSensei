## ADDED Requirements

### Requirement: Execution status tracks edit history

The system SHALL automatically mark imported executions as EDITED when any field (price, quantity, commission) is modified by the user.

#### Scenario: User edits imported execution price
- **WHEN** user updates price field on an execution with status IMPORTED
- **THEN** execution status changes to EDITED
- **AND** execution remains linked to original broker transaction

#### Scenario: User edits imported execution quantity
- **WHEN** user updates quantity field on an execution with status IMPORTED
- **THEN** execution status changes to EDITED

#### Scenario: User edits imported execution commission
- **WHEN** user updates commission field on an execution with status IMPORTED
- **THEN** execution status changes to EDITED

#### Scenario: User edits manual execution
- **WHEN** user updates any field on an execution with status MANUAL
- **THEN** execution status remains MANUAL
- **AND** changes are saved normally

#### Scenario: Status transition is irreversible
- **WHEN** execution status is EDITED
- **THEN** user cannot manually change status back to IMPORTED
- **AND** re-importing same broker data does not overwrite it (default behavior)

### Requirement: User-modified executions are protected during re-import

The system SHALL skip executions with status EDITED, SPLIT, or MERGED during broker re-import with overwrite mode, unless user explicitly opts in to overwrite user modifications.

#### Scenario: Re-import skips user-modified executions by default
- **WHEN** user imports broker data with overwrite enabled
- **AND** database contains executions with status EDITED, SPLIT, or MERGED
- **THEN** user-modified executions are not deleted or modified
- **AND** corresponding broker transactions are skipped (not imported as duplicates)
- **AND** import summary shows "X user-modified executions skipped"

#### Scenario: Re-import overwrites user modifications when opted in
- **WHEN** user imports broker data with overwrite enabled
- **AND** user checks "Overwrite user modifications" checkbox in import dialog
- **THEN** EDITED, SPLIT, and MERGED executions are deleted and replaced with fresh broker data
- **AND** new executions have status IMPORTED
- **AND** user confirms action with warning dialog

#### Scenario: Re-import without overwrite mode
- **WHEN** user imports broker data without overwrite mode
- **THEN** all existing executions (including EDITED, SPLIT, MERGED) are preserved
- **AND** only new executions are created
- **AND** duplicate detection still applies (skip transactions linked to user-modified executions)

### Requirement: User-modified executions prevent duplicate imports

The system SHALL prevent importing broker transactions that correspond to existing user-modified executions (EDITED, SPLIT, MERGED), to avoid duplicate executions in the same trade.

#### Scenario: Edited execution blocks corresponding broker transaction
- **WHEN** user imports broker data with overwrite disabled
- **AND** database contains execution with status EDITED linked to raw transaction ID "TX123"
- **AND** import file contains same transaction ID "TX123"
- **THEN** transaction "TX123" is skipped (not imported)
- **AND** EDITED execution remains unchanged
- **AND** trade does not gain duplicate execution

#### Scenario: Split executions block corresponding broker transaction
- **WHEN** user has split execution into two parts (status SPLIT)
- **AND** both SPLIT executions are linked to original raw transaction ID "TX123"
- **AND** user imports broker data with overwrite disabled
- **AND** import file contains transaction ID "TX123"
- **THEN** transaction "TX123" is skipped (not imported)
- **AND** both SPLIT executions remain unchanged
- **AND** trade does not gain duplicate execution (original 100 shares would conflict with split 50+50)

#### Scenario: Merged execution blocks corresponding broker transactions
- **WHEN** user has merged multiple executions into one (status MERGED)
- **AND** MERGED execution is linked to raw transaction IDs "TX123" and "TX124"
- **AND** user imports broker data with overwrite disabled
- **AND** import file contains transactions "TX123" and "TX124"
- **THEN** both transactions are skipped (not imported)
- **AND** MERGED execution remains unchanged
- **AND** trade does not gain duplicate executions

#### Scenario: Overwrite mode with user modifications checkbox
- **WHEN** user imports broker data with overwrite enabled
- **AND** user checks "Overwrite user modifications" checkbox
- **AND** database contains EDITED, SPLIT, or MERGED executions
- **THEN** all user-modified executions are deleted
- **AND** original broker transactions are imported as fresh IMPORTED executions
- **AND** trade returns to pristine broker state

#### Scenario: Manual execution without transaction link creates duplicate
- **WHEN** user deletes imported execution and creates new MANUAL execution
- **AND** MANUAL execution has no linked raw transaction (user created from scratch)
- **AND** broker import contains transaction that was originally linked to deleted execution
- **THEN** transaction is imported as new IMPORTED execution
- **AND** trade has both MANUAL and IMPORTED executions (duplicate)
- **AND** trade.has_conflict is set to true (inconsistent position)
- **AND** import summary warns "X trades flagged with conflicts due to manual duplicates"

#### Scenario: Trade conflict banner shows after manual duplicate import
- **WHEN** trade has duplicate executions (MANUAL + IMPORTED for same data)
- **AND** trade.has_conflict is true
- **THEN** trade details page shows conflict banner
- **AND** banner message: "This trade has inconsistent executions. Review execution legs."
- **AND** user can manually delete duplicate or adjust executions

#### Scenario: User resolves conflict manually
- **WHEN** trade.has_conflict is true due to duplicate executions
- **AND** user deletes duplicate MANUAL or IMPORTED execution
- **THEN** system re-aggregates trade
- **AND** if position is now consistent, trade.has_conflict is cleared to false
- **AND** conflict banner disappears

### Requirement: Execution status is visually distinct

The system SHALL display execution status with color-coded badges in the execution legs table.

#### Scenario: Imported execution badge
- **WHEN** execution status is IMPORTED
- **THEN** badge displays "imported" in neutral color (gray)

#### Scenario: Edited execution badge
- **WHEN** execution status is EDITED
- **THEN** badge displays "edited" in warning color (amber/orange)
- **AND** badge is visually distinct from imported

#### Scenario: Manual execution badge
- **WHEN** execution status is MANUAL
- **THEN** badge displays "manual" in info color (blue)

#### Scenario: Merged/Split execution badges
- **WHEN** execution status is MERGED or SPLIT
- **THEN** badge displays appropriate label in secondary color

### Requirement: Input precision is enforced

The system SHALL enforce decimal precision limits for execution field inputs: 4 decimals for price, 2 decimals for quantity/commission/P&L.

#### Scenario: Price input allows 4 decimals
- **WHEN** user enters price with up to 4 decimal places (e.g., 155.4275)
- **THEN** value is accepted and saved
- **AND** display shows all 4 decimals

#### Scenario: Price input rejects excess decimals
- **WHEN** user enters price with more than 4 decimals (e.g., 155.42759)
- **THEN** backend validation rejects the value
- **AND** error message explains maximum precision

#### Scenario: Quantity input allows 2 decimals
- **WHEN** user enters quantity with up to 2 decimals (e.g., 50.25)
- **THEN** value is accepted and saved

#### Scenario: Commission input allows 2 decimals
- **WHEN** user enters commission with up to 2 decimals (e.g., 2.50)
- **THEN** value is accepted and saved

#### Scenario: Display formatting is consistent
- **WHEN** execution is displayed in UI
- **THEN** price shows exactly 4 decimals (e.g., 155.4275)
- **AND** quantity shows up to 2 decimals (e.g., 50.25, not 50.2500)
- **AND** commission shows exactly 2 decimals (e.g., 2.50)

## Definition of Done

### Unit Tests (Backend)

**File:** `backend/tests/unit/test_execution_service.py`

- Test: `test_update_execution_changes_imported_to_edited()`
  - Verify IMPORTED → EDITED transition on update
- Test: `test_update_execution_preserves_manual_status()`
  - Verify MANUAL status unchanged on update
- Test: `test_update_execution_preserves_merged_status()`
  - Verify MERGED status unchanged on update

**File:** `backend/tests/unit/test_import_service.py`

- Test: `test_import_overwrite_skips_edited_executions_by_default()`
  - Verify EDITED executions not deleted during overwrite
- Test: `test_import_overwrite_skips_split_executions_by_default()`
  - Verify SPLIT executions not deleted during overwrite
- Test: `test_import_overwrite_skips_merged_executions_by_default()`
  - Verify MERGED executions not deleted during overwrite
- Test: `test_import_overwrite_includes_user_modifications_when_opted_in()`
  - Verify EDITED, SPLIT, MERGED executions deleted when flag=true
- Test: `test_import_skips_broker_transactions_linked_to_edited_executions()`
  - Verify broker transaction not re-imported if EDITED execution exists
- Test: `test_import_skips_broker_transactions_linked_to_split_executions()`
  - Verify original transaction not re-imported if SPLIT executions exist
- Test: `test_import_skips_broker_transactions_linked_to_merged_execution()`
  - Verify multiple transactions not re-imported if MERGED execution exists
- Test: `test_import_prevents_duplicate_execution_in_trade()`
  - Verify trade does not gain duplicate execution when user-modified exists
- Test: `test_import_warns_on_manual_execution_duplicate()`
  - Verify import summary warns about potential duplicates with MANUAL executions
- Test: `test_import_creates_duplicate_when_manual_has_no_transaction_link()`
  - Verify MANUAL execution without transaction link allows duplicate import

**File:** `backend/tests/unit/test_execution_validation.py`

- Test: `test_price_validation_accepts_4_decimals()`
- Test: `test_price_validation_rejects_5_decimals()`
- Test: `test_quantity_validation_accepts_2_decimals()`
- Test: `test_quantity_validation_rejects_3_decimals()`
- Test: `test_commission_validation_accepts_2_decimals()`

### Integration Tests (Backend)

**File:** `backend/tests/integration/test_execution_update_api.py`

- Test: `test_patch_execution_returns_edited_status()`
  - PATCH /api/v1/executions/{id} returns status="edited"
- Test: `test_patch_execution_refetches_trade_pnl()`
  - Verify trade P&L recalculated after execution edit

### E2E Tests (Playwright)

**File:** `frontend/tests/e2e/execution-edit-status.spec.ts`

- Test: `should mark imported execution as edited after price change`
  - Navigate to trade details with imported executions
  - Edit execution price
  - Verify status badge changes to "edited"
- Test: `should display edited badge with amber color`
  - Verify badge styling for EDITED status
- Test: `should enforce 4 decimal precision on price input`
  - Attempt to enter 5 decimals in price field
  - Verify validation error or auto-truncation

**File:** `frontend/tests/e2e/re-import-protection.spec.ts`

- Test: `should skip edited executions during re-import by default`
  - Create trade with executions
  - Edit one execution (becomes EDITED)
  - Re-import same data with overwrite
  - Verify EDITED execution still exists
  - Verify import summary shows skip message
- Test: `should not create duplicate execution for edited execution`
  - Edit execution (becomes EDITED)
  - Re-import same broker file with overwrite disabled
  - Verify trade has same number of executions (no duplicate)
  - Verify EDITED execution unchanged
- Test: `should overwrite edited executions when checkbox enabled`
  - Setup edited execution
  - Re-import with "Overwrite edited" checkbox checked
  - Verify edited execution replaced with fresh import
  - Verify no duplicate execution created

**File:** `frontend/tests/e2e/execution-pnl-display.spec.ts`

- Test: `should show broker P&L for imported executions`
  - Verify P&L column displays value for IMPORTED status
- Test: `should show dash for edited execution P&L`
  - Edit execution
  - Verify P&L column shows "—"
  - Verify tooltip explains "Calculated at trade level"

### Coverage Requirements

- Unit tests: ≥80% coverage for execution service and import service changes
- E2E tests: All acceptance criteria from scenarios above must have corresponding test
- All tests must pass before merge
