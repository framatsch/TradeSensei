## Context

After implementing soft-delete and tombstone protection (Change 1), the system has a robust mechanism to prevent infinite duplicate re-imports. However, this creates a new challenge: tombstones persist forever, and users have no way to completely reset their data.

### Current State
- Tombstones created when EMPTY trades are permanently deleted
- Tombstones prevent re-import of deleted transactions (desired behavior)
- No cleanup mechanism exists
- Manual database operations required for complete reset (dangerous, not user-accessible)

### User Scenarios Requiring Reset

**Scenario 1: Corrupted Data**
- User has imported data multiple times with various settings
- Many trades in conflicted state
- EMPTY trades scattered throughout
- User wants to "start fresh" with clean import

**Scenario 2: Testing/Development**
- Power user wants to test different import configurations
- Needs to clear data completely between tests
- Current workaround: manual database cleanup

**Scenario 3: Tombstone Interference**
- User deleted trades years ago (valid at the time)
- Now wants to re-import historical data
- Tombstones block re-import (unwanted behavior in this case)

### Existing Infrastructure
- FK constraints: trade_notes, trade_tags, trade_playbooks have ON DELETE SET NULL (from Change 1)
- DeletedExecutionTombstone table exists with indexes (from Change 1)
- Import service has transaction-based logic for rollback safety

## Goals / Non-Goals

