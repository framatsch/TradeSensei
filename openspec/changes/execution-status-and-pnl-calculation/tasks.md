## 1. Database Migrations

- [ ] 1.1 Create migration: Add 'edited' and 'ignored' to execution_status_enum
- [ ] 1.2 Create migration: Add previous_status column (NULLABLE) to logical_executions table
- [ ] 1.3 Create migration: Create deleted_execution_tombstones table with indexes
- [ ] 1.4 Create migration: Update FK constraints for journaling tables (ON DELETE SET NULL)
- [ ] 1.5 Test all migrations on local database (up and down)
- [ ] 1.6 Test migrations on staging with production data clone
- [ ] 1.7 Verify backward compatibility (old code can run with new schema)

## 2. Backend Models

- [ ] 2.1 Add ExecutionStatus.EDITED and IGNORED to logical_execution.py enum with docstrings
- [ ] 2.2 Add previous_status field to LogicalExecution model (Column, Enum, nullable=True)
- [ ] 2.3 Create DeletedExecutionTombstone model in new file models/deleted_execution_tombstone.py
- [ ] 2.4 Add unique constraint on DeletedExecutionTombstone.transaction_id
- [ ] 2.5 Add indexes: (transaction_id, account_id), (deleted_at)
- [ ] 2.6 Add is_empty computed property to Trade model (@property)
- [ ] 2.7 Update FK constraints in TradeNote, TradeTag, TradePlaybook models (ondelete="SET NULL")

## 3. Backend Schemas (Pydantic)

- [ ] 3.1 Update ExecutionStatus enum in schemas/execution.py (add EDITED, IGNORED)
- [ ] 3.2 Add previous_status: Optional[ExecutionStatus] to ExecutionResponse schema
- [ ] 3.3 Add is_empty: bool to TradeResponse schema
- [ ] 3.4 Add TradeListParams schema with include_empty, only_empty query params
- [ ] 3.5 Add decimal precision validation to LogicalExecutionUpdate (4 decimals price, 2 decimals qty/commission)
- [ ] 3.6 Add error codes to schemas/error.py: execution_already_ignored, execution_not_ignored, execution_ignored
- [ ] 3.7 Write unit tests for decimal validation (accept 4/2 decimals, reject 5/3)

## 4. Backend Tombstone Service (NEW)

- [ ] 4.1 Create services/tombstone.py with TombstoneService class
- [ ] 4.2 Implement create_tombstone(transaction_id, account_id, user_id, ...) method
- [ ] 4.3 Handle unique constraint violation gracefully (idempotent insert)
- [ ] 4.4 Implement tombstone_exists(transaction_id, account_id) -> bool method
- [ ] 4.5 Write unit tests: test_create_tombstone(), test_tombstone_unique_per_transaction()
- [ ] 4.6 Write unit tests: test_tombstone_scoped_to_account()

## 5. Backend Execution Service - Soft Delete

- [ ] 5.1 Update ExecutionService.delete_execution() to implement soft-delete logic
- [ ] 5.2 Soft-delete: IMPORTED/EDITED/SPLIT → set previous_status, status=IGNORED, return execution
- [ ] 5.3 Hard-delete: MANUAL/MERGED → physical delete, return None
- [ ] 5.4 Raise HTTPException 403 when attempting to delete IGNORED execution
- [ ] 5.5 Call _re_aggregate_trade() after soft-delete
- [ ] 5.6 Update delete_execution return type: Execution | None
- [ ] 5.7 Write unit test: test_delete_imported_execution_soft_deletes()
- [ ] 5.8 Write unit test: test_delete_edited_execution_soft_deletes()
- [ ] 5.9 Write unit test: test_delete_split_execution_soft_deletes()
- [ ] 5.10 Write unit test: test_delete_manual_execution_hard_deletes()
- [ ] 5.11 Write unit test: test_delete_merged_execution_hard_deletes()
- [ ] 5.12 Write unit test: test_delete_ignored_execution_forbidden()

## 6. Backend Execution Service - Restore

