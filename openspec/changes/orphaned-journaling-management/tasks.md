## 1. Database Schema - Add Metadata to Journaling Tables

- [ ] 1.1 Create migration: Add symbol, opened_at, closed_at to trade_notes table
- [ ] 1.2 Create migration: Add symbol, opened_at, closed_at to trade_tags table
- [ ] 1.3 Create migration: Add symbol, opened_at, closed_at to trade_playbooks table
- [ ] 1.4 Create migration: Backfill existing rows (UPDATE FROM trades WHERE trade_id NOT NULL)
- [ ] 1.5 Test migration on local database
- [ ] 1.6 Test migration on staging with production data clone
- [ ] 1.7 Verify backfill completes within acceptable time (<5 minutes)

## 2. Backend Services - Populate Metadata on Creation

- [ ] 2.1 Update TradeNoteService.create_note() to populate symbol, opened_at, closed_at from parent trade
- [ ] 2.2 Update TradeTagService.add_tag() to populate metadata
- [ ] 2.3 Update TradePlaybookService.link_playbook() to populate metadata
- [ ] 2.4 Write unit test: test_create_note_populates_metadata()
- [ ] 2.5 Write unit test: test_add_tag_populates_metadata()
- [ ] 2.6 Write unit test: test_link_playbook_populates_metadata()

## 3. Backend Journaling Service - Auto-Matching

- [ ] 3.1 Create services/journaling.py with JournalingService class
- [ ] 3.2 Implement _find_match(entry, trades) with heuristic algorithm
- [ ] 3.3 Implement confidence scoring (100% = ±1h, 80% = ±2h, 50% = ±1d)
- [ ] 3.4 Implement auto_match_orphaned() method (queries orphaned, runs matching, links high-confidence)
- [ ] 3.5 Write unit test: test_find_match_exact_symbol_and_time()
- [ ] 3.6 Write unit test: test_find_match_confidence_scoring()
- [ ] 3.7 Write unit test: test_find_match_no_match_found()
- [ ] 3.8 Write unit test: test_auto_match_links_high_confidence_only()

## 4. Backend Journaling Service - Orphaned Queries

- [ ] 4.1 Implement _get_orphaned_notes(db) method (query trade_notes WHERE trade_id IS NULL)
- [ ] 4.2 Implement _get_orphaned_tags(db) method
- [ ] 4.3 Implement _get_orphaned_playbooks(db) method
- [ ] 4.4 Implement get_orphaned_with_suggestions(db) method (includes suggested matches)
- [ ] 4.5 Write unit test: test_get_orphaned_notes()
- [ ] 4.6 Write unit test: test_get_orphaned_with_suggestions()

## 5. Backend API Endpoints - Orphaned Management

- [ ] 5.1 Create api/v1/journaling.py with router
- [ ] 5.2 Implement GET /api/v1/journaling/orphaned (returns orphaned with suggested matches)
- [ ] 5.3 Implement POST /api/v1/journaling/{id}/link (manually link to trade)
- [ ] 5.4 Implement POST /api/v1/journaling/orphaned/accept-matches (bulk accept high-confidence)
- [ ] 5.5 Implement DELETE /api/v1/journaling/orphaned (bulk delete with confirmation)
- [ ] 5.6 Implement GET /api/v1/journaling/orphaned/export (download as JSON)
- [ ] 5.7 Add OpenAPI docstrings for all endpoints
- [ ] 5.8 Add response_model annotations

## 6. Backend Integration with Fresh Start

- [ ] 6.1 Update ImportService.fresh_start_import() to call auto_match_orphaned() after import
- [ ] 6.2 Include matched count in ImportSummary response
- [ ] 6.3 Write integration test: test_fresh_start_auto_matches_orphaned_journaling()
- [ ] 6.4 Write integration test: test_fresh_start_does_not_link_low_confidence_matches()

## 7. Backend Integration Tests