**Goals:**
- Provide user-accessible "escape hatch" for complete data reset
- Clean up tombstones before Fresh Start import (allow re-import of previously deleted transactions)
- Preserve journaling data (orphan, don't delete) for potential re-linking (Change 3)
- Maintain import transaction safety (rollback on error)
- Clear and explicit UI warnings about data loss

**Non-Goals:**
- Auto-matching orphaned journaling data (deferred to Change 3)
- Import preview mode (show what will be imported before executing)
- Selective reset (e.g., "delete only trades from 2023")
- Backup/export before reset (user responsibility)

## Decisions

### Decision 1: Import Mode Enum (not Boolean Flags)

**Rationale:** Three distinct modes with clear semantics, not combinations of flags.

**Implementation:**
```python
class ImportMode(str, Enum):
    INCREMENTAL = "incremental"  # Add new data only, keep existing
    OVERWRITE = "overwrite"      # Replace data within date range
    FRESH_START = "fresh_start"  # Delete ALL data, then import
```

**API:**
```python
POST /api/v1/import/flex-query?mode=fresh_start
```

**Alternative considered:** Boolean flags (overwrite, delete_all)
- Rejected: Ambiguous combinations (overwrite=true, delete_all=false?)
- Rejected: Harder to extend (what if we add "merge" mode later?)

### Decision 2: Fresh Start Deletes Tombstones

**Rationale:** Fresh Start implies "truly start from scratch". Keeping tombstones would prevent re-import of previously deleted transactions, defeating the purpose.

**Implementation:**
```python
async def fresh_start_import(file, db):
    async with db.begin():  # Transaction for rollback safety
        # Order matters (FK constraints)
        await db.execute(delete(TransactionExecutionMapping))
        await db.execute(delete(DeletedExecutionTombstone))  # ← KEY
        await db.execute(delete(LogicalExecution))
        await db.execute(delete(Trade))
        # Note: BrokerRawTransaction NOT deleted (keep import history)
        
        # Journaling orphaned automatically (FK: ON DELETE SET NULL)
        
        # Now import fresh
        result = await process_import(file, db, mode=ImportMode.FRESH_START)
        
        return result
```

**Alternative considered:** Keep tombstones
- Rejected: Defeats the purpose of "Fresh Start"
- Rejected: User can't re-import historical data they previously deleted

**Alternative considered:** Ask user "Delete tombstones?"
- Rejected: Too complex, Fresh Start should be one-click

### Decision 3: Journaling Orphaned, Not Deleted

**Rationale:** TradeNotes, TradeTags, TradePlaybooks contain valuable user input. Deleting them is destructive. Orphaning preserves data for potential re-linking (Change 3).

**Implementation:**
- FK constraints already set to ON DELETE SET NULL (from Change 1)
- When Trade deleted → journaling.trade_id = NULL automatically
- No code changes needed

**Import Summary:**
```json
{
  "trades_imported": 250,
  "tombstones_cleared": 120,
  "journaling_orphaned": 35,
  "message": "Fresh start complete. 35 journal entries orphaned (can be re-linked later)."
}
```

**Alternative considered:** CASCADE DELETE journaling
- Rejected: User loses valuable notes
- Rejected: No way to recover after Fresh Start

**Alternative considered:** Checkbox "Also delete journal entries"
- Deferred: Optional enhancement, not needed for MVP

### Decision 4: BrokerRawTransaction NOT Deleted

**Rationale:** Import history is useful for debugging. BrokerRawTransaction table contains raw broker data (source of truth). Deleting it prevents inspection of what was originally imported.

**Implementation:**
```python
# Fresh Start deletes:
# - Trades
# - LogicalExecutions
# - TransactionExecutionMappings
# - DeletedExecutionTombstones

# Fresh Start DOES NOT delete:
# - BrokerRawTransactions (keep history)
# - Accounts (user data)
# - Playbooks (user-defined strategies)
```

**Why keep BrokerRawTransactions:**
- Small size (raw CSV rows)
- Useful for debugging import issues
- Allows "re-processing" same data without re-uploading file

**Alternative considered:** Delete everything
- Rejected: Loses valuable debugging information
- Rejected: User must re-upload files to re-import

### Decision 5: Fresh Start in Single Transaction

**Rationale:** All deletes and import must be atomic. If import fails after deleting data, rollback restores previous state.

**Implementation:**
```python
async def fresh_start_import(file, db):
    async with db.begin():  # ← Single transaction
        # Delete phase
        await delete_all_data(db)
        
        # Import phase
        result = await process_import(file, db)
        
        # If import fails → ROLLBACK (all deletes undone)
        # If import succeeds → COMMIT
        
        return result
```

**Alternative considered:** Delete, commit, then import
- Rejected: If import fails, user loses all data with no rollback

### Decision 6: UI Confirmation with "I Understand" Checkbox

**Rationale:** Fresh Start is destructive. Multi-step confirmation prevents accidental data loss.

**Implementation:**
```jsx
<Dialog>
  <DialogTitle>⚠️ Fresh Start Import</DialogTitle>
  <DialogContent>
    <Alert severity="error">
      This will permanently delete:
      - All trades and executions
      - All import history
      - All tombstone records
    </Alert>
    
    <Alert severity="warning">
      Journal entries will be orphaned (can be re-linked later)
    </Alert>
    
    <Checkbox>
      I understand this cannot be undone
    </Checkbox>
  </DialogContent>
  
  <DialogActions>
    <Button onClick={close}>Cancel</Button>
    <Button 
      variant="destructive" 
      disabled={!confirmed}
      onClick={startFreshImport}
    >
      Delete All & Import
    </Button>
  </DialogActions>
</Dialog>
```

**Alternative considered:** Simple confirmation dialog
- Rejected: Too easy to click through

**Alternative considered:** Type "DELETE" to confirm
- Considered overkill for MVP, but could add later

### Decision 7: Nuclear Reset as Separate Feature (Optional)

**Rationale:** Some users may want to delete all data without immediately re-importing. This is an admin/power user feature.

**Implementation:**
```python
@router.post("/system/reset", status_code=204)
async def nuclear_reset(
    confirm: bool = Body(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth)
):
    if not confirm:
        raise HTTPException(400, "Must confirm deletion")
    
    async with db.begin():
        await db.execute(delete(TransactionExecutionMapping))
        await db.execute(delete(DeletedExecutionTombstone))
        await db.execute(delete(LogicalExecution))
        await db.execute(delete(Trade))
    
    return Response(status_code=204)
```

**UI:**
```jsx
<Settings>
  <Section title="Data Management">
    <DangerZone>
      <Button variant="destructive" onClick={openNuclearDialog}>
        Reset All Data
      </Button>
      <Text>Permanently delete all trades and executions</Text>
    </DangerZone>
  </Section>
</Settings>
```

**Alternative considered:** Only allow Fresh Start (with import)
- Rejected: Power users may want to clear data without import file ready

**Decision:** Implement as optional enhancement (not required for MVP)

## Risks / Trade-offs

### Risk 1: Accidental Fresh Start triggers data loss

**Impact:** User accidentally selects Fresh Start instead of Incremental, loses all data.

**Mitigation:**
- Multi-step confirmation dialog
- "I understand" checkbox required
- Red destructive button styling
- Clear warning text about permanent deletion
- Default mode: INCREMENTAL (safe)

### Risk 2: Import fails after delete, transaction rollback fails

**Impact:** User loses all data, import doesn't succeed, rollback doesn't restore.

**Mitigation:**
- Test transaction rollback extensively
- Fresh Start requires database transaction support (PostgreSQL has this)
- Pre-flight check: Verify file is valid before deleting data
- Error handling: Clear message if rollback fails (rare)

### Risk 3: User confused about orphaned journaling

**Impact:** User doesn't understand why journal entries show up with no trade.

**Mitigation:**
- Import summary shows orphaned count
- Link to orphaned journaling management (Change 3)
- Documentation explains orphaning vs. deletion
- Banner in UI: "You have X orphaned journal entries"

### Risk 4: Fresh Start on large database is slow

**Impact:** DELETE on millions of rows takes minutes, user thinks it's frozen.

**Mitigation:**
- Progress indicator: "Deleting data... this may take a moment"
- Timeout: Set reasonable request timeout (5 minutes)
- Optimization: Use TRUNCATE instead of DELETE (faster, but can't rollback)
- Trade-off: Use DELETE for rollback safety, accept slower performance

### Risk 5: BrokerRawTransactions accumulate forever

**Impact:** Even after Fresh Start, BrokerRawTransactions remain, growing unbounded.

**Mitigation:**
- Document that BrokerRawTransactions are kept
- Future enhancement: "Delete import history" checkbox
- Quantify size: ~100 bytes per row × 10,000 rows = 1MB (negligible)

## Implementation Details

### Fresh Start Flow

```
User Flow:
1. User uploads Flex Query file
2. Selects mode: "Fresh Start"
3. Confirmation dialog appears
4. User checks "I understand" checkbox
5. User clicks "Delete All & Import"
6. Backend:
   a. Begin transaction
   b. Delete all data (trades, executions, mappings, tombstones)
   c. Process import
   d. If success → Commit
   e. If error → Rollback
7. Import summary shows:
   - Trades imported: 250
   - Tombstones cleared: 120
   - Journaling orphaned: 35
```

### API Changes

**Before (Change 1):**
```
POST /api/v1/import/flex-query
Body: FormData (file)
Query params: overwrite (bool)
```

**After (Change 2):**
```
POST /api/v1/import/flex-query
Body: FormData (file)
Query params: mode (ImportMode enum, default: "incremental")
```

**Backward Compatibility:**
- Old clients sending `overwrite=true` → Map to `mode=overwrite`
- Old clients sending `overwrite=false` → Map to `mode=incremental`
- New clients send `mode` directly

### Import Summary Schema

```python
class ImportSummary(BaseModel):
    trades_imported: int
    executions_imported: int
    mode: ImportMode
    tombstones_cleared: int = 0  # Only for FRESH_START
    journaling_orphaned: int = 0  # Only for FRESH_START
    warnings: List[str] = []
    errors: List[str] = []
```

## Migration Plan

**No database migrations required** - uses existing schema from Change 1.

### Deployment Order

1. **Backend:** Add ImportMode enum, fresh_start_import() method, API endpoint
2. **Frontend:** Add mode selection to import dialog, update API client
3. **Testing:** E2E test for Fresh Start flow
4. **Documentation:** Update import guide with Fresh Start instructions

### Rollback Plan

- Revert backend code (old clients continue to work with overwrite param)
- Revert frontend code (old UI doesn't show Fresh Start option)
- No database changes to revert

## Edge Cases

### Edge Case 1: Fresh Start with no journaling data

**Scenario:**
- User has trades but no TradeNotes/TradeTags
- Fresh Start executed
- journaling_orphaned = 0

**Result:** Normal flow, no orphaned data to worry about.

### Edge Case 2: Fresh Start fails mid-import

**Scenario:**
- Fresh Start deletes all data
- Import processes 100 trades
- CSV has invalid row, import fails
- Transaction rolls back

**Result:** All deletes undone, user's original data restored. Import summary shows error.

### Edge Case 3: User has 1000+ orphaned journal entries

**Scenario:**
- User has been journaling extensively
- Fresh Start creates 1000 orphaned entries
- User re-imports, but old journal entries don't auto-match

**Result:** User has 1000 orphaned entries. Import summary warns. Change 3 provides UI to manage.

### Edge Case 4: Concurrent import attempts

**Scenario:**
- User starts Fresh Start import
- While running, user (or another session) starts another import

**Result:** Database transaction lock prevents concurrent deletes. Second request waits or times out.

**Mitigation:** Lock import endpoint (only one import at a time per user/account).

## Open Questions

None - all design decisions resolved.