- [ ] 6.1 Create ExecutionService.restore_execution(execution_id) method (NEW)
- [ ] 6.2 Verify execution.status == IGNORED, else raise HTTPException 400
- [ ] 6.3 Set status = previous_status (or IMPORTED if NULL)
- [ ] 6.4 Set previous_status = NULL
- [ ] 6.5 Call _re_aggregate_trade() after restore
- [ ] 6.6 Recheck trade.has_conflict after restore (can re-create conflict)
- [ ] 6.7 Return restored execution
- [ ] 6.8 Write unit test: test_restore_ignored_to_imported()
- [ ] 6.9 Write unit test: test_restore_ignored_to_edited()
- [ ] 6.10 Write unit test: test_restore_ignored_to_split()
- [ ] 6.11 Write unit test: test_restore_null_previous_status_defaults_to_imported()
- [ ] 6.12 Write unit test: test_restore_non_ignored_returns_400()
- [ ] 6.13 Write unit test: test_restore_triggers_trade_reaggregation()
- [ ] 6.14 Write unit test: test_restore_rechecks_conflict()

## 7. Backend Execution Service - Auto-Transition to EDITED

- [ ] 7.1 Update ExecutionService.update_execution() to auto-transition IMPORTED → EDITED
- [ ] 7.2 Add validation: reject updates to IGNORED executions (raise 400)
- [ ] 7.3 Write unit test: test_update_execution_changes_imported_to_edited()
- [ ] 7.4 Write unit test: test_update_execution_preserves_manual_status()
- [ ] 7.5 Write unit test: test_update_execution_preserves_merged_status()
- [ ] 7.6 Write unit test: test_update_ignored_execution_returns_400()

## 8. Backend Trade Service - EMPTY and Two-Stage Delete

- [ ] 8.1 Add is_empty computed property to Trade model (@property, check all executions IGNORED)
- [ ] 8.2 Update TradeService.delete_trade() to implement two-stage deletion
- [ ] 8.3 Stage 1 (active trade): Soft-delete all executions, return updated trade
- [ ] 8.4 Stage 2 (EMPTY trade): Create tombstones, hard-delete trade, return None
- [ ] 8.5 Call TombstoneService.create_tombstone() for each IGNORED execution with transaction_id
- [ ] 8.6 Verify CASCADE deletes IGNORED executions + mappings
- [ ] 8.7 Verify journaling orphaned (trade_id → NULL) via FK constraint
- [ ] 8.8 Write unit test: test_trade_is_empty_when_all_ignored()
- [ ] 8.9 Write unit test: test_trade_not_empty_when_mixed_statuses()
- [ ] 8.10 Write unit test: test_delete_active_trade_soft_deletes_executions()
- [ ] 8.11 Write unit test: test_delete_empty_trade_creates_tombstones()
- [ ] 8.12 Write unit test: test_delete_empty_trade_cascades_to_executions()
- [ ] 8.13 Write unit test: test_delete_empty_trade_orphans_journaling()

## 9. Backend Trade Service - Query Filtering

- [ ] 9.1 Update TradeService.get_trades() to accept include_empty, only_empty params
- [ ] 9.2 Default behavior: Filter out trades where is_empty=True
- [ ] 9.3 include_empty=True: Return all trades
- [ ] 9.4 only_empty=True: Return only EMPTY trades
- [ ] 9.5 Write unit test: test_get_trades_default_excludes_empty()
- [ ] 9.6 Write unit test: test_get_trades_include_empty()
- [ ] 9.7 Write unit test: test_get_trades_only_empty()

## 10. Backend Aggregation - Exclude IGNORED

- [ ] 10.1 Update trade P&L calculation to exclude IGNORED executions
- [ ] 10.2 Update position calculation to exclude IGNORED executions
- [ ] 10.3 Update TradeService.get_performance_metrics() to exclude EMPTY trades
- [ ] 10.4 Verify win rate, profit factor calculations skip EMPTY trades
- [ ] 10.5 Write unit test: test_trade_pnl_excludes_ignored_executions()
- [ ] 10.6 Write unit test: test_performance_metrics_exclude_empty_trades()
- [ ] 10.7 Write unit test: test_position_calculation_excludes_ignored()

