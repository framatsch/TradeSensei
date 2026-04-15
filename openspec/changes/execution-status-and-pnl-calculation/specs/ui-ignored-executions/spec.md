## ADDED Requirements

### Requirement: IGNORED executions have visual distinction in UI

The system SHALL display IGNORED executions with strong visual differentiation to prevent confusion with active executions.

#### Scenario: IGNORED execution shown with 50% opacity
- **WHEN** user toggles "Show ignored executions"
- **AND** IGNORED execution appears in table
- **THEN** entire row has 50% opacity (CSS: opacity: 0.5)
- **AND** all text is dimmed (gray-600 instead of gray-900)
- **AND** row is visually distinct from active executions

#### Scenario: IGNORED execution has status badge
- **WHEN** IGNORED execution is visible
- **THEN** status badge displays "Ignored"
- **AND** badge color is gray (neutral, not warning/error)
- **AND** badge has ghost variant (outline, not filled)

#### Scenario: IGNORED execution P&L is struck through
- **WHEN** IGNORED execution is visible
- **THEN** P&L value has strikethrough styling (text-decoration: line-through)
- **AND** tooltip explains "Excluded from trade P&L"

#### Scenario: IGNORED execution has restore button instead of menu
- **WHEN** IGNORED execution is visible
- **THEN** actions column shows [↺ Restore] button (icon + text)
- **AND** overflow menu [...] is not shown
- **AND** restore button has primary color on hover

### Requirement: Show/hide IGNORED executions toggle with info banner

The system SHALL provide a toggle to show/hide IGNORED executions, with an info banner indicating when IGNORED executions exist.

#### Scenario: Info banner shown when IGNORED executions exist
- **WHEN** trade has 1+ IGNORED executions
- **AND** user views trade details page
- **AND** "Show ignored" is OFF (default)
- **THEN** info banner appears above execution legs table
- **AND** banner text: "ℹ️ 2 ignored executions hidden"
- **AND** banner has [Show] button on the right
- **AND** banner color is neutral blue (info, not warning)

#### Scenario: Toggle shows IGNORED executions
- **WHEN** user clicks [Show] button in info banner
- **THEN** banner text changes to "2 active, 2 ignored"
- **AND** button text changes to [Hide Ignored]
- **AND** IGNORED executions appear in table with 50% opacity
- **AND** table sorts: active executions first, IGNORED last

#### Scenario: Toggle persists per-trade in session
- **WHEN** user enables "Show ignored" on Trade A
- **AND** navigates to Trade B
- **THEN** "Show ignored" is OFF on Trade B (default)
- **AND** setting is per-trade, not global
- **AND** setting resets on page refresh (session-only, not persisted)

#### Scenario: No banner when no IGNORED executions
- **WHEN** trade has 0 IGNORED executions
- **THEN** no info banner is shown
- **AND** no [Show ignored] toggle available

### Requirement: EMPTY trade badge and archive view

The system SHALL display EMPTY trades with a badge and provide a separate archive view for trades with all executions IGNORED.

#### Scenario: EMPTY trade badge in trade list
- **WHEN** trade.is_empty is true
- **AND** user views main trade list
- **AND** include_empty=true (archive view)
- **THEN** trade card shows "Empty" badge next to symbol
- **AND** badge color is gray (neutral)
- **AND** badge has ghost variant (outline)

#### Scenario: EMPTY trade metrics show N/A
- **WHEN** EMPTY trade is displayed
- **THEN** P&L column shows "—" (not $0.00)
- **AND** win/loss badge is hidden (not "Win" or "Loss")
- **AND** return percentage shows "N/A"
- **AND** tooltip explains "Trade has no active executions"

#### Scenario: Archive tab shows only EMPTY trades
- **WHEN** user clicks "Archive" tab in trade list
- **THEN** API call: GET /trades?include_empty=true&only_empty=true
- **AND** only trades with is_empty=true are shown
- **AND** tab badge shows count: "Archive (5)"

#### Scenario: Default view hides EMPTY trades
- **WHEN** user views main trade list (default)
- **THEN** API call: GET /trades?include_empty=false
- **AND** only trades with is_empty=false are shown
- **AND** EMPTY trades do not appear in list

