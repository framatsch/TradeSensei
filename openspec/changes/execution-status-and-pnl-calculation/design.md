## Context

Currently, `LogicalExecution` has four status values: `IMPORTED`, `MANUAL`, `MERGED`, `SPLIT`. The system has two critical architectural gaps:

### Problem 1: No Edit Tracking
When a user edits an imported execution's price, quantity, or commission, the status remains `IMPORTED` even though the data no longer matches broker records. This creates:
- **Data integrity risk**: Re-import with overwrite silently discards user edits
- **P&L inconsistency**: Execution P&L field contains broker-reported value that's now wrong
- **No audit trail**: Can't distinguish modified executions from pristine broker data

### Problem 2: Hard Delete Causes Infinite Duplicates
When a user deletes an imported execution, the system performs a **hard delete** (physical removal from database). This destroys the `TransactionExecutionMapping` that links the execution to the broker's raw transaction. The consequences:

1. User deletes IMPORTED execution → Mapping destroyed
2. Next Flex Query import finds the transaction → No mapping exists → "New transaction!"
3. System imports it again → Duplicate execution created
4. User deletes duplicate → Mapping destroyed again
5. **Infinite cycle**: Every import recreates the duplicate

This is especially severe when user deletes IMPORTED and creates MANUAL (no transaction link), or when EMPTY trades are deleted and later re-imported.

### Existing Infrastructure
- `_re_aggregate_trade` in `execution.py` already recalculates trade P&L
- `transaction_execution_mappings` table already links executions to broker transactions
- `trade.has_conflict` flag already exists for inconsistent trades
- Conflict banner already displays in trade details when flag is true

## Goals / Non-Goals

**Goals:**
- **Solve infinite duplicate problem** via soft-delete pattern with tombstone protection
- Track execution edit history through status field (EDITED)
- Enable restoration of soft-deleted executions to correct previous state
- Prevent accidental data loss during re-import (protect EDITED/SPLIT/MERGED)
- Establish clear P&L calculation rules based on execution status
- Enforce consistent decimal precision for user input
- Provide UI for managing soft-deleted (IGNORED) executions

**Non-Goals:**
- Full audit log of what changed (just track that it changed, not what values)
- Automatic P&L recalculation on execution level (trade P&L is source of truth)
- Migration of existing data (existing executions keep their current status)
- Auto-matching orphaned journaling data (deferred to Change 3: Orphaned Journaling Management)
- Fresh Start import mode (deferred to Change 2: Fresh Start Import)

## Decisions

### Decision 1: Implement Soft-Delete Pattern with IGNORED status

**Rationale:** Hard-delete destroys the transaction mapping, causing infinite duplicate imports. Soft-delete keeps the link intact while making the execution invisible in calculations.

**Implementation:**
```python
class ExecutionStatus(str, Enum):
    IMPORTED = "imported"
    MANUAL = "manual"
    MERGED = "merged"
    SPLIT = "split"
    EDITED = "edited"      # NEW
    IGNORED = "ignored"    # NEW - soft-deleted

class LogicalExecution(Base):
    status = Column(Enum(ExecutionStatus))
    previous_status = Column(Enum(ExecutionStatus), nullable=True)  # NEW
    # ... existing fields
```

**Delete Rules by Status:**
```
IMPORTED → IGNORED (soft-delete, keeps TX link)
EDITED → IGNORED (soft-delete, keeps TX link)
SPLIT → IGNORED (soft-delete, keeps TX link)
MERGED → Hard delete (no TX link, synthetic)
MANUAL → Hard delete (no TX link, user-created)
IGNORED → 403 Forbidden (already soft-deleted, only Trade delete can hard-delete)
```

**Why MERGED/MANUAL are hard-deleted:**
- MERGED has no direct transaction link (created by merging multiple IMPORTEDs)
- Original IMPORTEDs that were merged → already IGNORED (keeps their TX links)
- MANUAL has no transaction link (user-created from scratch)
- Both are safe to hard-delete without risking re-import duplicates

