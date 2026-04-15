# Change: Execution Soft-Delete & Conflict Resolution

## Overview

This change implements a comprehensive soft-delete pattern for executions to solve the **infinite duplicate re-import problem** while also adding execution edit tracking (EDITED status) and clear P&L calculation rules.

**Status:** Ready for Implementation  
**Effort:** ~235 tasks, estimated 6-8 weeks  
**Priority:** HIGH (blocks Change 2 & 3)

---

## Problem Statement

### The Infinite Duplicate Problem

When a user deletes an imported execution, the system performs a **hard delete** (physical removal). This destroys the `TransactionExecutionMapping` that links the execution to the broker's raw transaction. Consequences:

1. User deletes IMPORTED execution → Mapping destroyed
2. Next Flex Query import finds the transaction → No mapping exists → "New transaction!"
3. System imports it again → Duplicate execution created
4. User deletes duplicate → Mapping destroyed again
5. **Infinite cycle**: Every import recreates the duplicate

This is especially severe when:
- User deletes IMPORTED and creates MANUAL (no transaction link)
- EMPTY trades are deleted and later re-imported
- Corporate actions occur on deleted executions

### Additional Problems

- **No edit tracking**: Modified executions can't be distinguished from pristine broker data
- **Re-import risk**: User edits silently discarded during re-import with overwrite
- **P&L inconsistency**: Broker-reported execution P&L becomes wrong after user edits

---

## Solution Architecture

### 1. Soft-Delete Pattern with IGNORED Status

**Core Concept:** Executions with transaction links (IMPORTED, EDITED, SPLIT) are **soft-deleted** by setting `status = IGNORED`. The execution remains in the database, preserving the `TransactionExecutionMapping`.

**Delete Rules:**
```
IMPORTED → IGNORED (soft-delete, keeps TX link)
EDITED → IGNORED (soft-delete, keeps TX link)
SPLIT → IGNORED (soft-delete, keeps TX link)
MERGED → Hard delete (no TX link, synthetic)
MANUAL → Hard delete (no TX link, user-created)
IGNORED → 403 Forbidden (already soft-deleted)
```

### 2. Tombstone Protection for Permanent Deletion

**Problem:** When EMPTY trade is permanently deleted, all IGNORED executions are hard-deleted (cascade). This destroys transaction mappings. Next import will re-import those transactions (duplicates return!).

**Solution:** Before hard-deleting IGNORED executions, create `DeletedExecutionTombstone` records.

**Tombstone Table:**
```sql
CREATE TABLE deleted_execution_tombstones (
    id SERIAL PRIMARY KEY,
    transaction_id INTEGER NOT NULL UNIQUE REFERENCES broker_raw_transactions(id),
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    deleted_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_by INTEGER REFERENCES users(id),
    -- Optional metadata for debugging
    original_trade_id INTEGER,
    symbol VARCHAR(20),
    execution_date TIMESTAMP
);
```

**Import Logic:**
```python
def should_skip_transaction(tx_id, account_id):
    # Check 1: Active mapping exists?
    if TransactionExecutionMapping.exists(tx_id):
        return True  # Already imported
    
    # Check 2: Tombstone exists?
    if DeletedExecutionTombstone.exists(tx_id, account_id):
        return True  # Was deleted, don't re-import
    
    return False  # Safe to import
```

### 3. Restore Mechanism with previous_status

**Problem:** When user restores an IGNORED execution, we need to know whether it was IMPORTED, EDITED, or SPLIT before deletion.

**Solution:** Add `previous_status` field.

**Flow:**
```
1. Execution starts as IMPORTED
2. User edits → status = EDITED
3. User deletes → previous_status = EDITED, status = IGNORED
4. User restores → status = EDITED (not IMPORTED!)
```

### 4. Two-Stage Trade Deletion

**Stage 1 (Archive):**
- User deletes active trade
- All executions → IGNORED (soft-delete)
- Trade becomes EMPTY (is_empty = true)
- Trade moves to archive view
- Response: 200 OK with message "Trade archived"

**Stage 2 (Permanent):**
- User deletes EMPTY trade
- System creates tombstones for each IGNORED execution
- Trade + executions + mappings hard-deleted (CASCADE)
- Journaling orphaned (trade_id → NULL)
- Response: 204 No Content