## 11. Backend Import Service - Tombstone Check

- [ ] 11.1 Update ImportService to check both TransactionExecutionMapping AND DeletedExecutionTombstone
- [ ] 11.2 Implement should_skip_transaction(tx_id, account_id) helper method
- [ ] 11.3 Skip transaction if mapping exists OR tombstone exists
- [ ] 11.4 Update import summary to show: "X transactions skipped (previously deleted)"
- [ ] 11.5 Write unit test: test_import_skips_transaction_with_mapping()
- [ ] 11.6 Write unit test: test_import_skips_transaction_with_tombstone()
- [ ] 11.7 Write unit test: test_import_creates_execution_when_no_mapping_or_tombstone()
- [ ] 11.8 Write unit test: test_import_summary_shows_tombstone_skips()

## 12. Backend Import Service - Protect User-Modified

- [ ] 12.1 Update ImportService._clear_existing_data() to filter out EDITED/SPLIT/MERGED executions by default
- [ ] 12.2 Add overwrite_user_modifications parameter to import endpoint (future enhancement, optional for MVP)
- [ ] 12.3 Skip broker transactions linked to EDITED/SPLIT/MERGED executions (prevent duplicates)
- [ ] 12.4 Write unit test: test_import_overwrite_skips_edited_executions_by_default()
- [ ] 12.5 Write unit test: test_import_overwrite_skips_split_executions_by_default()
- [ ] 12.6 Write unit test: test_import_overwrite_skips_merged_executions_by_default()
- [ ] 12.7 Write unit test: test_import_skips_broker_transactions_linked_to_edited_executions()
- [ ] 12.8 Write unit test: test_import_prevents_duplicate_execution_in_trade()

## 13. Backend Corporate Action - Status Inheritance

- [ ] 13.1 Update Corporate Action Processor to inherit status when creating split executions
- [ ] 13.2 New execution.status = original.status (inherit IGNORED, IMPORTED, etc.)
- [ ] 13.3 New execution.previous_status = original.previous_status (also inherit)
- [ ] 13.4 Special case: MERGED after split → original becomes IGNORED, new executions are SPLIT
- [ ] 13.5 Write unit test: test_split_inherits_ignored_status()
- [ ] 13.6 Write unit test: test_split_on_merged_creates_split_executions()

## 14. Backend API Endpoints - Execution

- [ ] 14.1 Update DELETE /api/v1/executions/{id} to return 200 OK for soft-delete (with body)
- [ ] 14.2 Return 204 No Content for hard-delete (no body)
- [ ] 14.3 Return 403 Forbidden for IGNORED execution
- [ ] 14.4 Create POST /api/v1/executions/{id}/restore endpoint (NEW)
- [ ] 14.5 Return 200 OK with restored execution
- [ ] 14.6 Return 400 Bad Request if not IGNORED
- [ ] 14.7 Update PATCH /api/v1/executions/{id} to reject IGNORED executions (400)
- [ ] 14.8 Add OpenAPI docstrings for all endpoints
- [ ] 14.9 Add response_model annotations

## 15. Backend API Endpoints - Trade

- [ ] 15.1 Update DELETE /api/v1/trades/{id} to implement two-stage deletion
- [ ] 15.2 Return 200 OK with message "Trade archived" for Stage 1
- [ ] 15.3 Return 204 No Content for Stage 2 (permanent delete)
- [ ] 15.4 Update GET /api/v1/trades to accept include_empty, only_empty query params
- [ ] 15.5 Default: include_empty=false (filter out EMPTY)
- [ ] 15.6 Update GET /api/v1/trades/{id} to include is_empty in response
- [ ] 15.7 GET /api/v1/trades/{id}/executions returns all executions (including IGNORED)
- [ ] 15.8 Add OpenAPI docstrings for all endpoints

## 16. Backend Integration Tests