**Alternative considered:** Always hard-delete
- Rejected: Destroys transaction mapping → infinite duplicate problem

**Alternative considered:** Never allow deletion
- Rejected: User needs ability to clean up mistakes

### Decision 2: Add EDITED status to ExecutionStatus enum

**Rationale:** Adding a new status value is cleaner than adding a boolean flag because:
- Status already tracks data lineage (`IMPORTED` = broker, `MANUAL` = user-created)
- `EDITED` = broker origin but user-modified fits the same pattern
- Frontend can render status badges consistently
- Import logic can filter by status directly

**Alternative considered:** Add `is_modified: bool` field
- Rejected: Duplicates information that status already conveys
- Rejected: Requires more complex queries (status + flag)

### Decision 3: Add previous_status field for correct restoration

**Rationale:** When user restores an IGNORED execution, we need to know whether it was IMPORTED, EDITED, or SPLIT before deletion. Restoring everything to IMPORTED would destroy semantic history.

**Implementation:**
```python
# On soft-delete:
execution.previous_status = execution.status  # Save current
execution.status = ExecutionStatus.IGNORED

# On restore:
execution.status = execution.previous_status  # Restore original
execution.previous_status = None  # Clear
```

**Example Flow:**
```
1. Execution starts as IMPORTED
2. User edits → status = EDITED
3. User deletes → previous_status = EDITED, status = IGNORED
4. User restores → status = EDITED (not IMPORTED!)
```

**Alternative considered:** Always restore to IMPORTED
- Rejected: Loses information that execution was modified (causes P&L display bugs)

**Alternative considered:** Separate history table
- Rejected: Over-engineering for simple use case

### Decision 4: Create deleted_execution_tombstones table

**Problem:** When EMPTY trade is permanently deleted, all IGNORED executions are hard-deleted (cascade). This destroys transaction mappings. Next import will re-import those transactions (duplicates return!).

**Solution:** Before hard-deleting IGNORED executions, create tombstone records.

**Schema:**
```python
class DeletedExecutionTombstone(Base):
    __tablename__ = "deleted_execution_tombstones"
    
    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey("broker_raw_transactions.id"), 
                           nullable=False, unique=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    deleted_at = Column(DateTime, nullable=False, server_default=func.now())
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Optional metadata for debugging
    original_trade_id = Column(Integer, nullable=True)
    symbol = Column(String, nullable=True)
    execution_date = Column(DateTime, nullable=True)
```

**Import Logic:**
```python
def should_skip_transaction(tx: BrokerRawTransaction, account_id: int) -> bool:
    # Check 1: Active mapping exists?
    if TransactionExecutionMapping.exists(transaction_id=tx.id):
        return True  # Already imported
    
    # Check 2: Tombstone exists?
    if DeletedExecutionTombstone.exists(
        transaction_id=tx.id, 
        account_id=account_id
    ):
        return True  # Was deleted, don't re-import
    
    return False  # Safe to import
```

**Trade Delete Logic:**
```python
async def delete_trade(trade_id: int, user_id: int):
    trade = await get_trade(trade_id)
    
    if not trade.is_empty:
        # Stage 1: Soft-delete all active executions
        for execution in trade.executions:
            if execution.status != ExecutionStatus.IGNORED:
                execution.previous_status = execution.status
                execution.status = ExecutionStatus.IGNORED
        # Trade is now EMPTY, moved to archive
        return {"status": "archived", "message": "Trade moved to archive"}
    
    else:
        # Stage 2: Create tombstones, then hard-delete
        for execution in trade.executions:  # All are IGNORED
            if execution.transaction_id:
                await create_tombstone(
                    transaction_id=execution.transaction_id,
                    account_id=trade.account_id,
                    deleted_by=user_id,
                    original_trade_id=trade.id,
                    symbol=trade.symbol,
                    execution_date=execution.timestamp
                )
        
        # Hard delete (CASCADE removes executions + mappings)
        await db.delete(trade)
        return {"status": "deleted", "message": "Trade permanently deleted"}
```