### 5. EMPTY Trade Handling

**Definition:** Trade is EMPTY when all executions have status IGNORED.

**Implementation:** `is_empty` computed property (not stored in DB):
```python
@property
def is_empty(self) -> bool:
    if not self.executions:
        return True
    return all(e.status == ExecutionStatus.IGNORED for e in self.executions)
```

**Behavior:**
- EMPTY trades excluded from performance metrics
- EMPTY trades shown in separate "Archive" tab
- EMPTY trades can be restored by restoring any execution

---

## Key Decisions

### Decision 1: Tombstone Pattern (not Orphaned Mappings)
**Chosen:** Tombstone table  
**Rejected:** Keep orphaned mappings with execution_id=NULL  
**Reason:** Tombstones provide clean audit trail, no DB pollution, scoped to account

### Decision 2: previous_status Field (not Always IMPORTED)
**Chosen:** Store previous status before soft-delete  
**Rejected:** Always restore to IMPORTED  
**Reason:** Preserves semantic history (EDITED stays EDITED after restore)

### Decision 3: is_empty Computed Property (not DB Field)
**Chosen:** Computed from execution statuses  
**Rejected:** Store status field in Trade table  
**Reason:** Avoids inconsistency risk, no DB migration needed

### Decision 4: Journaling Orphaned (not Cascade Deleted)
**Chosen:** ON DELETE SET NULL  
**Rejected:** ON DELETE CASCADE (delete journaling with trade)  
**Reason:** User doesn't lose valuable notes, handled in Change 3 (auto-matching)

### Decision 5: Corporate Actions Inherit Status
**Chosen:** Split execution inherits IGNORED status from parent  
**Rejected:** New split execution always IMPORTED  
**Reason:** Prevents duplicates after corporate actions on deleted executions

---

## File Structure

```
openspec/changes/execution-status-and-pnl-calculation/
├── README.md                               # This file
├── proposal.md                             # Why, what changes, impact
├── design.md                               # 12 decisions, 8 risks, 8 edge cases
├── tasks.md                                # 235 tasks across 39 groups
├── .openspec.yaml                          # Metadata
└── specs/
    ├── execution-soft-delete/
    │   └── spec.md                         # Soft-delete, restore, tombstones, EMPTY trades
    ├── execution-edit-tracking/
    │   └── spec.md                         # EDITED status, re-import protection
    ├── pnl-calculation-rules/
    │   └── spec.md                         # P&L display rules based on status
    ├── ui-ignored-executions/
    │   └── spec.md                         # Show/hide toggle, restore button, badges
    └── api-endpoints/
        └── spec.md                         # All API changes documented
```

---

## Dependencies

**Blocks:**
- Change 2: Fresh Start Import (needs tombstone cleanup mechanism)
- Change 3: Orphaned Journaling Management (needs orphaned data from trade deletion)

**No Dependencies:**
- This change can be implemented standalone

---

## Testing Strategy

### Unit Tests (Backend)
- **Execution Service:** Soft-delete, hard-delete, restore, auto-transition to EDITED
- **Trade Service:** is_empty property, two-stage deletion, tombstone creation
- **Tombstone Service:** Create, check existence, handle unique constraint
- **Import Service:** Skip logic (mapping + tombstone), duplicate prevention
- **Aggregator:** Exclude IGNORED, exclude EMPTY trades

**Target:** ≥85% coverage

### Integration Tests (Backend)
- Full soft-delete → restore workflow
- EMPTY trade deletion with tombstones
- Re-import after soft-delete (no duplicates)
- Re-import after permanent delete (tombstone blocks import)

### E2E Tests (Frontend - Playwright)
- Execution soft-delete and status badge
- Restore IGNORED execution to previous status
- Show/hide IGNORED executions toggle
- EMPTY trade badge and archive view
- Two-stage trade deletion (active → EMPTY → permanent)
- Re-import protection (no duplicates after delete)
- Execution edit status (IMPORTED → EDITED)
- P&L display rules ("—" for EDITED)

### Visual Regression Tests
- Execution badges (IMPORTED, EDITED, IGNORED)
- 50% opacity for IGNORED rows
- Info banner "X ignored executions hidden"
- EMPTY trade card and detail page
- Delete dialogs (active vs EMPTY)