- [ ] 16.1 Test: test_delete_imported_returns_200_soft_delete() (DELETE /executions/{id})
- [ ] 16.2 Test: test_delete_manual_returns_204_hard_delete()
- [ ] 16.3 Test: test_delete_ignored_returns_403()
- [ ] 16.4 Test: test_restore_ignored_returns_200() (POST /executions/{id}/restore)
- [ ] 16.5 Test: test_restore_non_ignored_returns_400()
- [ ] 16.6 Test: test_update_ignored_returns_400() (PATCH /executions/{id})
- [ ] 16.7 Test: test_delete_active_trade_returns_200_archived() (DELETE /trades/{id})
- [ ] 16.8 Test: test_delete_empty_trade_returns_204_permanent()
- [ ] 16.9 Test: test_get_trades_default_excludes_empty() (GET /trades)
- [ ] 16.10 Test: test_get_trades_archive_view() (?include_empty=true&only_empty=true)
- [ ] 16.11 Test: test_full_soft_delete_and_restore_workflow()
- [ ] 16.12 Test: test_empty_trade_deletion_with_tombstones()
- [ ] 16.13 Test: test_reimport_after_soft_delete()
- [ ] 16.14 Test: test_reimport_after_permanent_delete()

## 17. Frontend Types

- [ ] 17.1 Update ExecutionStatus enum in types/execution.ts (add EDITED, IGNORED)
- [ ] 17.2 Add previous_status: ExecutionStatus | null to Execution interface
- [ ] 17.3 Add is_empty: boolean to Trade interface
- [ ] 17.4 Update API client types (regenerate from OpenAPI spec)

## 18. Frontend API Client

- [ ] 18.1 Update deleteExecution() to handle 200 OK response (soft-delete)
- [ ] 18.2 Add restoreExecution(id: number) method (POST /executions/{id}/restore)
- [ ] 18.3 Update getTrades() to accept include_empty, only_empty query params
- [ ] 18.4 Update deleteTrade() to handle 200 OK (Stage 1) vs 204 (Stage 2)

## 19. Frontend Hooks

- [ ] 19.1 Update useDeleteExecution mutation hook (handle 200 OK response)
- [ ] 19.2 Create useRestoreExecution mutation hook (NEW)
- [ ] 19.3 Refetch trade and executions after restore (refetchQueries type: "all")
- [ ] 19.4 Add success/error toast notifications
- [ ] 19.5 Update useTrade to handle is_empty field
- [ ] 19.6 Update useDeleteTrade to handle two-stage deletion

## 20. Frontend ExecutionStatusBadge Component

- [ ] 20.1 Add EDITED status styling: amber color, "Edited" text, default variant
- [ ] 20.2 Add IGNORED status styling: gray color, "Ignored" text, ghost variant (outline)
- [ ] 20.3 Verify all status colors match design system
- [ ] 20.4 Add Storybook stories for all statuses
- [ ] 20.5 Add visual regression test (screenshot comparison)

## 21. Frontend ExecutionRow Component

- [ ] 21.1 Add conditional rendering: [Restore] button for IGNORED, [...] menu for others
- [ ] 21.2 Add 50% opacity for IGNORED rows (Tailwind: opacity-50)
- [ ] 21.3 Add strikethrough on P&L for IGNORED (text-decoration: line-through)
- [ ] 21.4 Add onClick handler for restore button
- [ ] 21.5 Show loading spinner during restore
- [ ] 21.6 Update P&L display: show value only for IMPORTED with non-null pnl, else "—"
- [ ] 21.7 Add tooltip to "—" explaining "P&L calculated at trade level"

## 22. Frontend ExecutionLegsTable Component

- [ ] 22.1 Add show/hide IGNORED toggle state management (useState)
- [ ] 22.2 Create info banner component for "X ignored executions hidden" with [Show] button
- [ ] 22.3 Conditional rendering: show banner only if IGNORED count > 0
- [ ] 22.4 Filter IGNORED executions when toggle OFF
- [ ] 22.5 Sort executions: active first (by timestamp), IGNORED last (by timestamp)
- [ ] 22.6 Add visual separator (dashed border) between active and IGNORED groups
- [ ] 22.7 Update banner text when toggled: "X active, Y ignored"

