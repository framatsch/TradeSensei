# trade-list-mobile-ui Specification

## Purpose
Define the mobile Trades list layout below the `lg` breakpoint, including trade cards, sorting, selection, bulk actions, a tabbed filter sheet, and pagination.

## Requirements

### Requirement: Trades list mobile layout reference
On viewports below `lg` (`< 1024px`), the Trades list page (`/dashboard/trades`) SHALL follow the reference wireframes below. The desktop layout (`lg+`) SHALL remain unchanged. The wireframes are the visual contract for implementation and UI review (mobile baseline viewport `375×812`).

```text
List (default)
+------------------------------------------+
| Trades                     [+ New Trade] |
+------------------------------------------+
| [⚙ Filter (3)]  View: Swing A+   [Clear] |   filter trigger row
| [Sort: Closed ↓            v]  [Select]  |   list toolbar
+------------------------------------------+
| AAPL ⧉ [▲ LONG] STK          +$412.50    |   TradeCard (tap → detail)
| 100 @ $182.40 → $186.52                  |
| Oct 24 → Oct 25 · IBKR Main              |
| [Breakout] [FOMO]                  💬 2  |
+------------------------------------------+
| SPY 241025C580  COMBO          -$88.40   |
| 2 @ $4.10 → $4.54                        |
| Oct 25 → Oct 25 · IBKR Main        💬 +  |
+------------------------------------------+
| TSLA [▼ SHORT] STK  [Open]          —    |
| 50 @ $251.10 → —                         |
| Oct 28 → — · Schwab                      |
+------------------------------------------+
| 128 total trades        Rows [20 v]      |
|        [‹ Prev]   Page 2   [Next ›]      |
+------------------------------------------+

Selection mode
+------------------------------------------+
| [x] Select all on page          [Done]   |
+------------------------------------------+
| [x] AAPL [▲ LONG] STK        +$412.50    |
|     100 @ $182.40 → $186.52              |
+------------------------------------------+
| [ ] SPY 241025C580  COMBO      -$88.40   |
+------------------------------------------+
| 1 selected                               |   fixed bottom bar
| [⑂ Merge] [▤ Playbook] [# Tags] [🗑 Del] |   (Merge only with ≥ 2)
+------------------------------------------+

Filter bottom sheet
+------------------------------------------+
| Filters                            [ X ] |
| [ Trade 2 ] [ Time 1 ] [ Journal ] [Acct]|   tabs with active-count badge
+------------------------------------------+
| Symbol      [AAPL x] [-TSLA x] [...]     |   tab "Trade"
| Direction   [All                    v]   |
| Status      [All                    v]   |
| Result      (•) All ( ) Winners ( ) Los. |
| Asset Class [EQUITY] [OPTION] [FUTURE]   |
|             [FOREX] [CRYPTO] [COMBO]     |
|                                          |
+------------------------------------------+
| [Save View] [Update] [Rename] [Delete]   |   saved-view actions
| [Clear all]             [Show results]   |
+------------------------------------------+
```

#### Scenario: Mobile list matches the reference wireframe
- **WHEN** a user opens `/dashboard/trades` on a `375×812` viewport
- **THEN** trades render as cards with the filter trigger row, list toolbar and compact pagination shown in the reference wireframe, without horizontal page overflow

#### Scenario: Desktop table is unchanged
- **WHEN** a user opens `/dashboard/trades` on a viewport `lg` or wider
- **THEN** the existing sortable table, collapsible filter panel and sticky bulk-action toolbar are rendered and no trade cards are visible

### Requirement: Trades render as tappable cards on mobile
Below `lg`, each trade SHALL render as a `TradeCard` containing:
1. Row 1: symbol (with corporate-action split icon if applicable), direction badge (hidden for combo trades), asset class or `COMBO`, an `Open` badge for open trades, and the P&L right-aligned and colored by sign (`—` if null).
2. Row 2: `<quantity> @ <entry price> → <exit price>` (`—` for a missing exit price).
3. Row 3: `<opened date> → <closed date> · <account name>`.
4. Row 4 (only if tags exist or quick notes are enabled): taxonomy badges and, if `enable_quick_notes` is enabled, the notes-count badge.

Tapping the card (outside of the notes badge) SHALL navigate to `/dashboard/trades/[id]`. Tapping the notes badge SHALL toggle the Quick Note input below the card without navigating. The card SHALL be keyboard-focusable as a link and expose the symbol as its accessible name. The empty state (`No trades found…`), loading spinner and error/retry state SHALL be the same as for the table.

#### Scenario: Tap opens trade detail
- **WHEN** the user taps a trade card outside the notes badge
- **THEN** the router navigates to `/dashboard/trades/<trade id>`

#### Scenario: Notes badge opens quick note input
- **WHEN** quick notes are enabled and the user taps the notes badge on a card
- **THEN** the Quick Note input opens below that card and no navigation happens

#### Scenario: Combo trade card hides direction
- **WHEN** a combo trade is rendered as a card
- **THEN** no LONG/SHORT badge is shown and `COMBO` is displayed as asset class

