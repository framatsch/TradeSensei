## Why

After implementing soft-delete (Change 1) and Fresh Start import (Change 2), journaling data (TradeNotes, TradeTags, TradePlaybooks) can become **orphaned** (trade_id = NULL) when trades are permanently deleted or Fresh Start is executed.

**Problem:** Orphaned journaling data has no automatic way to reconnect to trades after re-import.

**User Scenario:**
1. User journals extensively on 50 trades (notes, tags, playbook associations)
2. User executes Fresh Start import to fix corrupted data
3. All 50 trades deleted → 150 journal entries orphaned (trade_id = NULL)
4. Fresh Start re-imports trades from broker file
5. **Problem:** Old journal entries don't automatically reconnect to new trades
6. User loses valuable journaling context unless manually re-linked

**Why This Matters:**
- Journaling is high-value user input (trade analysis, lessons learned, psychological notes)
- Losing journaling context reduces platform value
- Manual re-linking for 100+ notes is tedious and error-prone

## What Changes

**Auto-Matching Heuristic:**
- After Fresh Start import, automatically match orphaned journal entries to new trades
- Matching criteria: symbol + time window (±1 hour around trade open time)
- Confidence scoring: exact match (100%), close match (80%), uncertain (<50%)
- Low-confidence matches flagged for manual review

**Orphaned Journaling Review UI:**
- New page: "Orphaned Journal Entries" in Settings or Trade management
- Shows all TradeNotes, TradeTags, TradePlaybooks with trade_id = NULL
- For each orphaned entry:
  - Original trade info (symbol, date range from journal metadata)
  - Suggested match (if auto-matching found candidate)
  - Confidence score
  - Actions: [Link to Trade] [Delete] [Keep Orphaned]

**Manual Linking:**
- User can manually link orphaned entry to any trade
- Search/select trade by symbol + date
- Confirm link → Update trade_id

**Bulk Operations:**
- "Accept All High-Confidence Matches" button (>80% confidence)
- "Delete All Orphaned" button (with confirmation)
- "Download Backup" button (export orphaned entries as JSON before deleting)

**Enhanced Journaling Schema:**
- Add symbol, opened_at, closed_at columns to TradeNote, TradeTag, TradePlaybook
- Populate these fields when creating journal entry (from parent trade)
- Used for auto-matching after orphaning

## Capabilities

### New Capabilities
- `auto-match-orphaned-journaling`: Heuristic matching of orphaned notes to re-imported trades
- `orphaned-journaling-review`: UI to view, manage, and manually link orphaned entries
- `orphaned-journaling-bulk-ops`: Accept all matches, delete all, download backup
- `manual-journaling-link`: User can manually link orphaned entry to trade

### Modified Capabilities
- `journaling-schema`: Add symbol, opened_at, closed_at to TradeNote, TradeTag, TradePlaybook tables

## Impact

**Database:**
- Add symbol, opened_at, closed_at columns to trade_notes table
- Add symbol, opened_at, closed_at columns to trade_tags table
- Add symbol, opened_at, closed_at columns to trade_playbooks table
- Migration: Backfill existing rows with data from linked trades (if trade_id not NULL)

**Backend:**
- `app/services/journaling.py` - NEW: Auto-matching service with heuristic logic
- `app/services/trade_note.py` - Update create_note() to populate symbol, opened_at, closed_at
- `app/services/trade_tag.py` - Update add_tag() to populate metadata
- `app/services/trade_playbook.py` - Update link_playbook() to populate metadata
- `app/api/v1/journaling.py` - NEW: Endpoints for orphaned management
- `app/schemas/journaling.py` - Add OrphanedJournalEntry schema with confidence score

**Frontend:**
- `pages/OrphanedJournaling.tsx` - NEW: Review page for orphaned entries
- `components/orphaned/OrphanedEntryCard.tsx` - NEW: Display orphaned entry with suggested match
- `components/orphaned/ManualLinkDialog.tsx` - NEW: Search/select trade to link
- `hooks/useOrphanedJournaling.ts` - NEW: Query orphaned entries, link, delete
- Navigation: Add link to orphaned page (if orphaned count > 0)

**API:**
- GET /api/v1/journaling/orphaned - Get all orphaned entries with suggested matches
- POST /api/v1/journaling/{id}/link - Manually link orphaned entry to trade
- POST /api/v1/journaling/orphaned/accept-matches - Bulk accept high-confidence matches
- DELETE /api/v1/journaling/orphaned - Bulk delete all orphaned entries
- GET /api/v1/journaling/orphaned/export - Download orphaned entries as JSON

## Out of Scope (Future Enhancements)

- **ML-based matching:** Use trade characteristics (P&L, duration, setup type) for smarter matching
- **Conflict resolution:** If multiple orphaned notes match same trade, how to decide which to link
- **Undo auto-matching:** If auto-match was wrong, user can unlink and re-match
- **Batch re-link:** Select multiple orphaned entries and link to one trade
