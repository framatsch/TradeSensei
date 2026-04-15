## 1. Backend Schema & Types

- [ ] 1.1 Create ImportMode enum in schemas/import_schema.py (INCREMENTAL, OVERWRITE, FRESH_START)
- [ ] 1.2 Update ImportSummary schema to include tombstones_cleared, journaling_orphaned fields
- [ ] 1.3 Add mode field to import request validation schema
- [ ] 1.4 Write unit test: test_import_mode_enum_values()

## 2. Backend Import Service - Fresh Start Logic

- [ ] 2.1 Create ImportService.fresh_start_import(file, db) method
- [ ] 2.2 Implement delete phase: DELETE FROM transaction_execution_mappings
- [ ] 2.3 Implement delete phase: DELETE FROM deleted_execution_tombstones
- [ ] 2.4 Implement delete phase: DELETE FROM logical_executions
- [ ] 2.5 Implement delete phase: DELETE FROM trades
- [ ] 2.6 Wrap all deletes + import in single transaction (async with db.begin())
- [ ] 2.7 Count orphaned journaling: SELECT COUNT(*) FROM trade_notes WHERE trade_id IS NULL
- [ ] 2.8 Call existing process_import() after delete phase
- [ ] 2.9 Return ImportSummary with tombstones_cleared and journaling_orphaned counts
- [ ] 2.10 Write unit test: test_fresh_start_deletes_all_data()
- [ ] 2.11 Write unit test: test_fresh_start_clears_tombstones()
- [ ] 2.12 Write unit test: test_fresh_start_orphans_journaling()
- [ ] 2.13 Write unit test: test_fresh_start_preserves_broker_raw_transactions()

## 3. Backend Import Service - Mode Handling

- [ ] 3.1 Update ImportService.import_flex_query() to accept mode parameter
- [ ] 3.2 Add mode switch: if mode == INCREMENTAL → existing behavior
- [ ] 3.3 Add mode switch: if mode == OVERWRITE → existing overwrite behavior
- [ ] 3.4 Add mode switch: if mode == FRESH_START → call fresh_start_import()
- [ ] 3.5 Write unit test: test_import_mode_incremental()
- [ ] 3.6 Write unit test: test_import_mode_overwrite()
- [ ] 3.7 Write unit test: test_import_mode_fresh_start()

## 4. Backend Import Service - Transaction Rollback

- [ ] 4.1 Verify all Fresh Start operations wrapped in transaction
- [ ] 4.2 Add error handling: if import fails → rollback deletes
- [ ] 4.3 Write integration test: test_fresh_start_rollback_on_import_error()
- [ ] 4.4 Write integration test: test_fresh_start_commit_on_import_success()

## 5. Backend API Endpoint - Import

- [ ] 5.1 Update POST /api/v1/import/flex-query to accept mode query parameter
- [ ] 5.2 Default mode: INCREMENTAL (backward compatible)
- [ ] 5.3 Add backward compatibility: overwrite=true → mode=OVERWRITE
- [ ] 5.4 Add OpenAPI docstring explaining mode parameter
- [ ] 5.5 Add response_model with tombstones_cleared, journaling_orphaned fields

## 6. Backend API Endpoint - Nuclear Reset (Optional)

- [ ] 6.1 Create POST /api/v1/system/reset endpoint (optional enhancement)
- [ ] 6.2 Require confirm=true in request body
- [ ] 6.3 Implement delete logic (same as Fresh Start, without import)
- [ ] 6.4 Return 204 No Content on success
- [ ] 6.5 Add OpenAPI docstring with warnings
- [ ] 6.6 Write integration test: test_nuclear_reset_deletes_all_data()
- [ ] 6.7 Write integration test: test_nuclear_reset_requires_confirmation()

## 7. Backend Integration Tests

- [ ] 7.1 Test: test_fresh_start_import_full_workflow()
  - Create trades + journaling
  - Fresh Start import
  - Verify all trades deleted
  - Verify tombstones cleared
  - Verify journaling orphaned (trade_id=NULL)
  - Verify new trades imported
- [ ] 7.2 Test: test_fresh_start_allows_reimport_of_deleted_transactions()
  - Import trades with TX123
  - Delete trade (creates tombstone for TX123)
  - Fresh Start import (clears tombstone)
  - Verify TX123 can be re-imported
- [ ] 7.3 Test: test_fresh_start_preserves_broker_raw_transactions()
  - Import trades
  - Fresh Start
  - Verify BrokerRawTransactions still exist

## 8. Frontend Types

- [ ] 8.1 Create ImportMode enum in types/import.ts (INCREMENTAL, OVERWRITE, FRESH_START)
- [ ] 8.2 Update ImportSummary interface to include tombstones_cleared, journaling_orphaned
- [ ] 8.3 Update import API client types

## 9. Frontend API Client

- [ ] 9.1 Update importFlexQuery() to accept mode parameter
- [ ] 9.2 Default mode: INCREMENTAL
- [ ] 9.3 Pass mode as query parameter: /import/flex-query?mode=fresh_start

## 10. Frontend Import Dialog - Mode Selection

