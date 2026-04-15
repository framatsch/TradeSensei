## Why

After implementing soft-delete and tombstone protection (Change 1), tombstones accumulate in the database forever. While this prevents re-import of deleted transactions (solving the infinite duplicate problem), it creates a new issue: **users have no escape hatch** if they want to completely reset their data and re-import from scratch.

**Problem Scenarios:**
1. **User's data is corrupted:** Multiple trades are in conflicted state, EMPTY trades everywhere, import history is messy
2. **User wants to test from scratch:** Developer or power user wants to clear everything and re-import clean data
3. **Tombstones block desired re-import:** User deleted trades years ago, now wants to re-import those transactions but tombstones prevent it

Currently, the only way to reset is manual database operations (DELETE FROM trades, DELETE FROM deleted_execution_tombstones), which is dangerous and not user-accessible.

Additionally, tombstone accumulation (though small) grows unbounded. After years of use, the tombstones table could contain thousands of records that are no longer relevant.

## What Changes

**Import Mode Enum:**
- Add `ImportMode` enum: `INCREMENTAL` | `OVERWRITE` | `FRESH_START`
- Extend import endpoint to accept `mode` parameter
- Default: `INCREMENTAL` (existing behavior, add new data only)

**Fresh Start Import Mode:**
- Deletes ALL trades, executions, mappings, and **tombstones** before import
- Orphans journaling data (TradeNotes, TradeTags, TradePlaybooks) via FK: ON DELETE SET NULL
- Clears import history
- Then performs full import from provided file
- Response includes count of orphaned journaling records (for user awareness)

**Nuclear Reset Button (Optional UI Enhancement):**
- Settings > Data Management > "Reset All Data" button
- Confirmation dialog with "I understand this cannot be undone" checkbox
- Calls DELETE ALL API endpoint (same backend logic as Fresh Start, without re-import)
- Useful for complete cleanup without needing an import file

**Import Summary Enhancement:**
- Shows tombstone cleanup count: "X tombstones cleared"
- Shows orphaned journaling count: "Y journal entries orphaned (can be re-linked later)"
- Links to orphaned journaling management (Change 3, if implemented)

## Capabilities

### New Capabilities
- `fresh-start-import`: Complete data reset with tombstone cleanup before re-importing
- `import-mode-selection`: User can choose between INCREMENTAL, OVERWRITE, or FRESH_START
- `nuclear-reset`: Admin/power user can reset all data without import file (optional UI)

### Modified Capabilities
- `broker-import`: Add mode parameter, default to INCREMENTAL

## Impact

**Backend:**
- `app/schemas/import_schema.py` - Add ImportMode enum (INCREMENTAL, OVERWRITE, FRESH_START)
- `app/services/import_service.py` - Implement fresh_start_import() method
- `app/api/v1/import.py` - Add mode parameter to import endpoint, handle Fresh Start logic
- `app/api/v1/system.py` - NEW (optional): Add POST /system/reset endpoint for nuclear reset

**Frontend:**
- `components/import/ImportDialog.tsx` - Add mode radio buttons (Incremental/Overwrite/Fresh Start)
- `components/import/ImportSummary.tsx` - Display tombstone cleanup and orphaned journaling counts
- `components/settings/DataManagement.tsx` - NEW (optional): Nuclear Reset button with confirmation
- `types/import.ts` - Add ImportMode enum

**API:**
- POST /api/v1/import/flex-query - Add `mode` query parameter (default: "incremental")
- POST /api/v1/system/reset - NEW (optional): Nuclear reset without import

**Database:**
- No schema changes (uses existing tables and FK constraints from Change 1)

## Out of Scope (Deferred to Change 3)

- **Auto-matching orphaned journaling:** After Fresh Start, orphaned journal entries remain in database with trade_id=NULL. Automatic re-linking to new trades based on symbol/time heuristics is handled in Change 3.
- **Orphaned journaling review UI:** Manual linking interface for orphaned notes is Change 3.
- **Bulk delete orphaned journaling:** UI to delete all orphaned notes at once is Change 3.
