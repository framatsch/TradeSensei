# trade-detail-mobile-ui Specification

## Purpose
Define the mobile Trade Detail layout below the `lg` breakpoint, including compact results, state-preserving tabs, execution cards, and touch-accessible controls.

## Requirements

### Requirement: Trade Detail mobile layout reference
On viewports below `lg` (`< 1024px`), the Trade Detail page (`/dashboard/trades/[id]`) SHALL follow the reference wireframe below. The desktop layout (`lg+`) SHALL remain unchanged. The wireframe is the visual contract for implementation and UI review (mobile baseline viewport `375×812`).

```text
+------------------------------------------+
| [<-]  AAPL ⧉             [‹] [›]  [⋯]   |   Row 1: back, symbol, split icon,
|                                          |          prev/next, actions menu
|       [▲ LONG] [STK] [Closed] [Edited]   |   Row 2: badges
|       Oct 24, 09:41 → Oct 25 · 1d 6h     |   Row 3: open → close · holding
|                                  3 / 128 |          + list position
| +--------------------------------------+ |
| |  +$412.50   |   +1.8R    |  +2.3%    | |   KPI strip (3 equal columns)
| |  P&L        |  Real. R   |  Return   | |
| +--------------------------------------+ |
+------------------------------------------+
| ! Conflict banner / unlinked banner      |   (only when applicable)
+------------------------------------------+
| [ Overview ] [ Journal • ] [ Execs (4) ] |   sticky segmented switcher
+------------------------------------------+

Tab "Overview" (default)
+------------------------------------------+
| [ TradingView | Screenshots (2) ]        |
| +--------------------------------------+ |
| |                                      | |
| |     TradingView chart (min-h 360)    | |
| |                                      | |
| +--------------------------------------+ |
+------------------------------------------+
| PERFORMANCE                              |
| Stop Loss       ✎ | Take Profit      ✎   |
| $178.00           | Add...               |
| Initial Risk      | Planned RRR          |
| $440.00           | 1 : 2.10             |
| Gross P&L         | Net P&L              |
| +$420.00          | +$412.50             |
+------------------------------------------+
| EXECUTION SUMMARY (2-column grid)        |
+------------------------------------------+

Tab "Journal"
+------------------------------------------+
| QUALITATIVE ANALYSIS & METADATA          |
| Playbook   [Breakout                  v] |
| Tags       [FOMO x] [Patient x] [+ Add]  |
| Annotations                              |
|   Setup quality   [A          v]         |
|   Mood (1-5)      [ 4 ]                  |
| Journal                       [ ✎ Edit ] |
| +--------------------------------------+ |
| | ## Entry                             | |
| | Waited for the retest...             | |
| +--------------------------------------+ |
+------------------------------------------+
| QUICK NOTES (2)                          |
+------------------------------------------+
| Unsaved changes      [Cancel]  [Save]    |   fixed bottom bar (only when dirty)
+------------------------------------------+

Tab "Executions (4)"
+------------------------------------------+
| EXECUTION LEGS (4)  [Show deleted] [+ Add]|
+------------------------------------------+
| [▲ BUY]  100 @ $182.40              [⋯]  |
| Oct 24, 09:41 · Comm. $1.00              |
| P&L —            [Imported] [Lineage]    |
+------------------------------------------+
| ── ⧉ Split 2:1 on 2026-10-24 ──────────  |   corporate action divider
+------------------------------------------+
| [▼ SELL] 200 @ $93.26               [⋯]  |
| Oct 25, 15:12 · Comm. $1.00              |
| P&L +$412.50     [Manual]                |
+------------------------------------------+
```

#### Scenario: Mobile layout matches the reference wireframe
- **WHEN** a user opens `/dashboard/trades/[id]` on a `375×812` viewport
- **THEN** the page renders the compact Header Card with KPI strip, the segmented switcher, and the `Overview` pane as shown in the reference wireframe, without horizontal page overflow

#### Scenario: Desktop layout is unchanged
- **WHEN** a user opens `/dashboard/trades/[id]` on a viewport `lg` or wider
- **THEN** the existing desktop layout (header, chart + performance grid, execution summary, qualitative panel, quick notes, execution legs table) is rendered and the segmented switcher is not visible

