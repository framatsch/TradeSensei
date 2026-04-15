## Why

When users edit or delete imported executions, the system faces three critical problems:

1. **No edit tracking**: Modified executions aren't distinguished from pristine broker data, risking silent data loss during re-import
2. **Duplicate execution problem**: Deleting an imported execution destroys the link to the broker transaction, causing it to be re-imported on the next run (infinite duplicate cycle)
3. **P&L inconsistency**: Execution-level P&L from broker becomes meaningless after user modifications

The root cause is that deletion is permanent (hard delete), which breaks the transaction mapping that prevents duplicate imports.

## What Changes

**Soft-Delete Pattern for Executions:**
- Implement `IGNORED` status for soft-deleted executions (keeps transaction link intact)
- Add `previous_status` field to enable correct restoration (EDITED → IGNORED → EDITED)
- Create `deleted_execution_tombstones` table to prevent re-import of permanently deleted executions
- Implement two-stage trade deletion: active trades → EMPTY (all executions IGNORED) → permanent delete

**Execution Edit Tracking:**
- Add `EDITED` status to distinguish modified imported executions from pristine broker data
- Automatically transition IMPORTED → EDITED when user modifies price/quantity/commission
- Protect EDITED, SPLIT, MERGED executions from overwrite during re-import (with opt-in override)

**P&L Calculation Rules:**
- Execution P&L only displayed for IMPORTED executions with broker-reported data
- Trade P&L always calculated (source of truth for EDITED/MANUAL/IGNORED executions)
- Standardize decimal precision: 4 decimals for price, 2 for quantity/commission/P&L

**UI for Soft-Deleted Executions:**
- Show/hide IGNORED executions toggle in execution legs table
- Restore button for IGNORED executions (returns to previous_status)
- EMPTY trade badge and archive view
- Visual distinction (50% opacity, "Ignored" badge)

## Capabilities

### New Capabilities
- `execution-soft-delete`: Soft-delete pattern with IGNORED status and tombstone protection
- `execution-edit-tracking`: Track and protect user modifications to imported executions
- `execution-restore`: Restore soft-deleted executions to previous status
- `empty-trade-management`: Detect and handle trades with all executions ignored
- `pnl-calculation-rules`: Consistent P&L calculation logic based on execution status

### Modified Capabilities
- `execution-management`: Add EDITED and IGNORED statuses to execution lifecycle
- `trade-deletion`: Two-stage deletion (soft → hard) with tombstone creation
- `broker-import`: Skip executions with existing mappings OR tombstones
- `trade-aggregation`: Exclude IGNORED executions from P&L and position calculations
- `conflict-detection`: Auto-clear has_conflict when duplicates resolved

## Impact

**Backend:**
- `app/models/logical_execution.py` - Add EDITED and IGNORED enum values, add previous_status field
- `app/models/deleted_execution_tombstone.py` - NEW: Tombstone table for permanent deletions
- `app/services/execution.py` - Soft-delete logic, restore logic, auto-transition to EDITED
- `app/services/trade.py` - Two-stage delete, is_empty property, EMPTY trade handling
- `app/services/import_service.py` - Check tombstones, skip user-modified executions, prevent duplicates
- `app/repositories/logical_execution_repository.py` - Filter IGNORED from queries
- Database migrations:
  - Add "edited" and "ignored" to execution_status_enum
  - Add previous_status NULLABLE column to logical_executions
  - Create deleted_execution_tombstones table

**Frontend:**
- `components/trades/ExecutionRow.tsx` - Status badge, conditional P&L, restore button, 50% opacity for IGNORED
- `components/trades/ExecutionStatusBadge.tsx` - Add EDITED and IGNORED status styling
- `components/trades/ExecutionLegsTable.tsx` - Show/hide IGNORED toggle, info banner
- `components/trades/TradeCard.tsx` - EMPTY trade badge
- `hooks/useExecutions.ts` - Already refactored to force refetch
- `hooks/useTrade.ts` - Handle EMPTY trades, refetch after restore
- Import dialog - Add "Overwrite user modifications" checkbox (future enhancement)

**API:**
- PATCH /api/v1/executions/{id} - Enhanced with auto-transition to EDITED (backward compatible)
- DELETE /api/v1/executions/{id} - Now performs soft-delete (returns 200, execution becomes IGNORED)
- POST /api/v1/executions/{id}/restore - NEW: Restore IGNORED execution to previous_status
- DELETE /api/v1/trades/{id} - Two-stage: active → EMPTY (soft), EMPTY → permanent (with tombstones)
- GET /api/v1/trades - Add is_empty to response schema
- GET /api/v1/trades/{id}/executions - Include IGNORED by default (frontend filters)