- [ ] 7.1 Test: test_get_orphaned_returns_all_types (notes, tags, playbooks)
- [ ] 7.2 Test: test_manual_link_updates_trade_id()
- [ ] 7.3 Test: test_accept_matches_links_high_confidence_only()
- [ ] 7.4 Test: test_bulk_delete_requires_confirmation()
- [ ] 7.5 Test: test_export_orphaned_returns_json()

## 8. Frontend Types & Schemas

- [ ] 8.1 Create OrphanedEntry interface in types/journaling.ts
- [ ] 8.2 Create SuggestedMatch interface
- [ ] 8.3 Add symbol, opened_at, closed_at to TradeNote, TradeTag, TradePlaybook types

## 9. Frontend API Client

- [ ] 9.1 Add getOrphanedEntries() method
- [ ] 9.2 Add linkEntryToTrade(id, trade_id) method
- [ ] 9.3 Add acceptHighConfidenceMatches() method
- [ ] 9.4 Add bulkDeleteOrphaned(confirm) method
- [ ] 9.5 Add exportOrphaned() method (download JSON file)

## 10. Frontend Hooks

- [ ] 10.1 Create useOrphanedJournaling hook (query orphaned entries)
- [ ] 10.2 Create useLinkEntry mutation hook
- [ ] 10.3 Create useAcceptMatches mutation hook
- [ ] 10.4 Create useBulkDeleteOrphaned mutation hook
- [ ] 10.5 Add success/error toast notifications

## 11. Frontend OrphanedJournaling Page

- [ ] 11.1 Create pages/OrphanedJournaling.tsx
- [ ] 11.2 Page title: "Orphaned Journal Entries"
- [ ] 11.3 Info banner explaining what orphaned entries are
- [ ] 11.4 Display count: "X notes, Y tags, Z playbooks"
- [ ] 11.5 Filter/tabs: All | Notes | Tags | Playbooks
- [ ] 11.6 Bulk action buttons: [Accept All High-Confidence] [Delete All] [Export Backup]

## 12. Frontend OrphanedEntryCard Component

- [ ] 12.1 Create components/orphaned/OrphanedEntryCard.tsx
- [ ] 12.2 Display entry type icon (note, tag, playbook)
- [ ] 12.3 Display content/title
- [ ] 12.4 Display original trade info: "AAPL, 2024-03-15"
- [ ] 12.5 If suggested match exists: Show alert with confidence badge
- [ ] 12.6 Action buttons: [Link to Suggested] [Manual Link] [Delete]
- [ ] 12.7 If no suggested match: Show "No automatic match found" message

## 13. Frontend ManualLinkDialog Component

- [ ] 13.1 Create components/orphaned/ManualLinkDialog.tsx
- [ ] 13.2 Search input: Filter trades by symbol or date
- [ ] 13.3 Trade list: Display trades matching search
- [ ] 13.4 TradeCard: Symbol, date range, P&L
- [ ] 13.5 Click TradeCard → Confirm link → Call API → Close dialog
- [ ] 13.6 Success toast: "Entry linked to trade"

## 14. Frontend Bulk Operations

- [ ] 14.1 Implement Accept All High-Confidence button
  - Confirmation dialog: "Link X entries with >80% confidence?"
  - Call acceptHighConfidenceMatches()
  - Refetch orphaned list
  - Success toast: "X entries linked"
- [ ] 14.2 Implement Delete All button
  - Confirmation dialog with "I understand" checkbox
  - Call bulkDeleteOrphaned(confirm=true)
  - Redirect to trades page or show empty state
  - Success toast: "All orphaned entries deleted"
- [ ] 14.3 Implement Export Backup button
  - Call exportOrphaned()
  - Download JSON file
  - Success toast: "Backup downloaded"

## 15. Frontend Navigation Integration

- [ ] 15.1 Add orphaned count query to layout/nav
- [ ] 15.2 Conditional NavLink: Show "Orphaned Entries" only if count > 0
- [ ] 15.3 Add warning badge with orphaned count
- [ ] 15.4 Link to /orphaned-journaling page