#### Scenario: EMPTY trade detail shows info banner
- **WHEN** user opens EMPTY trade from archive
- **THEN** large info banner at top of page:
  - Icon: ℹ️ (info, not warning)
  - Text: "This trade is empty. All executions have been deleted."
  - Subtext: "Restore executions below to reactivate this trade."
  - Color: neutral blue background
- **AND** execution legs table shows all IGNORED executions by default (no toggle needed)
- **AND** each IGNORED execution has [Restore] button

#### Scenario: EMPTY trade moves to active after restore
- **WHEN** user restores 1 execution in EMPTY trade
- **THEN** trade.is_empty changes to false (computed property)
- **AND** frontend refetches trade list
- **AND** trade appears in main list (not archive)
- **AND** "Empty" badge removed

### Requirement: Restore button triggers execution restoration

The system SHALL provide a restore button for IGNORED executions that calls the restore API and updates the UI.

#### Scenario: Restore button visible on IGNORED execution
- **WHEN** IGNORED execution is visible (show ignored ON)
- **THEN** actions column shows [↺ Restore] button
- **AND** button has icon (↺ rotate-ccw) + text "Restore"
- **AND** button has ghost variant (outline, not filled)
- **AND** button color is primary on hover

#### Scenario: Click restore button calls API
- **WHEN** user clicks [Restore] button on IGNORED execution
- **THEN** POST /api/v1/executions/{id}/restore is called
- **AND** loading spinner shown on button
- **AND** button disabled during request

#### Scenario: Restore success updates UI
- **WHEN** restore API call succeeds
- **THEN** frontend refetches trade data (refetchQueries type: "all")
- **AND** execution appears in active list (no longer IGNORED)
- **AND** status badge changes (e.g., "Imported" or "Edited")
- **AND** row opacity returns to 100%
- **AND** [Restore] button replaced with [...] overflow menu
- **AND** success toast: "Execution restored"

#### Scenario: Restore failure shows error
- **WHEN** restore API call fails (e.g., trade deleted, DB error)
- **THEN** button returns to enabled state
- **AND** error toast: "Failed to restore execution: {error message}"
- **AND** execution remains IGNORED

### Requirement: Execution status badges have consistent styling

The system SHALL use color-coded badges for all execution statuses with consistent design.

#### Scenario: IMPORTED badge styling
- **WHEN** execution status is IMPORTED
- **THEN** badge displays "Imported"
- **AND** badge color is gray (neutral)
- **AND** badge variant is default (subtle background)

#### Scenario: EDITED badge styling
- **WHEN** execution status is EDITED
- **THEN** badge displays "Edited"
- **AND** badge color is amber/orange (warning)
- **AND** badge variant is default (subtle background)
- **AND** visually distinct from IMPORTED

#### Scenario: MANUAL badge styling
- **WHEN** execution status is MANUAL
- **THEN** badge displays "Manual"
- **AND** badge color is blue (info)
- **AND** badge variant is default

#### Scenario: SPLIT badge styling
- **WHEN** execution status is SPLIT
- **THEN** badge displays "Split"
- **AND** badge color is purple (secondary)
- **AND** badge variant is default

#### Scenario: MERGED badge styling
- **WHEN** execution status is MERGED
- **THEN** badge displays "Merged"
- **AND** badge color is purple (secondary)
- **AND** badge variant is default

#### Scenario: IGNORED badge styling
- **WHEN** execution status is IGNORED
- **THEN** badge displays "Ignored"
- **AND** badge color is gray (neutral)
- **AND** badge variant is ghost (outline only, no background)

### Requirement: Trade delete button behavior for EMPTY trades

The system SHALL show different delete button behavior for active vs. EMPTY trades.

#### Scenario: Delete active trade shows soft-delete warning
- **WHEN** user clicks delete button on active trade
- **AND** trade has executions with status != IGNORED
- **THEN** confirmation dialog appears:
  - Title: "Archive this trade?"
  - Body: "All executions will be moved to archive. You can restore them later."
  - Buttons: [Cancel] [Archive Trade]