**Tombstone Cleanup (deferred to Change 2: Fresh Start Import):**
- Fresh Start import mode will DELETE FROM deleted_execution_tombstones
- Allows user to re-import everything from scratch
- Without this, tombstones would block re-import forever

**Alternative considered:** Keep orphaned mappings (execution_id = NULL)
- Rejected: Database pollution, no way to distinguish "deleted" from "corrupted data"

**Alternative considered:** Never allow EMPTY trade deletion
- Rejected: User needs escape hatch for corrupted data

**Alternative considered:** Tombstone with TTL (auto-expire after 2 years)
- Rejected: Arbitrary timeframe, user might want permanent protection

### Decision 5: Auto-transition IMPORTED → EDITED on update

**Implementation:** In `ExecutionService.update_execution()`:
```python
if execution.status == ExecutionStatus.IMPORTED:
    update_data["status"] = ExecutionStatus.EDITED
```

**Rationale:** 
- Automatic = zero user friction, can't forget to set it
- Only applies to IMPORTED (MANUAL/MERGED/SPLIT stay unchanged)
- Irreversible by design (once edited, can't un-edit)

**Alternative considered:** Require explicit status in update payload
- Rejected: Too easy to forget, API clients must know internal rules

### Decision 6: Trade.is_empty as computed property (not DB field)

**Rationale:** EMPTY status is derived from execution statuses. Storing it in DB risks inconsistency.

**Implementation:**
```python
class Trade(Base):
    # ... existing fields
    
    @property
    def is_empty(self) -> bool:
        """Trade is empty when all executions are IGNORED."""
        if not self.executions:
            return True
        return all(e.status == ExecutionStatus.IGNORED for e in self.executions)
```

**Aggregation Logic:**
```python
# In TradeService.get_performance_metrics()
active_trades = [t for t in trades if not t.is_empty]
# Calculate metrics only on active_trades
```

**API Response:**
```json
{
  "id": 123,
  "symbol": "AAPL",
  "is_empty": true,
  "executions": [
    {"id": 1, "status": "ignored", ...},
    {"id": 2, "status": "ignored", ...}
  ]
}
```

**Alternative considered:** Add `status` field to Trade table
- Rejected: Requires DB migration, risk of status/executions mismatch

**Alternative considered:** Aggregate query (COUNT active executions)
- Rejected: Performance overhead, still need to load executions anyway

### Decision 7: EMPTY trade handling - no auto-delete

**Rationale:** If EMPTY trades auto-delete, user loses ability to restore IGNORED executions (can't find the trade anymore).

**Implementation:**
```python
# Trade remains in database with is_empty=true
# UI shows in separate "Archive" tab or filters out by default

# API allows filtering:
GET /api/v1/trades?include_empty=false  # Default
GET /api/v1/trades?include_empty=true&only_empty=true  # Archive view
```

**UI Behavior:**
- Default trade list: `include_empty=false` (EMPTY trades hidden)
- Archive tab: `only_empty=true` (shows only EMPTY trades)
- EMPTY trade detail page: Shows all IGNORED executions (with restore buttons)
- Performance metrics: Exclude EMPTY trades (same as IGNORED executions)

**Alternative considered:** Auto-delete EMPTY trades
- Rejected: User can't restore executions if trade is gone

**Alternative considered:** Soft-delete trades (trade.status = DELETED)
- Rejected: Adds complexity, computed property is cleaner

### Decision 8: Execution P&L display rules

**Rule:**
```
if execution.status == IMPORTED AND execution.pnl != null:
    Display: execution.pnl (broker truth)
else:
    Display: "—" (calculated at trade level)
```

**Rationale:**
- Execution P&L only meaningful for pristine broker data
- Edited/manual executions: can't recalculate execution P&L without full FIFO context
- Trade P&L (aggregated) is always the source of truth

**Alternative considered:** Recalculate execution P&L on edit
- Rejected: Execution might partially close multiple opening legs (FIFO)
- Rejected: Can't replicate broker's exact matching logic

### Decision 9: Decimal precision standards

**Rule:**
- **Price**: 4 decimals (options, penny stocks need precision)
- **Quantity**: 2 decimals (fractional shares)
- **Commission**: 2 decimals (currency precision)
- **P&L**: 2 decimals (currency precision)

**Rationale:**
- Matches broker data precision (IBKR Flex Query provides 4 decimals for price)
- 4 decimals for price: `$1.2375` for options, `$0.0025` for penny stocks
- 2 decimals for quantity: `50.25` shares (fractional trading)

**Implementation:**
- Frontend: `<input type="number" step="0.0001">` for price, `step="0.01"` for others
- Backend: Already `Numeric(20, 10)` - validation ensures max 4/2 decimals
- Display: `.toFixed(4)` for price, `.toFixed(2)` for others

### Decision 10: Re-import overwrite protection with duplicate prevention

**Default behavior:** Skip EDITED executions during overwrite AND skip corresponding broker transactions

**UI:** Import dialog checkbox: "Overwrite edited executions" (unchecked by default)

**Rationale:**
- Safe by default (protect user data)
- Prevents duplicate executions: if we skip EDITED but re-import its broker transaction, we'd have TWO executions for the same data
- Explicit opt-in to overwrite (user knows what they're doing)

**Implementation:**
```python
# ImportService._clear_existing_data()
if not overwrite_edited:
    query = query.where(LogicalExecution.status != ExecutionStatus.EDITED)

# ImportService._process_broker_transaction()
# Check if transaction already linked to EDITED execution
edited_executions = session.query(LogicalExecution).join(
    transaction_execution_mappings
).filter(
    transaction_execution_mappings.c.transaction_id == broker_tx.id,
    LogicalExecution.status == ExecutionStatus.EDITED
).all()

if edited_executions and not overwrite_edited:
    # Skip this transaction (already represented by EDITED execution)
    continue
```

**Alternative considered:** Always protect EDITED (no override)
- Rejected: User may genuinely want to reset to broker data
- Rejected: Forces manual deletion if user wants fresh import

**Alternative considered:** Only skip EDITED, allow duplicate imports
- Rejected: Creates duplicate executions in trade
- Rejected: P&L would be double-counted
- Rejected: User must manually clean up duplicates

### Decision 11: Corporate Action status inheritance

**Problem:** When stock split occurs on IGNORED execution, should the new split execution also be IGNORED?

**Answer:** **Yes**. Status must be inherited.

**Implementation:**
```python
# In Corporate Action Processor
def apply_split(execution: LogicalExecution, split_ratio: float):
    new_execution = LogicalExecution(
        quantity=execution.quantity * split_ratio,
        price=execution.price / split_ratio,
        status=execution.status,  # ← INHERIT status
        previous_status=execution.previous_status,  # ← Also inherit
        # ... other fields
    )
    
    # Original execution behavior depends on status:
    if execution.status == ExecutionStatus.IGNORED:
        # Keep as IGNORED (already soft-deleted)
        pass
    else:
        # Mark original as SPLIT (normal flow)
        execution.status = ExecutionStatus.SPLIT
```

**Why:** If IGNORED execution gets split and new execution is IMPORTED, we have duplicate problem again:
1. User had IMPORTED, deleted it → IGNORED
2. Stock splits 2:1
3. New execution created as IMPORTED (if not inherited)
4. Now trade has IGNORED (200 shares) + IMPORTED (200 shares) → duplicate!

**Special Case: Split on MERGED execution:**
```python
# MERGED execution after split:
# Option A: Keep as MERGED? (wrong, it's been split)
# Option B: Mark as SPLIT? (correct)

if execution.status == ExecutionStatus.MERGED:
    # Original MERGED → becomes IGNORED (like user-merge flow)
    execution.previous_status = execution.status
    execution.status = ExecutionStatus.IGNORED
    
    # New split executions → SPLIT (not MERGED)
    new_execution.status = ExecutionStatus.SPLIT
```

**Alternative considered:** Don't inherit status
- Rejected: Creates duplicate executions after corporate actions

### Decision 12: Journaling data on trade delete - SET NULL (deferred handling)

**Problem:** When trade is deleted (EMPTY → permanent), what happens to `TradeNote`, `TradeTag`, `TradePlaybook`?

**Decision:** **SET NULL** (orphan journaling data, handle in Change 3)

**DB Constraints:**
```sql
-- In trade_notes, trade_tags, trade_playbooks:
trade_id INTEGER REFERENCES trades(id) ON DELETE SET NULL
```

**Behavior:**
```
1. Trade deleted → trade_id = NULL on all journaling records
2. Journaling data remains in database (orphaned)
3. Change 3 (Orphaned Journaling Management) will:
   - Auto-match orphaned notes to new trades (heuristic: symbol + time window)
   - Provide UI to manually link orphaned notes
   - Allow bulk delete of orphaned notes
```

**Why defer to Change 3:**
- Change 1 scope: Execution soft-delete & conflict resolution
- Change 3 scope: Journaling management & auto-matching
- Separation of concerns: execution lifecycle vs. journaling lifecycle

**Alternative considered:** CASCADE DELETE (delete journaling with trade)
- Rejected: User loses valuable notes when cleaning up executions

**Alternative considered:** RESTRICT (can't delete trade if journaling exists)
- Rejected: User stuck with undeletable EMPTY trades

**Alternative considered:** Store symbol/date in TradeNote for auto-matching
- Deferred to Change 3 (will add these fields when implementing auto-matching)

## Risks / Trade-offs

### Risk 1: Tombstones accumulate forever in database
**Impact:** Database grows with deleted execution records that are never cleaned up.

**Mitigation:**
- Tombstones are small (single integer FK per deleted execution)
- Indexed on transaction_id for fast lookup
- Future: Change 2 (Fresh Start Import) will provide cleanup mechanism
- Future: Admin tool to purge tombstones older than X years

**Quantification:** 1000 trades × 3 executions × 4 bytes = 12KB per 1000 trades. Negligible.

### Risk 2: User confused by EMPTY trades in archive
**Impact:** User doesn't understand why trade is empty or how to restore executions.

**Mitigation:**
- Clear UI banner: "This trade is empty. All executions have been deleted. Restore executions to reactivate."
- Archive tab clearly separated from active trades
- Restore button prominently displayed on each IGNORED execution
- Help tooltip explains EMPTY status

### Risk 3: Execution P&L shows "—" confuses users
**Impact:** User doesn't understand why P&L is missing.

**Mitigation:** 
- Add tooltip on "—" explaining "P&L calculated at trade level"
- Trade P&L always visible and prominent
- Documentation explains EDITED executions don't have execution-level P&L

### Risk 4: User edits execution then re-imports, forgets about edits
**Impact:** User confused why import didn't update certain executions.

**Mitigation:** 
- Import summary shows "X user-modified executions skipped"
- Status badge in ExecutionRow is visually distinct (amber for EDITED)
- Import summary links to affected trades

### Risk 5: Database migration fails on enum constraint
**Impact:** Deployment blocked by failed migration.

**Mitigation:** 
- Alembic migration adds enum values without data migration
- Existing rows keep current status (no UPDATE needed)
- Test migration on staging with production data clone first
- Rollback plan: Enum values can't be removed (Postgres limitation), but code can ignore them

### Risk 6: Frontend number input allows arbitrary precision
**Impact:** User enters 5+ decimals, gets validation error, frustrated.

**Mitigation:**
- HTML5 `step` attribute enforces client-side (price: 0.0001, others: 0.01)
- Backend validation rejects excess decimals with clear error message
- Display formatting normalizes on save (.toFixed())

### Risk 7: Corporate action on IGNORED execution creates confusion
**Impact:** User sees split applied to "deleted" execution.

**Mitigation:**
- Corporate action processor inherits IGNORED status (new execution also IGNORED)
- Both remain hidden from UI (unless "Show ignored" toggled)
- Consistent behavior: IGNORED stays IGNORED through corporate actions

### Risk 8: Restore execution in wrong trade context
**Impact:** IGNORED execution's trade was deleted, restore fails or restores to wrong trade.

**Mitigation:**
- IGNORED executions retain trade_id (not NULL)
- Restore only possible if parent trade exists
- If trade deleted (EMPTY → permanent), IGNORED executions cascade deleted (can't restore)
- UI: Restore button disabled if trade no longer exists (shouldn't happen)

## Edge Cases & Complex Scenarios

### Edge Case 1: User deletes IMPORTED, creates MANUAL → Re-import creates duplicate

**Scenario:**
```
1. Trade has IMPORTED execution (TX123, 100 shares AAPL)
2. User deletes IMPORTED → becomes IGNORED (TX123 link intact)
3. User creates MANUAL execution (100 shares AAPL, no TX link)
4. Trade has: IGNORED + MANUAL (both 100 shares)
5. Re-import finds TX123:
   - Mapping exists? YES (IGNORED execution still has it)
   - Skip TX123 ✅
6. Result: Only MANUAL execution visible (correct)
```

**Alternate scenario (worse):**
```
1. Trade has IMPORTED execution (TX123, 100 shares AAPL)
2. User HARD-DELETES execution (if we didn't implement soft-delete)
3. User creates MANUAL execution (100 shares AAPL, no TX link)
4. Trade has: MANUAL (100 shares)
5. Re-import finds TX123:
   - Mapping exists? NO (destroyed by hard-delete)
   - Import TX123 as new IMPORTED ❌
6. Result: MANUAL + IMPORTED (duplicate!) → has_conflict = true
7. Next re-import: TX123 has mapping again → skip
8. Duplicate persists until manual cleanup
```

**Why soft-delete solves this:** IGNORED execution keeps TX123 mapping → prevents re-import even though user created MANUAL.

### Edge Case 2: SPLIT executions block re-import

**Scenario:**
```
1. IMPORTED execution: 100 shares, TX123
2. User splits into: 50 shares (SPLIT) + 50 shares (SPLIT)
3. Both SPLIT executions link to TX123 (via original mapping)
4. Re-import finds TX123:
   - Mapping exists? YES (2 SPLIT executions have it)
   - Skip TX123 ✅
5. Result: SPLIT executions protected
```

**If user deletes one SPLIT:**
```
1. User deletes first SPLIT (50 shares) → becomes IGNORED
2. Trade has: IGNORED (50) + SPLIT (50)
3. Re-import finds TX123:
   - Mapping exists? YES (IGNORED still has it)
   - Skip TX123 ✅
4. Result: Only second SPLIT (50) visible
```

### Edge Case 3: MERGED execution deleted, originals re-import

**Scenario:**
```
1. User has 3 IMPORTED: TX123 (50), TX124 (50), TX125 (50)
2. User merges into 1 MERGED (150 shares)
   - Original 3 IMPORTED → become IGNORED
   - New MERGED created (has NO direct TX link)
3. User deletes MERGED → hard delete (no TX to protect)
4. Trade has: 3 IGNORED executions (TX123, TX124, TX125 links intact)
5. Re-import finds TX123, TX124, TX125:
   - Mappings exist? YES (IGNORED executions have them)
   - Skip all 3 ✅
6. Result: Trade is EMPTY (all executions IGNORED)
```

**Why MERGED can be hard-deleted:** Original executions (IGNORED) keep the TX mappings.

### Edge Case 4: Corporate action on IGNORED execution

**Scenario:**
```
1. IMPORTED execution: 100 shares AAPL, TX123
2. User deletes → IGNORED (100 shares, TX123 link intact)
3. AAPL splits 2:1
4. Corporate action processor:
   - Creates new execution: 200 shares, status = IGNORED (inherited)
   - Original IGNORED: stays IGNORED
5. Trade has: 2 IGNORED executions (100 old + 200 new)
6. Re-import finds TX123:
   - Mapping exists? YES (old IGNORED has it)
   - Skip TX123 ✅
```

**If status wasn't inherited:**
```
4. New execution: 200 shares, status = IMPORTED (wrong!)
5. Trade has: IGNORED (100) + IMPORTED (200) → visible duplicate
6. has_conflict = true
```

### Edge Case 5: EMPTY trade deletion and re-import

**Scenario:**
```
1. Trade has 3 executions: TX123, TX124, TX125
2. User deletes all 3 → all become IGNORED
3. Trade is EMPTY (is_empty = true)
4. User deletes trade (permanent delete):
   - Create tombstones for TX123, TX124, TX125
   - Hard-delete trade + IGNORED executions + mappings
5. Re-import finds TX123, TX124, TX125:
   - Mappings exist? NO (deleted)
   - Tombstones exist? YES ✅
   - Skip all 3 ✅
6. Result: No trades created (correct)
```

**Without tombstones:**
```
5. Re-import finds TX123, TX124, TX125:
   - Mappings exist? NO (deleted)
   - Tombstones exist? NO (not implemented)
   - Import all 3 ❌
6. Result: Trade recreated (user's deletion undone!)
7. Infinite cycle: User deletes → re-import recreates
```

### Edge Case 6: Restore execution, trade no longer EMPTY

**Scenario:**
```
1. Trade has 2 executions: both IGNORED
2. Trade.is_empty = true (computed property)
3. User restores one IGNORED execution
4. Execution: status = previous_status (e.g., IMPORTED)
5. Trade.is_empty = false (computed property auto-updates)
6. Trade moves from archive to active list (frontend filter)
```

**No manual flag update needed:** `is_empty` is computed, not stored.

### Edge Case 7: has_conflict auto-clear after resolution

**Scenario:**
```
1. Trade has MANUAL (100 shares) + IMPORTED (100 shares) → duplicate
2. System sets has_conflict = true
3. User deletes MANUAL → hard delete (no TX link)
4. Trade has: IMPORTED (100 shares)
5. System rechecks conflict:
   - Active executions: 1 (IMPORTED)
   - Duplicate TX links? NO
   - Duplicate timestamps? NO
   - has_conflict = false ✅
6. Conflict banner disappears
```

**Alternate resolution:**
```
3. User deletes IMPORTED → becomes IGNORED
4. Trade has: MANUAL (100 visible) + IGNORED (100 hidden)
5. System rechecks conflict:
   - Active executions: 1 (MANUAL)
   - Duplicate TX links? NO (IGNORED excluded from conflict check)
   - has_conflict = false ✅
```

### Edge Case 8: Restore creates conflict

**Scenario:**
```
1. Trade has MANUAL (100 shares) + IGNORED (100 shares, TX123)
2. has_conflict = false (only 1 active execution)
3. User restores IGNORED → becomes IMPORTED
4. Trade has: MANUAL (100) + IMPORTED (100) → duplicate
5. System rechecks conflict after restore:
   - Active executions: 2
   - Duplicate timestamps/quantities? YES
   - has_conflict = true ✅
6. Conflict banner appears
```

## Migration Plan

### Phase 1: Database Schema (Deploy First)

**Migration 001: Add enum values**
```sql
-- Alembic migration
ALTER TYPE execution_status_enum ADD VALUE 'edited';
ALTER TYPE execution_status_enum ADD VALUE 'ignored';
```

**Migration 002: Add previous_status column**
```sql
ALTER TABLE logical_executions 
ADD COLUMN previous_status execution_status_enum NULL;

-- No default value, NULL for all existing rows
```

**Migration 003: Create tombstone table**
```sql
CREATE TABLE deleted_execution_tombstones (
    id SERIAL PRIMARY KEY,
    transaction_id INTEGER NOT NULL REFERENCES broker_raw_transactions(id),
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    deleted_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_by INTEGER REFERENCES users(id),
    original_trade_id INTEGER,
    symbol VARCHAR(20),
    execution_date TIMESTAMP,
    
    UNIQUE(transaction_id)  -- One tombstone per transaction
);

CREATE INDEX idx_tombstone_tx_account 
ON deleted_execution_tombstones(transaction_id, account_id);

CREATE INDEX idx_tombstone_deleted_at 
ON deleted_execution_tombstones(deleted_at);
```

**Migration 004: Update FK constraints for journaling**
```sql
-- Change ON DELETE CASCADE to ON DELETE SET NULL
ALTER TABLE trade_notes 
DROP CONSTRAINT trade_notes_trade_id_fkey,
ADD CONSTRAINT trade_notes_trade_id_fkey 
    FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE SET NULL;

-- Repeat for trade_tags, trade_playbooks
```

**Rollback Plan:**
- Can't remove enum values (Postgres limitation)
- Can drop previous_status column (no business logic depends on it for existing data)
- Can drop deleted_execution_tombstones table (empty until code deployed)
- Can revert FK constraints (journaling won't be orphaned if code not deployed)

### Phase 2: Backend Code (Deploy Second)

**Deploy Order:**
1. Models: ExecutionStatus enum, DeletedExecutionTombstone model, previous_status field
2. Repositories: Filter IGNORED from queries, tombstone queries
3. Services: Soft-delete logic, restore logic, auto-transition IMPORTED→EDITED, tombstone creation
4. Import Service: Check tombstones, skip user-modified executions
5. Aggregator: Exclude IGNORED from calculations
6. API: DELETE soft-delete, POST restore endpoint, Trade DELETE two-stage logic

**Testing Before Deploy:**
- All unit tests pass (execution service, trade service, import service)
- All integration tests pass (with test database)
- Staging deployment with production data clone

**Rollback Plan:**
- Revert to previous code version
- Existing EDITED/IGNORED executions: Code falls back to treating as IMPORTED (safe, no data loss)
- Tombstones: Ignored by old code (no impact)

### Phase 3: Frontend Code (Deploy Third)

**Deploy Order:**
1. Types: Update ExecutionStatus enum (add EDITED, IGNORED)
2. Components: ExecutionStatusBadge styling, show/hide toggle, restore button
3. Hooks: API client methods for restore endpoint
4. Pages: Trade detail with EMPTY badge, archive view

**Testing Before Deploy:**
- E2E tests pass (execution edit, soft-delete, restore, EMPTY trade)
- Visual regression tests (screenshot comparison)
- Accessibility tests (keyboard navigation, screen reader)

**Rollback Plan:**
- Revert to previous frontend version
- Backend still works (API unchanged, only enhanced)
- Users see old UI, but data protected by backend logic

### Phase 4: Import Dialog Enhancement (Optional, Later)

**Future Enhancement:**
- Add "Overwrite user modifications" checkbox to import dialog
- Add import summary showing skipped executions

**Not blocking for Phase 1-3 deployment.**

### Deployment Checklist

**Pre-Deployment:**
- [ ] All migrations tested on staging with production data clone
- [ ] All unit tests pass (≥80% coverage)
- [ ] All integration tests pass
- [ ] All E2E tests pass
- [ ] Code review approved (code-reviewer agent)
- [ ] Manual QA on staging (smoke test all scenarios)

**Deployment:**
- [ ] Deploy Phase 1 (migrations) - Wait 10 minutes, monitor errors
- [ ] Deploy Phase 2 (backend) - Wait 10 minutes, monitor logs
- [ ] Deploy Phase 3 (frontend) - Monitor user sessions
- [ ] Smoke test in production: Create trade, edit execution, verify EDITED status

**Post-Deployment:**
- [ ] Monitor error rates (Sentry/logs)
- [ ] Monitor database for new EDITED/IGNORED executions
- [ ] Monitor import jobs (verify tombstone checks work)
- [ ] User feedback (check for confusion about IGNORED executions)

**Rollback Triggers:**
- Migration fails (Phase 1): Halt deployment, fix migration, retry
- Backend errors spike >5% (Phase 2): Rollback backend code
- Frontend errors spike >5% (Phase 3): Rollback frontend code
- Import jobs fail >10% (Phase 2): Rollback backend, investigate tombstone logic

## Open Questions

None - all design decisions resolved.