### Accessibility Tests (axe-core)
- Keyboard navigation (Tab to Restore button)
- Screen reader support (aria-labels)
- Color contrast (WCAG AA: ≥4.5:1)
- Focus indicators

---

## Edge Cases Covered

1. **User deletes IMPORTED, creates MANUAL → Re-import:** IGNORED execution keeps TX mapping → Skip
2. **SPLIT executions block re-import:** Both SPLIT link to original TX → Skip
3. **MERGED execution deleted, originals re-import:** Originals IGNORED keep TX links → Skip
4. **Corporate action on IGNORED execution:** New execution inherits IGNORED status
5. **EMPTY trade deletion and re-import:** Tombstones created → Block re-import
6. **Restore execution, trade no longer EMPTY:** is_empty auto-updates (computed)
7. **has_conflict auto-clear after resolution:** Recheck after delete/restore
8. **Restore creates conflict:** MANUAL + restored IMPORTED → has_conflict=true

---

## Risks & Mitigations

### Risk 1: Tombstones accumulate forever
**Mitigation:** Change 2 (Fresh Start Import) provides cleanup mechanism. Tombstones are small (~4 bytes per deleted execution).

### Risk 2: User confused by EMPTY trades
**Mitigation:** Clear UI banner, separate archive tab, restore button prominently displayed.

### Risk 3: Corporate action on IGNORED creates confusion
**Mitigation:** Status inheritance ensures consistent behavior (IGNORED stays IGNORED).

### Risk 4: Database migration fails
**Mitigation:** Test on staging with production data clone first. Backward compatible (old code can run with new schema).

---

## Deployment Checklist

### Pre-Deployment
- [ ] All migrations tested on staging with production data clone
- [ ] All unit tests pass (≥85% coverage)
- [ ] All integration tests pass
- [ ] All E2E tests pass
- [ ] Code review approved (code-reviewer agent)
- [ ] Manual QA on staging (smoke test all scenarios)

### Deployment Order
1. **Phase 1:** Database migrations (enum values, previous_status, tombstones, FK constraints)
2. **Phase 2:** Backend code (models, services, API endpoints)
3. **Phase 3:** Frontend code (types, components, hooks)
4. **Phase 4:** Import dialog enhancement (optional, can be deferred)

### Post-Deployment
- [ ] Monitor error rates (Sentry/logs)
- [ ] Monitor database for new EDITED/IGNORED executions
- [ ] Monitor import jobs (verify tombstone checks work)
- [ ] User feedback (check for confusion about IGNORED executions)

### Rollback Triggers
- Migration fails (Phase 1): Halt deployment, fix migration, retry
- Backend errors spike >5% (Phase 2): Rollback backend code
- Frontend errors spike >5% (Phase 3): Rollback frontend code
- Import jobs fail >10% (Phase 2): Rollback backend, investigate tombstone logic

---

## Future Enhancements (Out of Scope)

Deferred to later changes:

### Change 2: Fresh Start Import
- Import mode: INCREMENTAL | OVERWRITE | FRESH_START
- Fresh Start deletes all trades + tombstones (escape hatch for user)
- "Nuclear Reset" button in settings

### Change 3: Orphaned Journaling Management
- Auto-match orphaned notes to new trades (heuristic: symbol + time window)
- Review UI for manually linking orphaned notes
- Bulk delete orphaned notes

### Optional Enhancements
- Import dialog checkbox: "Overwrite user modifications"
- Bulk restore (restore all executions in EMPTY trade at once)
- Tombstone TTL (auto-expire after X years)
- Audit log (who deleted/restored what, when)

---

## Related Documents

- **AGENTS.md:** Project-wide context and agent strategy
- **docs/architecture/soft-delete-pattern.md:** (To be created) Deep dive on soft-delete design
- **CHANGELOG.md:** Release notes for this change (Keep a Changelog format)

---

## Contact & Support

**Questions?** Ask in project chat or tag `@backend-engineer` or `@frontend-engineer` agents.

**Found a bug?** Create issue with label `execution-soft-delete`.

**Need clarification on spec?** Review `design.md` edge cases section or ask `@docs-writer` agent.

---

**Last Updated:** 2026-04-15  
**Status:** ✅ Specification Complete, Ready for Implementation