## 23. Frontend TradeCard Component

- [ ] 23.1 Add conditional "Empty" badge when trade.is_empty
- [ ] 23.2 Badge styling: gray color, ghost variant (outline)
- [ ] 23.3 Conditional metrics: show "—" for P&L, "N/A" for return % when is_empty
- [ ] 23.4 Hide win/loss badge when is_empty

## 24. Frontend TradeDetailPage Component

- [ ] 24.1 Add large info banner at top for EMPTY trades
- [ ] 24.2 Banner text: "This trade is empty. All executions have been deleted."
- [ ] 24.3 Banner subtext: "Restore executions below to reactivate this trade."
- [ ] 24.4 Banner styling: neutral blue background, info icon
- [ ] 24.5 Show all IGNORED executions by default when trade is EMPTY (no toggle needed)

## 25. Frontend TradeList and Archive Tab

- [ ] 25.1 Create Archive tab in TradeListTabs component
- [ ] 25.2 Add badge with EMPTY trade count: "Archive (5)"
- [ ] 25.3 Default tab: GET /trades?include_empty=false
- [ ] 25.4 Archive tab: GET /trades?include_empty=true&only_empty=true
- [ ] 25.5 Filter EMPTY trades from default view (frontend filter as backup)

## 26. Frontend DeleteTradeDialog Component

- [ ] 26.1 Create two dialog variants: active trade vs EMPTY trade
- [ ] 26.2 Active trade dialog: "Archive this trade?" with soft-delete explanation
- [ ] 26.3 EMPTY trade dialog: "Permanently delete this trade?" with warning
- [ ] 26.4 EMPTY dialog: Red destructive button styling
- [ ] 26.5 EMPTY dialog: Warning text "⚠️ Broker transactions will be blocked from re-import"
- [ ] 26.6 Optional: Add checkbox "Also delete journal entries" (future enhancement)

## 27. Frontend Input Precision

- [ ] 27.1 Add step="0.0001" to price input field in ExecutionRow
- [ ] 27.2 Add step="0.01" to quantity and commission input fields
- [ ] 27.3 Update display formatting: price.toFixed(4), qty.toFixed(2), commission.toFixed(2)
- [ ] 27.4 Add client-side validation error messages for excess decimals

## 28. Frontend E2E Tests - Soft Delete

**File:** `frontend/tests/e2e/execution-soft-delete.spec.ts`

- [ ] 28.1 Test: should soft-delete imported execution and show ignored badge
- [ ] 28.2 Test: should restore ignored execution to previous status
- [ ] 28.3 Test: should show ignored execution with 50% opacity when toggle ON
- [ ] 28.4 Test: should hide ignored executions by default

## 29. Frontend E2E Tests - EMPTY Trade

**File:** `frontend/tests/e2e/empty-trade-management.spec.ts`

- [ ] 29.1 Test: should mark trade as empty when all executions deleted
- [ ] 29.2 Test: should show empty badge on trade card
- [ ] 29.3 Test: should show info banner on empty trade detail page
- [ ] 29.4 Test: should restore trade from archive when execution restored
- [ ] 29.5 Test: should permanently delete empty trade with confirmation

## 30. Frontend E2E Tests - Archive Tab

**File:** `frontend/tests/e2e/archive-tab.spec.ts`

- [ ] 30.1 Test: should show only empty trades in archive tab
- [ ] 30.2 Test: should show correct count in archive tab badge
- [ ] 30.3 Test: should move trade to active list after restore

## 31. Frontend E2E Tests - Re-import After Delete

**File:** `frontend/tests/e2e/reimport-after-delete.spec.ts`

- [ ] 31.1 Test: should not create duplicate after soft-delete and reimport
- [ ] 31.2 Test: should not create duplicate after permanent delete and reimport (tombstone protection)

## 32. Frontend E2E Tests - Execution Edit Status

**File:** `frontend/tests/e2e/execution-edit-status.spec.ts`

- [ ] 32.1 Test: should mark imported execution as edited after price change
- [ ] 32.2 Test: should display edited badge with amber color
- [ ] 32.3 Test: should enforce 4 decimal precision on price input

