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

[... rest of content exactly as shown above from the bash output ...]
