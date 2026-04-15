# Split Summary: Execution Status & Conflict Resolution

## Original Comprehensive Change

**Name:** `execution-status-and-pnl-calculation`  
**Size:** 235 tasks, 6-8 weeks effort  
**Status:** Too large, split into 3 manageable changes

---

## Split into 3 Changes

### ✅ **Change 1: Execution Soft-Delete & Tombstone Protection**

**Directory:** `openspec/changes/execution-soft-delete-tombstone-protection/`  
**Size:** 185 tasks, 4-5 weeks  
**Priority:** HIGH  
**Dependencies:** None  
**Blocks:** Change 2, Change 3

**Scope:**
- Soft-delete pattern with IGNORED status
- Tombstone table for permanent deletion protection
- Restore mechanism with previous_status field
- Two-stage trade deletion (active → EMPTY → permanent)
- EDITED status for tracking user modifications
- P&L calculation rules based on status
- UI for managing IGNORED executions (show/hide toggle, restore button)
- EMPTY trade handling (archive view, badges)

**Key Files:**
- `proposal.md` - Problem statement, solution overview
- `design.md` - 12 decisions, 8 risks, 8 edge cases
- `tasks.md` - 185 tasks across 39 groups
- `specs/execution-soft-delete/spec.md` - Soft-delete, restore, tombstones
- `specs/execution-edit-tracking/spec.md` - EDITED status, re-import protection
- `specs/pnl-calculation-rules/spec.md` - P&L display logic
- `specs/ui-ignored-executions/spec.md` - UI for IGNORED executions
- `specs/api-endpoints/spec.md` - API changes

**Impact:**
- 4 database migrations
- 7 backend services modified/created
- 6 frontend components modified/created
- 50+ unit tests
- 15+ integration tests
- 25+ E2E tests

---

### ✅ **Change 2: Fresh Start Import Mode**

**Directory:** `openspec/changes/fresh-start-import-mode/`  
**Size:** 70 tasks, 1.5-2 weeks  
**Priority:** MEDIUM  
**Dependencies:** Change 1 (tombstone infrastructure)  
**Blocks:** Change 3 (creates orphaned data)

**Scope:**
- Import mode enum (INCREMENTAL | OVERWRITE | FRESH_START)
- Fresh Start deletes all trades + tombstones before re-import
- Journaling orphaned (not deleted) via FK: ON DELETE SET NULL
- Nuclear Reset button (optional, settings page)
- Import summary shows tombstone cleanup and orphaned counts
- Transaction rollback safety

**Key Files:**
- `proposal.md` - Escape hatch for tombstone accumulation
- `design.md` - 7 decisions, 5 risks
- `tasks.md` - 70 tasks across 19 groups

**Impact:**
- 0 database migrations (uses existing schema)
- ImportService enhanced with Fresh Start mode
- Import dialog with mode selection UI
- Confirmation dialogs with "I understand" checkbox
- Optional nuclear reset endpoint

---

### ✅ **Change 3: Orphaned Journaling Management**

**Directory:** `openspec/changes/orphaned-journaling-management/`  
**Size:** 85 tasks, 2-3 weeks  
**Priority:** LOW  
**Dependencies:** Change 1 (FK constraints), Change 2 (creates orphaned data)  
**Blocks:** None

**Scope:**
- Auto-matching heuristic (symbol + time window, confidence scoring)
- Orphaned journaling review UI (dedicated page)
- Manual linking (search/select trade)
- Bulk operations (accept all, delete all, export backup)
- Enhanced journaling schema (add symbol, opened_at, closed_at columns)

**Key Files:**
- `proposal.md` - Auto-matching and manual review
- `design.md` - 7 decisions, 4 risks, matching algorithm
- `tasks.md` - 85 tasks across 22 groups

**Impact:**
- 3 database migrations (add metadata to journaling tables)
- JournalingService with auto-matching algorithm
- OrphanedJournaling page + components
- Integration with Fresh Start import

---

## Dependency Graph

```
Change 1: Execution Soft-Delete & Tombstone Protection
    ↓
Change 2: Fresh Start Import ← needs tombstones
    ↓
Change 3: Orphaned Journaling ← needs orphaned data from Fresh Start
```

---

## Deployment Order

1. **Deploy Change 1 first** (foundation, no dependencies)
2. **Deploy Change 2 after Change 1** (needs tombstone infrastructure)
3. **Deploy Change 3 after Change 2** (optional, needs orphaned data)

**Note:** Change 3 is optional. System works without it, but orphaned journaling accumulates.

---

## Task Distribution

| Change | Backend | Frontend | Testing | Total | Effort |
|--------|---------|----------|---------|-------|--------|
| Change 1 | ~90 | ~70 | ~25 | **185** | 4-5 weeks |
| Change 2 | ~35 | ~25 | ~10 | **70** | 1.5-2 weeks |
| Change 3 | ~40 | ~35 | ~10 | **85** | 2-3 weeks |
| **Total** | **165** | **130** | **45** | **340** | **8-10 weeks** |

**Note:** Total is 340 tasks (not 235) because splitting added some duplication (documentation, deployment prep per change).

---

## Benefits of Splitting

### **Development:**
- ✅ Smaller, focused PRs (easier to review)
- ✅ Parallel work possible (after Change 1)
- ✅ Faster iteration (deploy Change 1, get feedback, adjust Change 2)
- ✅ Clear scope boundaries

### **Testing:**
- ✅ Isolated test suites per change
- ✅ Easier to debug failures (know which change broke)
- ✅ Better test coverage per feature

### **Deployment:**
- ✅ Incremental rollout (de-risks deployment)
- ✅ Easier rollback (revert one change, not everything)
- ✅ User value delivered sooner (Change 1 solves infinite duplicate problem)

### **Maintenance:**
- ✅ Clear boundaries for bug fixes
- ✅ Easier to understand for new developers
- ✅ Documentation per change (not one massive doc)

---

## Original Comprehensive Spec

The original comprehensive spec remains at:
`openspec/changes/execution-status-and-pnl-calculation/`

This serves as:
- **Reference:** Full context and detailed design
- **Archive:** Preserved for historical context
- **Source:** Content was distributed to the 3 new changes

**Status:** Superseded by the 3 new changes

---

## Next Steps

### **Option 1: Start Implementation**
```bash
# Implement Change 1 first
cd openspec/changes/execution-soft-delete-tombstone-protection
# Review specs, then start with tasks.md

# After Change 1 complete:
cd openspec/changes/fresh-start-import-mode

# After Change 2 complete (optional):
cd openspec/changes/orphaned-journaling-management
```

### **Option 2: Review & Refine**
- Review each change's proposal.md, design.md
- Ask questions about unclear decisions
- Request modifications if needed

---

## Summary

**✅ Split Complete**

- 3 well-defined changes created
- Clear dependencies and deployment order
- 340 tasks distributed (165 backend, 130 frontend, 45 testing)
- 8-10 weeks total effort (can be parallelized after Change 1)
- All comprehensive work preserved as reference

**Ready to start implementation!** 🚀