- **AND** on confirm: DELETE /trades/{id} called (Stage 1)
- **AND** trade moves to archive tab

#### Scenario: Delete EMPTY trade shows permanent warning
- **WHEN** user clicks delete button on EMPTY trade
- **AND** trade.is_empty is true
- **THEN** confirmation dialog appears:
  - Title: "Permanently delete this trade?"
  - Body: "This trade will be permanently deleted. This action cannot be undone."
  - Warning: "⚠️ Broker transactions will be blocked from re-import."
  - Buttons: [Cancel] [Delete Permanently]
  - Delete button is red (destructive variant)
- **AND** on confirm: DELETE /trades/{id} called (Stage 2)
- **AND** trade removed from archive

#### Scenario: Delete EMPTY trade with journaling shows additional warning
- **WHEN** user deletes EMPTY trade
- **AND** trade has TradeNotes or TradeTags
- **THEN** confirmation dialog shows:
  - Additional line: "5 journal entries will be orphaned (can be re-linked later)."
  - Checkbox: "☐ Also delete journal entries"
  - If checked: journal entries deleted with trade
  - If unchecked: journal entries orphaned (trade_id = NULL)

### Requirement: Execution legs table sorting with IGNORED

The system SHALL sort executions with active executions first, IGNORED last.

#### Scenario: Executions sorted by date then status
- **WHEN** trade has mixed IMPORTED and IGNORED executions
- **AND** "Show ignored" is ON
- **THEN** table sorts:
  1. Primary: Status (active statuses first, IGNORED last)
  2. Secondary: Timestamp (ascending, oldest first)
- **AND** active executions group together at top
- **AND** IGNORED executions group together at bottom
- **AND** visual separator (border) between groups

#### Scenario: Separator line between active and IGNORED
- **WHEN** "Show ignored" is ON
- **AND** table has both active and IGNORED executions
- **THEN** dashed border line appears between last active and first IGNORED
- **AND** line color is gray-300 (subtle)
- **AND** line helps visual grouping

## Definition of Done

### Component Implementation

**File:** `frontend/components/trades/ExecutionStatusBadge.tsx`
- Add EDITED status: amber color, "Edited" text
- Add IGNORED status: gray ghost variant, "Ignored" text
- All status colors match design system
- Storybook stories for all statuses

**File:** `frontend/components/trades/ExecutionRow.tsx`
- Conditional rendering: show [Restore] button for IGNORED, [...] menu for others
- 50% opacity for IGNORED rows (Tailwind: opacity-50)
- Strikethrough on P&L for IGNORED (line-through)
- onClick handler for restore button

**File:** `frontend/components/trades/ExecutionLegsTable.tsx`
- Show/hide IGNORED toggle state management (useState)
- Info banner component (conditional: only if IGNORED count > 0)
- Filter IGNORED executions when toggle OFF
- Sort executions: active first, IGNORED last
- Visual separator between groups

**File:** `frontend/components/trades/TradeCard.tsx`
- Conditional "Empty" badge when trade.is_empty
- Conditional metrics: show "—" for P&L, "N/A" for return %
- Hide win/loss badge when empty

**File:** `frontend/components/trades/TradeDetailPage.tsx`
- Info banner at top for EMPTY trades
- Show all IGNORED executions by default when trade is EMPTY (no toggle)

**File:** `frontend/components/trades/TradeListTabs.tsx`
- Add "Archive" tab
- Badge with EMPTY trade count
- API call with include_empty/only_empty params

**File:** `frontend/components/trades/DeleteTradeDialog.tsx`
- Two variants: active trade vs. EMPTY trade
- Different warning text and button styling
- Checkbox for deleting journaling (EMPTY trades only)

### API Client

**File:** `frontend/lib/api/executions.ts`
- Add `restoreExecution(id: number)` method
- POST /api/v1/executions/{id}/restore
- Returns updated execution

### Hooks

**File:** `frontend/hooks/useExecutions.ts`
- Add `useRestoreExecution` mutation hook
- Refetch trade and executions after restore
- Toast notifications on success/error

**File:** `frontend/hooks/useTrade.ts`
- Handle is_empty field in Trade type
- Refetch on execution restore