- [ ] 10.1 Add ImportModeSelector component (radio buttons)
- [ ] 10.2 Radio option: "Incremental (add new data)" - default
- [ ] 10.3 Radio option: "Overwrite (replace existing month)"
- [ ] 10.4 Radio option: "Fresh Start (delete all and reimport)"
- [ ] 10.5 Add help text for each mode explaining behavior
- [ ] 10.6 Wire selected mode to import API call

## 11. Frontend Import Dialog - Fresh Start Confirmation

- [ ] 11.1 Create FreshStartConfirmationDialog component
- [ ] 11.2 Dialog title: "⚠️ Fresh Start Import"
- [ ] 11.3 Add error alert: "This will permanently delete all trades and executions"
- [ ] 11.4 Add warning alert: "Journal entries will be orphaned"
- [ ] 11.5 Add "I understand this cannot be undone" checkbox
- [ ] 11.6 Destructive button styling (red)
- [ ] 11.7 Disable button until checkbox checked
- [ ] 11.8 Show when user selects Fresh Start mode

## 12. Frontend Import Summary - Enhanced Display

- [ ] 12.1 Update ImportSummary component to show tombstones_cleared
- [ ] 12.2 Update ImportSummary component to show journaling_orphaned
- [ ] 12.3 Add info text: "X tombstones cleared (previously deleted transactions)"
- [ ] 12.4 Add warning text: "Y journal entries orphaned (can be re-linked later)"
- [ ] 12.5 Add link to orphaned journaling management (if Change 3 implemented)

## 13. Frontend Settings - Nuclear Reset (Optional)

- [ ] 13.1 Create DataManagement.tsx component in settings (optional)
- [ ] 13.2 Add "Danger Zone" section
- [ ] 13.3 Add "Reset All Data" button with destructive styling
- [ ] 13.4 Create NuclearResetDialog component
- [ ] 13.5 Dialog with "I understand" checkbox and destructive button
- [ ] 13.6 Call POST /system/reset on confirmation
- [ ] 13.7 Redirect to import page after successful reset

## 14. Frontend E2E Tests - Fresh Start

- [ ] 14.1 Test: should show mode selection in import dialog
  - Open import dialog
  - Verify 3 radio options visible
  - Verify Incremental selected by default
- [ ] 14.2 Test: should show confirmation dialog when Fresh Start selected
  - Select "Fresh Start" mode
  - Verify confirmation dialog appears
  - Verify checkbox and destructive button
- [ ] 14.3 Test: should not allow Fresh Start without confirmation
  - Select "Fresh Start"
  - Leave checkbox unchecked
  - Verify button disabled
- [ ] 14.4 Test: should execute Fresh Start import successfully
  - Setup: Create trades and journaling
  - Select Fresh Start mode
  - Check "I understand"
  - Upload file
  - Verify success message
  - Verify trades list shows new imports
  - Verify old trades gone

## 15. Frontend E2E Tests - Nuclear Reset (Optional)

- [ ] 15.1 Test: should show Reset button in settings
  - Navigate to Settings > Data Management
  - Verify "Reset All Data" button visible
- [ ] 15.2 Test: should show confirmation dialog on Reset click
  - Click Reset button
  - Verify dialog with warnings
- [ ] 15.3 Test: should execute nuclear reset successfully
  - Confirm reset
  - Verify redirect to import page
  - Verify trades list empty

## 16. Documentation

- [ ] 16.1 Update import user guide with Fresh Start mode explanation
- [ ] 16.2 Add warning about data loss in import documentation
- [ ] 16.3 Document difference between modes (Incremental, Overwrite, Fresh Start)
- [ ] 16.4 Add troubleshooting section: "When to use Fresh Start"
- [ ] 16.5 Document orphaned journaling behavior

## 17. Code Review & Quality

- [ ] 17.1 Run lint-check skill (ruff + mypy)
- [ ] 17.2 Run unit-test skill (pytest with coverage ≥80%)
- [ ] 17.3 Run all E2E tests (Playwright)
- [ ] 17.4 Invoke code-reviewer agent for architecture compliance
- [ ] 17.5 Verify no regression in existing import tests

## 18. Deployment Preparation

- [ ] 18.1 Test Fresh Start on staging with production data clone
- [ ] 18.2 Verify transaction rollback works on staging database
- [ ] 18.3 Create deployment runbook (rollback steps if needed)
- [ ] 18.4 Add monitoring alerts for Fresh Start usage (track how often used)

## 19. Changelog & Release Notes

- [ ] 19.1 Invoke changelog-writer agent to update CHANGELOG.md
- [ ] 19.2 Add entry under [Unreleased] section
- [ ] 19.3 Section: Added (Fresh Start import mode, tombstone cleanup)
- [ ] 19.4 Section: Changed (Import endpoint accepts mode parameter)

---

## Summary

**Total Tasks:** 70 tasks across 19 groups

**Estimated Effort:** 1.5-2 weeks
- Backend: ~35 tasks (1 week)
- Frontend: ~25 tasks (0.5-1 week)
- Testing & Documentation: ~10 tasks (0.5 week)

**Dependencies:** 
- Requires Change 1 (tombstone infrastructure, FK constraints)

**Blocks:** 
- Change 3 (Fresh Start creates orphaned journaling data)