## 16. Frontend ImportSummary Enhancement

- [ ] 16.1 Update ImportSummary component to show auto_matched count
- [ ] 16.2 Info text: "X journal entries automatically re-linked"
- [ ] 16.3 If orphaned count > 0: Add link to orphaned page

## 17. Frontend E2E Tests - Orphaned Management

- [ ] 17.1 Test: should show orphaned page link when entries exist
  - Setup: Create orphaned note (trade_id=NULL)
  - Verify nav link visible with badge
- [ ] 17.2 Test: should display orphaned entries correctly
  - Navigate to orphaned page
  - Verify entry card shows content, symbol, date
- [ ] 17.3 Test: should show suggested match with confidence
  - Setup: Orphaned note + matching trade
  - Run auto-match backend
  - Verify suggested match displayed with confidence badge
- [ ] 17.4 Test: should link to suggested match on button click
  - Click "Link to Suggested" button
  - Verify success toast
  - Verify entry removed from orphaned list
- [ ] 17.5 Test: should manually link to selected trade
  - Click "Manual Link" button
  - Search for trade
  - Select trade from list
  - Verify link created
- [ ] 17.6 Test: should accept all high-confidence matches
  - Setup: Multiple orphaned with high confidence matches
  - Click "Accept All" button
  - Confirm dialog
  - Verify all linked
- [ ] 17.7 Test: should delete all orphaned entries
  - Click "Delete All" button
  - Check "I understand" checkbox
  - Confirm
  - Verify orphaned page empty
- [ ] 17.8 Test: should export orphaned as JSON
  - Click "Export Backup" button
  - Verify file downloaded

## 18. Frontend E2E Tests - Auto-Matching After Fresh Start

- [ ] 18.1 Test: should auto-match orphaned entries after fresh start
  - Setup: Trade with note
  - Fresh Start import (orphans note)
  - Verify import summary shows "X entries re-linked"
  - Verify note linked to new trade
  - Verify orphaned count = 0

## 19. Documentation

- [ ] 19.1 Create user guide: "Managing Orphaned Journal Entries"
- [ ] 19.2 Document auto-matching heuristic and confidence scores
- [ ] 19.3 Add troubleshooting: "Why wasn't my note automatically matched?"
- [ ] 19.4 Document bulk operations and export backup workflow
- [ ] 19.5 Update AGENTS.md with journaling metadata fields

## 20. Code Review & Quality

- [ ] 20.1 Run lint-check skill (ruff + mypy)
- [ ] 20.2 Run unit-test skill (pytest with coverage ≥80%)
- [ ] 20.3 Run all E2E tests (Playwright)
- [ ] 20.4 Invoke code-reviewer agent for architecture compliance
- [ ] 20.5 Verify no regression in existing journaling tests

## 21. Deployment Preparation

- [ ] 21.1 Test backfill migration on staging (verify completes within time limit)
- [ ] 21.2 Test auto-matching performance on large dataset (1000+ orphaned entries)
- [ ] 21.3 Create deployment runbook (migration order, rollback steps)
- [ ] 21.4 Add monitoring for orphaned count (track over time)

## 22. Changelog & Release Notes

- [ ] 22.1 Invoke changelog-writer agent to update CHANGELOG.md
- [ ] 22.2 Add entry under [Unreleased] section
- [ ] 22.3 Section: Added (auto-matching, orphaned review UI, bulk operations)
- [ ] 22.4 Section: Changed (journaling tables now store symbol and dates)

---

## Summary

**Total Tasks:** 85 tasks across 22 groups

**Estimated Effort:** 2-3 weeks
- Database & Backend: ~40 tasks (1-1.5 weeks)
- Frontend: ~35 tasks (1-1.5 weeks)
- Testing & Documentation: ~10 tasks (0.5 week)

**Dependencies:** 
- Requires Change 1 (FK constraints ON DELETE SET NULL)
- Requires Change 2 (Fresh Start creates orphaned data)

**Blocks:** None (optional enhancement)