### Requirement: Compact mobile Header Card with KPI strip
On viewports below `lg`, the Trade Detail Header Card SHALL render:
1. Row 1: an icon-only `Back to Trades` button (`aria-label="Back to Trades"`), the symbol, the corporate-action split icon (if applicable), the icon-only `Previous trade` / `Next trade` buttons (as defined in `trade-detail-navigation`), and the `Trade actions` (`⋯`) menu containing `Correct Trade…` and `Merge with…`.
2. Row 2: the direction badge (hidden for combo trades), the asset-class / `COMBO` badge, the `Open` / `Closed` status badge and the `Manually Edited` badge (if applicable).
3. Row 3: a single line `<opened_at> → <closed_at> · <holding period>` (`Ongoing` for open trades) and, right-aligned, the list position indicator (as defined in `trade-detail-navigation`).
4. A KPI strip with three equal columns: `P&L` (the trade's final P&L, colored by sign), `Realized R`, and `Return %`. Values that cannot be computed SHALL render as `—`.

The separate `Back to Trades` text link above the header SHALL be hidden below `lg`.

#### Scenario: KPI strip shows key results without scrolling
- **WHEN** a user opens a closed trade with a stop loss on a mobile viewport
- **THEN** P&L, Realized R and Return % are visible in the Header Card above the fold

#### Scenario: KPI values fall back to dash
- **WHEN** a trade has no stop loss set
- **THEN** the `Realized R` KPI renders `—`

#### Scenario: Actions menu is reachable on mobile
- **WHEN** the user taps the `Trade actions` button in the mobile Header Card
- **THEN** a menu with `Correct Trade…` and `Merge with…` opens and each entry opens the same modal as on desktop

### Requirement: Three-tab segmented switcher with state-preserving panes
On viewports below `lg`, a segmented switcher with the tabs `Overview`, `Journal`, and `Executions (n)` SHALL be rendered directly below the Header Card (and below any conflict/unlinked banners), using the same visual pattern as the Playbook and Check-in mobile switchers (`role="tablist"`, `role="tab"`, `aria-selected`). `n` SHALL be the number of non-deleted execution legs of the trade. The switcher SHALL stick to the top of the scroll container while scrolling. `Overview` SHALL be the default tab.

All three panes SHALL stay mounted in the DOM; inactive panes SHALL be hidden via CSS only (`hidden lg:block`), so that the TradingView widget is not re-initialized and unsaved journal input is not lost when switching tabs. On `lg+` all panes SHALL be visible in the existing desktop order.

#### Scenario: Default tab on mobile
- **WHEN** a user opens a trade on a mobile viewport
- **THEN** the `Overview` tab is selected and the Media & Charts card, Performance card and Execution Summary are visible, while the Journal and Executions panes are hidden

#### Scenario: Switching tabs preserves unsaved journal input
- **WHEN** the user types into the journal in the `Journal` tab, switches to `Overview`, and switches back to `Journal`
- **THEN** the typed journal text is still present and still marked as unsaved

#### Scenario: Executions tab shows leg count
- **WHEN** a trade has 4 active and 1 deleted execution legs
- **THEN** the third tab is labelled `Executions (4)`

#### Scenario: Conflict banner review switches to Executions tab
- **WHEN** the trade has a conflict and the user taps `Review` in the conflict banner on a mobile viewport
- **THEN** the `Executions` tab becomes active and the execution legs are scrolled into view

### Requirement: Overview pane shows compact chart and 2-column performance grid
Below `lg`, the `Overview` pane SHALL contain, in order: the Media & Charts card (TradingView / Screenshots tabs) with a minimum height of `360px`, the Performance card, and the Execution Summary card. The Performance card SHALL render its metrics as a 2-column grid containing `Stop Loss` and `Take Profit` (both inline-editable as on desktop), `Initial Risk`, `Planned RRR`, `Gross P&L`, and `Net P&L`. Metrics already shown in the Header (`Realized R`, `Return %`, `Holding Period`) SHALL be hidden from the Performance card below `lg`.

#### Scenario: Stop loss is editable on mobile
- **WHEN** the user taps the `Stop Loss` value in the mobile Performance card, enters a value and confirms
- **THEN** the stop loss is saved via the same update mutation as on desktop and the `Realized R` KPI in the header updates

#### Scenario: No duplicate metrics on mobile
- **WHEN** the `Overview` pane is shown on a mobile viewport
- **THEN** `Realized R`, `Return %` and `Holding Period` appear only in the Header Card, not in the Performance card

### Requirement: Journal pane with sticky save bar
Below `lg`, the `Journal` pane SHALL contain the Qualitative Analysis & Metadata panel (Playbook, Tags, Annotations, Markdown journal) followed by Quick Notes (when the `enable_quick_notes` feature flag is enabled). While the panel has unsaved changes, below `lg`:
- the `Journal` tab SHALL display an unsaved-changes dot indicator, and
- the `Unsaved changes` label with `Cancel` and `Save` buttons SHALL render in a bar fixed to the bottom of the viewport (respecting the device safe-area inset) instead of the panel header.

#### Scenario: Save bar appears when journal is dirty
- **WHEN** the user changes the playbook, tags, annotations or journal text on a mobile viewport
- **THEN** a fixed bottom bar with `Unsaved changes`, `Cancel` and `Save` appears and the `Journal` tab shows a dot indicator

#### Scenario: Save from the bottom bar
- **WHEN** the user taps `Save` in the fixed bottom bar
- **THEN** the changes are persisted exactly as with the desktop `Save` button and the bar and the tab indicator disappear

### Requirement: Execution legs render as cards on mobile
Below `lg`, the execution legs SHALL render as a vertical list of cards instead of a table. The section header (title with count, `Show deleted` toggle, `Add Execution` button) SHALL remain, and the section SHALL NOT be collapsed by default on mobile. Each leg card SHALL show the side badge, quantity @ price (as-traded value with split-adjusted indicator where applicable), executed-at timestamp, commission, P&L, origin/status badge and lineage badge; combo legs SHALL additionally show open/close, symbol and asset class; option legs SHALL additionally show strike, type and expiry. Corporate-action timeline items SHALL render as a full-width divider between cards. Conflicting legs SHALL be highlighted with the same conflict styling as on desktop; deleted legs SHALL render at reduced opacity with a `Restore` action.

Each card SHALL provide a `Leg actions` (`⋯`) menu with the same entries and conditions as the desktop row menu: `Edit`, `Split`, `Link broker transaction…`, `Move to...`, `Detach as new Trade`, `Delete`. Selecting `Edit` SHALL turn the card into a stacked edit form (direction toggle, executed-at, quantity, price, commission, P&L) with `Save` and `Cancel` buttons.

#### Scenario: Legs are readable without horizontal scrolling
- **WHEN** the user opens the `Executions` tab on a `375×812` viewport for a combo option trade
- **THEN** every leg is shown as a card with all its values and no horizontal scrollbar appears

#### Scenario: Editing a leg on mobile
- **WHEN** the user selects `Edit` from a leg card's `⋯` menu, changes the price and taps `Save`
- **THEN** the execution is updated via the same mutation as the desktop row and the card returns to read mode

#### Scenario: Deleted legs can be restored on mobile
- **WHEN** `Show deleted` is active and the user taps `Restore` on a deleted leg card
- **THEN** the leg is restored and rendered as an active card

### Requirement: Hover-only controls are visible on touch viewports
Below `lg`, controls in the Trade Detail page that are revealed only on hover on desktop SHALL be permanently visible: the journal `Edit` button in the Qualitative Analysis panel, the screenshot delete and zoom controls in the Screenshots tab, and the quick-note action buttons. On `lg+` the existing hover behavior SHALL remain.

#### Scenario: Journal edit button is tappable on mobile
- **WHEN** the journal is shown in preview mode on a mobile viewport
- **THEN** the journal `Edit` button is visible without hovering and switches the journal to write mode when tapped

#### Scenario: Screenshot can be deleted on mobile
- **WHEN** the user views the Screenshots tab on a mobile viewport
- **THEN** each screenshot shows its delete control without hovering