### Types

**File:** `frontend/types/execution.ts`
```typescript
export enum ExecutionStatus {
  IMPORTED = 'imported',
  MANUAL = 'manual',
  MERGED = 'merged',
  SPLIT = 'split',
  EDITED = 'edited',      // NEW
  IGNORED = 'ignored',    // NEW
}

export interface Execution {
  id: number;
  status: ExecutionStatus;
  previous_status: ExecutionStatus | null;  // NEW
  // ... existing fields
}
```

**File:** `frontend/types/trade.ts`
```typescript
export interface Trade {
  id: number;
  is_empty: boolean;  // NEW - computed on backend
  // ... existing fields
}
```

### E2E Tests

**File:** `frontend/tests/e2e/execution-ignored-ui.spec.ts`

- Test: `should show info banner when ignored executions exist`
  - Setup trade with 1 IMPORTED, 1 IGNORED
  - Verify banner text: "1 ignored execution hidden"
  - Verify [Show] button visible
- Test: `should toggle ignored executions visibility`
  - Click [Show] → verify IGNORED appears with 50% opacity
  - Verify banner text: "1 active, 1 ignored"
  - Click [Hide Ignored] → verify IGNORED disappears
- Test: `should show restore button on ignored execution`
  - Enable "Show ignored"
  - Verify [↺ Restore] button visible on IGNORED row
  - Verify no [...] overflow menu
- Test: `should restore ignored execution on button click`
  - Click [Restore] on IGNORED execution
  - Verify loading state
  - Verify execution moves to active list
  - Verify status badge changes (e.g., "Imported")
  - Verify success toast

**File:** `frontend/tests/e2e/empty-trade-ui.spec.ts`

- Test: `should show empty badge on empty trade`
  - Setup EMPTY trade in API
  - Navigate to archive tab
  - Verify "Empty" badge on trade card
  - Verify P&L shows "—"
- Test: `should show info banner on empty trade detail`
  - Open EMPTY trade
  - Verify info banner: "This trade is empty..."
  - Verify all executions visible by default (no toggle)
  - Verify restore buttons on all executions
- Test: `should show different delete dialogs for active vs empty`
  - Active trade: verify "Archive" dialog
  - EMPTY trade: verify "Permanently delete" dialog with warning
  - Verify destructive button styling (red)

**File:** `frontend/tests/e2e/archive-tab.spec.ts`

- Test: `should show only empty trades in archive tab`
  - Setup 3 trades: 2 active, 1 EMPTY
  - Click "Archive" tab
  - Verify only EMPTY trade shown
  - Verify tab badge: "Archive (1)"
- Test: `should move trade to active after restore`
  - Navigate to archive
  - Open EMPTY trade
  - Restore 1 execution
  - Navigate to main trade list
  - Verify trade now in active list (not archive)

### Visual Regression Tests

**Tool:** Playwright screenshot comparison

- Capture: Execution row with IMPORTED status
- Capture: Execution row with EDITED status (amber badge)
- Capture: Execution row with IGNORED status (50% opacity, gray badge)
- Capture: Info banner "X ignored executions hidden"
- Capture: Trade card with "Empty" badge
- Capture: EMPTY trade detail with info banner
- Capture: Delete dialog for active trade
- Capture: Delete dialog for EMPTY trade

### Accessibility Tests

**Tool:** axe-core via Playwright

- Test: Keyboard navigation through execution table
  - Tab to [Restore] button
  - Enter key triggers restore
- Test: Screen reader announces IGNORED status
  - Badge has aria-label: "Status: Ignored"
- Test: Color contrast for all badges (WCAG AA)
  - EDITED badge: amber on white ≥ 4.5:1
  - IGNORED badge: gray on white ≥ 4.5:1
- Test: Focus indicators visible on all interactive elements
  - [Show] button, [Restore] button, Delete button

### Coverage Requirements

- Component tests (Jest + RTL): ≥80% coverage
- E2E tests: All user flows covered (toggle, restore, delete, archive)
- Visual regression: No unintended UI changes
- Accessibility: No violations reported by axe
- All tests pass before merge