## 33. Frontend E2E Tests - P&L Display

**File:** `frontend/tests/e2e/execution-pnl-display.spec.ts`

- [ ] 33.1 Test: should show broker P&L for imported executions
- [ ] 33.2 Test: should show dash for edited execution P&L
- [ ] 33.3 Test: should show tooltip on execution P&L dash

## 34. Frontend Visual Regression Tests

- [ ] 34.1 Capture: Execution row with IMPORTED status
- [ ] 34.2 Capture: Execution row with EDITED status (amber badge)
- [ ] 34.3 Capture: Execution row with IGNORED status (50% opacity, gray badge)
- [ ] 34.4 Capture: Info banner "X ignored executions hidden"
- [ ] 34.5 Capture: Trade card with "Empty" badge
- [ ] 34.6 Capture: EMPTY trade detail with info banner
- [ ] 34.7 Capture: Delete dialog for active trade
- [ ] 34.8 Capture: Delete dialog for EMPTY trade

## 35. Frontend Accessibility Tests

- [ ] 35.1 Test: Keyboard navigation through execution table (Tab to Restore button)
- [ ] 35.2 Test: Screen reader announces IGNORED status (aria-label)
- [ ] 35.3 Test: Color contrast for all badges (WCAG AA: ≥4.5:1)
- [ ] 35.4 Test: Focus indicators visible on all interactive elements
- [ ] 35.5 Run axe-core via Playwright (no violations)

## 36. Documentation

- [ ] 36.1 Update AGENTS.md: Document soft-delete pattern and tombstone protection
- [ ] 36.2 Update AGENTS.md: Add IGNORED and EDITED to execution status descriptions
- [ ] 36.3 Create docs/architecture/soft-delete-pattern.md explaining the design
- [ ] 36.4 Update API documentation (OpenAPI annotations complete)
- [ ] 36.5 Add migration guide for developers (how to test locally)

## 37. Code Review & Quality

- [ ] 37.1 Run lint-check skill (ruff + mypy)
- [ ] 37.2 Run unit-test skill (pytest with coverage ≥85%)
- [ ] 37.3 Run all E2E tests (Playwright)
- [ ] 37.4 Invoke code-reviewer agent for architecture compliance check
- [ ] 37.5 Fix any blockers identified by code-reviewer
- [ ] 37.6 Verify no regression in existing tests (test_pnl_regression.py still passes)

## 38. Deployment Preparation

- [ ] 38.1 Test all migrations on staging with production data clone
- [ ] 38.2 Verify backward compatibility (old code can run with new schema)
- [ ] 38.3 Create deployment runbook (migration order, rollback steps)
- [ ] 38.4 Create smoke test checklist for post-deployment verification
- [ ] 38.5 Prepare monitoring alerts (error rate spikes, import failures)

## 39. Changelog & Release Notes

- [ ] 39.1 Invoke changelog-writer agent to update CHANGELOG.md
- [ ] 39.2 Add entry under [Unreleased] section following Keep a Changelog format
- [ ] 39.3 Section: Added (soft-delete, restore, EMPTY trades, tombstones)
- [ ] 39.4 Section: Changed (DELETE execution now returns 200 for soft-delete)
- [ ] 39.5 Section: Fixed (infinite duplicate re-import problem solved)

---

## Summary

**Total Tasks:** ~235 tasks across 39 groups

**Estimated Effort:**
- Database & Backend: ~70 tasks (2-3 weeks)
- Frontend Implementation: ~90 tasks (2-3 weeks)
- Testing (Unit + Integration + E2E): ~60 tasks (1-2 weeks)
- Documentation & Review: ~15 tasks (3-5 days)

**Critical Path:**
1. Database migrations → Backend models → Backend services
2. API endpoints → Frontend hooks → Frontend components
3. E2E tests → Code review → Deployment

**Dependencies:**
- All backend tasks must complete before frontend API client work
- All component work must complete before E2E tests
- All tests must pass before code review
- Code review must pass before deployment
