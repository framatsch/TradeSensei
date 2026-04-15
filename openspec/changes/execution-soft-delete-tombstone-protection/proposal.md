## Why

When users delete imported executions, the system performs hard-delete (physical removal), which destroys the `TransactionExecutionMapping`. This causes an **infinite duplicate re-import problem**:

1. User deletes IMPORTED execution → Mapping destroyed
2. Next Flex Query import finds the transaction → No mapping exists → "New transaction!"
3. System imports it again → Duplicate execution created
4. User deletes duplicate → Mapping destroyed again
5. **Infinite cycle**: Every import recreates the duplicate

This is especially severe when:
- User deletes IMPORTED and creates MANUAL (no transaction link)
- EMPTY trades are deleted and later re-imported
- Corporate actions occur on deleted executions

Additional problems:
- **No edit tracking**: Modified executions can't be distinguished from pristine broker data
- **Re-import risk**: User edits silently discarded during re-import with overwrite
- **P&L inconsistency**: Broker-reported execution P&L becomes wrong after user edits

## What Changes

**Soft-Delete Pattern for Executions:**
- Implement `IGNORED` status for soft-deleted executions (keeps transaction link intact)
- Add `previous_status` field to enable correct restoration (EDITED → IGNORED → EDITED, not → IMPORTED)
- Implement two-stage trade deletion: active trades → EMPTY (all executions IGNORED) → permanent delete

**Tombstone Protection:**
- Create `deleted_execution_tombstones` table to prevent re-import of permanently deleted executions
- Before hard-deleting IGNORED executions (on EMPTY trade delete), create tombstone records
- Import service checks both TransactionExecutionMapping AND tombstones before importing

**Execution Edit Tracking:**
- Add `EDITED` status to distinguish modified imported executions from pristine broker data
- Automatically transition IMPORTED → EDITED when user modifies price/quantity/commission
- Protect EDITED, SPLIT, MERGED executions from overwrite during re-import

**P&L Calculation Rules:**
- Execution P&L only displayed for IMPORTED executions with broker-reported data
- Trade P&L always calculated (source of truth for EDITED/MANUAL/IGNORED executions)
- Standardize decimal precision: 4 decimals for price, 2 for quantity/commission/P&L

**UI for Soft-Deleted Executions:**
- Show/hide IGNORED executions toggle in execution legs table
- Restore button for IGNORED executions (returns to previous_status)
- EMPTY trade badge and archive view
- Visual distinction (50% opacity, "Ignored" badge, strikethrough P&L)

## Capabilities

### New Capabilities
- `execution-soft-delete`: Soft-delete pattern with IGNORED status and tombstone protection
- `execution-restore`: Restore soft-deleted executions to previous status
- `empty-trade-management`: Detect and handle trades with all executions ignored
- `tombstone-protection`: Prevent re-import of permanently deleted transactions
- `execution-edit-tracking`: Track and protect user modifications to imported executions
- `pnl-calculation-rules`: Consistent P&L calculation logic based on execution status

### Modified Capabilities
- `execution-management`: Add EDITED and IGNORED statuses to execution lifecycle
- `trade-deletion`: Two-stage deletion (soft → hard) with tombstone creation
- `broker-import`: Skip executions with existing mappings OR tombstones
- `trade-aggregation`: Exclude IGNORED executions from P&L and position calculations
- `conflict-detection`: Auto-clear has_conflict when duplicates resolved

## Impact

**Database:**
- Add "edited" and "ignored" to execution_status_enum
- Add previous_status column to logical_executions (NULLABLE)
- Create deleted_execution_tombstones table with indexes
- Update FK constraints for journaling (ON DELETE SET NULL)

**Backend:**
- `app/models/logical_execution.py` - Add EDITED and IGNORED enum values, previous_status field
- `app/models/deleted_execution_tombstone.py` - NEW: Tombstone model
- `app/services/execution.py` - Soft-delete logic, restore logic, auto-transition IMPORTED→EDITED
- `app/services/trade.py` - Two-stage delete, is_empty property, EMPTY trade handling
- `app/services/tombstone.py` - NEW: Tombstone service (create, check existence)
- `app/services/import_service.py` - Check tombstones, skip user-modified executions
- `app/repositories/logical_execution_repository.py` - Filter IGNORED from queries (optional)
- Database migrations: 4 migrations (enum, previous_status, tombstones, FK constraints)

**Frontend:**
- `components/trades/ExecutionRow.tsx` - Status badge, conditional P&L, restore button, 50% opacity
- `components/trades/ExecutionStatusBadge.tsx` - EDITED (amber) and IGNORED (gray ghost) styling
- `components/trades/ExecutionLegsTable.tsx` - Show/hide IGNORED toggle, info banner
- `components/trades/TradeCard.tsx` - EMPTY trade badge
- `components/trades/TradeDetailPage.tsx` - EMPTY trade info banner
- `components/trades/TradeListTabs.tsx` - Archive tab for EMPTY trades
- `components/trades/DeleteTradeDialog.tsx` - Two variants (active vs EMPTY)
- `hooks/useExecutions.ts` - useRestoreExecution mutation hook
- `types/execution.ts` - Add EDITED, IGNORED to enum; add previous_status field
- `types/trade.ts` - Add is_empty field

**API:**
- DELETE /api/v1/executions/{id} - Now returns 200 OK for soft-delete (with body), 204 for hard-delete
- POST /api/v1/executions/{id}/restore - NEW: Restore IGNORED execution to previous_status
- DELETE /api/v1/trades/{id} - Two-stage: 200 OK (archived) or 204 (permanent)
- GET /api/v1/trades - Add include_empty, only_empty query params
- GET /api/v1/trades/{id} - Include is_empty in response
- PATCH /api/v1/executions/{id} - Reject IGNORED executions (400 Bad Request)