### Requirement: Sort dropdown replaces sortable column headers on mobile
Below `lg`, the list toolbar SHALL contain a sort select with the options `Opened: newest`, `Opened: oldest`, `Closed: newest`, `Closed: oldest`, `P&L: highest`, `P&L: lowest`, `Symbol: A → Z`, `Symbol: Z → A`, mapped to the existing `sort_by` / `sort_dir` values. Changing the selection SHALL call the same sort handler as the table headers, so URL sync and cursor reset behave identically.

#### Scenario: Sorting by P&L on mobile
- **WHEN** the user selects `P&L: highest` in the mobile sort select
- **THEN** the URL contains `sort_by=pnl` and `sort_dir=desc`, pagination resets to page 1, and the cards are ordered by P&L descending

#### Scenario: Sort select reflects current sort
- **WHEN** the page is opened with `sort_by=symbol&sort_dir=asc`
- **THEN** the mobile sort select shows `Symbol: A → Z`

### Requirement: Selection mode with fixed bottom bulk-action bar on mobile
Below `lg`, card checkboxes SHALL be hidden by default. A `Select` button in the list toolbar SHALL enter selection mode, which shows a checkbox on every card, a `Select all on page` checkbox, and a `Done` button. In selection mode, tapping a card SHALL toggle its selection instead of navigating. `Done` SHALL exit selection mode and clear the selection.

While at least one trade is selected below `lg`, the bulk-action toolbar SHALL render as a bar fixed to the bottom of the viewport (respecting the device safe-area inset) showing the selection count and icon+label buttons `Merge` (only with ≥ 2 selected), `Playbook`, `Tags`, and `Delete`, triggering the same handlers and modals as the desktop toolbar. The list SHALL reserve bottom padding so the bar never covers the last card or the pagination.

#### Scenario: Entering selection mode
- **WHEN** the user taps `Select`
- **THEN** checkboxes appear on all cards and tapping a card toggles its checkbox instead of opening the trade

#### Scenario: Bulk assign playbook from bottom bar
- **WHEN** the user selects two trades in selection mode and taps `Playbook` in the bottom bar
- **THEN** the existing Playbook picker modal opens, and after confirming, the playbook is assigned to both trades and the selection is cleared

#### Scenario: Merge requires two trades
- **WHEN** exactly one trade is selected
- **THEN** the bottom bar does not show the `Merge` button

#### Scenario: Done clears selection
- **WHEN** the user taps `Done` with trades selected
- **THEN** selection mode ends, all checkboxes are hidden, and the bottom bar disappears

### Requirement: Tabbed filter bottom sheet on mobile
Below `lg`, the filter trigger row SHALL show a `Filter` button with the active-filter count, the active saved-view name (if any), and a `Clear` button when filters are active. Tapping `Filter` SHALL open a bottom sheet (modal dialog with focus trap, closable via close button, overlay tap and `Esc`, max height `90dvh`) instead of expanding the inline panel.

The sheet SHALL group the existing filter fields into four tabs, each tab label showing the number of active filters in that group:
- `Trade`: Symbol (include/exclude), Direction, Status (only when open trades are shown), Result, Asset Class.
- `Time`: Opened From / To, Closed From / To, Hour of Day, Day of Week.
- `Journal`: Playbook, Taxonomies, Annotation Filters.
- `Account`: Account, Execution State, Needs linking.

Filter changes SHALL apply immediately through the same `onChange` handler as the desktop panel (including URL sync). The sheet footer SHALL contain `Clear all` and a primary `Show results` button that closes the sheet. The saved-view actions (`Save View`; and for active user views `Update`, `Rename`, `Delete View`) SHALL be available in the sheet footer. Every filter field available on desktop SHALL be available in exactly one sheet tab.

#### Scenario: Opening the filter sheet
- **WHEN** the user taps `Filter (3)` on a mobile viewport
- **THEN** a bottom sheet opens with the `Trade` tab selected and the tabs `Trade`, `Time`, `Journal`, `Account` showing their active-filter counts

#### Scenario: Filters apply live
- **WHEN** the user selects `Winners` in the `Trade` tab of the sheet
- **THEN** the URL is updated with the filter, the list behind the sheet refreshes, and the `Filter` count increases by one

#### Scenario: Show results closes the sheet
- **WHEN** the user taps `Show results`
- **THEN** the sheet closes and the filtered card list is visible

#### Scenario: Saved view actions in the sheet
- **WHEN** a user view is active and the user opens the filter sheet
- **THEN** `Save View`, `Update`, `Rename` and `Delete View` are available in the sheet footer and trigger the same handlers as on desktop

#### Scenario: Clear all from the sheet
- **WHEN** the user taps `Clear all` in the sheet
- **THEN** all filters are reset and every tab count shows no active filters

### Requirement: Compact pagination on mobile
Below `lg`, the pagination footer SHALL render in two rows: the total trade count with the rows-per-page select, and `‹ Prev`, `Page n`, `Next ›` controls with touch targets of at least `40px` height. Behavior (cursor stack, disabled states, page-size change) SHALL be identical to the desktop pagination.

#### Scenario: Paging forward on mobile
- **WHEN** the user taps `Next ›` on page 1 and a next cursor exists
- **THEN** page 2 is loaded and `‹ Prev` becomes enabled
