## ADDED Requirements

### Requirement: Mobile chart maximize and restore
On viewports below `lg` (`< 1024px`), the Media & Charts card (`MediaChartsCard`) SHALL display a `Maximize chart` icon button (`aria-label="Maximize chart"`, `lg:hidden`) right-aligned in the card's tab bar when the `Chart` tab is active. On `lg+` viewports, or when the `Screenshots` tab is active, the maximize button SHALL NOT be rendered.

Activating `Maximize chart` SHALL expand the existing `MediaChartsCard` instance in-place into a full-viewport modal overlay (`fixed inset-0 z-50 w-screen h-[100dvh]`, `role="dialog"`, `aria-modal="true"`, `aria-label="Maximized trade chart"`) without unmounting `TradeChart` or the TradingView fallback widget. While maximized:
- the top bar SHALL remain visible with a `Restore chart` button (`aria-label="Restore chart"`) that returns the card to its normal inline layout,
- background page scrolling SHALL be locked (`document.body.style.overflow = "hidden"`),
- pressing `Escape` SHALL restore the normal layout, and
- `←` / `→` keyboard trade navigation SHALL be suppressed by the dialog check.

#### Scenario: Maximizing and restoring the chart on mobile preserves chart state
- **WHEN** the user taps `Maximize chart` in the Media & Charts card on a mobile viewport (`< lg`)
- **THEN** the card expands in-place to fill the viewport (`role="dialog"`, `aria-modal="true"`), displays the `Restore chart` button, and keeps the same `TradeChart` instance mounted
- **AND WHEN** the user taps `Restore chart` (or presses `Escape`)
- **THEN** the card returns to its inline layout in the `Overview` pane at the same scroll position

#### Scenario: Maximize button is hidden on desktop and on Screenshots tab
- **WHEN** the user views the Trade Detail page on a desktop viewport (`lg+`) or switches to the `Screenshots` tab on mobile
- **THEN** the `Maximize chart` button is not visible

### Requirement: Collapsible Trade Detail panels
On all viewports (`< lg` and `lg+`), the following Trade Detail section cards SHALL provide a collapsible header toggle (`button` with `aria-expanded` and a chevron indicator) and SHALL start expanded by default when a trade is loaded:
1. `Performance` card (in the `Overview` pane / desktop right column)
2. `Execution Summary` card (`ExecutionSummaryCard`)
3. `Qualitative Analysis & Metadata` card (Playbook, Tags, Annotations)
4. `Journal` card (Markdown preview/editor and `Import Quick Notes` button)
5. `Quick Notes` card (`NoteList`, displaying the note count in the header when notes are loaded)

Collapsing a card SHALL hide its body via CSS (`hidden`) rather than unmounting its content, preserving any in-progress edits or draft state. When `Qualitative Analysis & Metadata` is collapsed, its header SHALL display a compact summary of assigned metadata (e.g., playbook assignment status, tag count, and annotation count).

#### Scenario: All panels start expanded by default
- **WHEN** a user opens `/dashboard/trades/[id]` on mobile or desktop
- **THEN** the `Performance`, `Execution Summary`, `Qualitative Analysis & Metadata`, `Journal`, and `Quick Notes` panels are all expanded (`aria-expanded="true"`)

#### Scenario: Collapsing Qualitative Analysis & Metadata on mobile brings Journal to the top
- **WHEN** the user opens the `Journal` tab on a mobile viewport and taps the `Qualitative Analysis & Metadata` header toggle
- **THEN** the Playbook, Tags, and Annotations fields are hidden (`aria-expanded="false"`), a compact metadata summary is shown in the header, and the `Journal` card moves directly below the collapsed header

#### Scenario: Collapsing a panel preserves unsaved draft state
- **WHEN** the user edits tags or journal text in the `Journal` pane and collapses the `Qualitative Analysis & Metadata` or `Journal` panel
- **THEN** the unsaved draft values and the `Unsaved changes` save bar remain intact and can still be saved

## MODIFIED Requirements

### Requirement: Trade Detail mobile layout reference
On viewports below `lg` (`< 1024px`), the Trade Detail page (`/dashboard/trades/[id]`) SHALL follow the reference wireframe below. On `lg+`, the desktop grid structure SHALL remain unchanged while sharing the separate `Journal` card and collapsible panel headers. The wireframe is the visual contract for implementation and UI review (mobile baseline viewport `375×812`).

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
| [ Chart | Screenshots (2) ]        [⛶]  |   [⛶] Maximize chart (< lg)
| +--------------------------------------+ |
| |                                      | |
| |     Trade chart (min-h 360)          | |
| |                                      | |
| +--------------------------------------+ |
+------------------------------------------+
| ▾ PERFORMANCE                            |   collapsible (default expanded)
| Stop Loss       ✎ | Take Profit      ✎   |
| $178.00           | Add...               |
| Initial Risk      | Planned RRR          |
| $440.00           | 1 : 2.10             |
| Gross P&L         | Net P&L              |
| +$420.00          | +$412.50             |
+------------------------------------------+
| ▾ EXECUTION SUMMARY (2-column grid)      |   collapsible (default expanded)
+------------------------------------------+

Tab "Journal"
+------------------------------------------+
| ▾ QUALITATIVE ANALYSIS & METADATA        |   collapsible (default expanded)
| Playbook   [Breakout                  v] |
| Tags       [FOMO x] [Patient x] [+ Add]  |
| Annotations                              |
|   Setup quality   [A          v]         |
|   Mood (1-5)      [ 4 ]                  |
+------------------------------------------+
| ▾ JOURNAL                     [ ✎ Edit ] |   collapsible separate card
| +--------------------------------------+ |
| | ## Entry                             | |
| | Waited for the retest...             | |
| +--------------------------------------+ |
+------------------------------------------+
| ▾ QUICK NOTES (2)                        |   collapsible (default expanded)
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

#### Scenario: Desktop layout preserves grid structure
- **WHEN** a user opens `/dashboard/trades/[id]` on a viewport `lg` or wider
- **THEN** the desktop layout (header, chart + performance grid, execution summary, qualitative metadata card, journal card, quick notes card, execution legs table) is rendered with collapsible section headers and the mobile segmented switcher is not visible

### Requirement: Journal pane with sticky save bar
Below `lg`, the `Journal` pane SHALL contain the `Qualitative Analysis & Metadata` card (Playbook, Tags, Annotations) and the `Journal` card (Markdown journal preview/editor and Quick Notes import) followed by the `Quick Notes` card (when the `enable_quick_notes` feature flag is enabled). While `QualitativeMetadataPanel` has unsaved changes ( across Playbook, Tags, Annotations, or Journal), below `lg`:
- the `Journal` tab SHALL display an unsaved-changes dot indicator, and
- the `Unsaved changes` label with `Cancel` and `Save` buttons SHALL render in a bar fixed to the bottom of the viewport (respecting the device safe-area inset) instead of the panel header.

#### Scenario: Save bar appears when journal is dirty
- **WHEN** the user changes the playbook, tags, annotations or journal text on a mobile viewport
- **THEN** a fixed bottom bar with `Unsaved changes`, `Cancel` and `Save` appears and the `Journal` tab shows a dot indicator

#### Scenario: Save from the bottom bar
- **WHEN** the user taps `Save` in the fixed bottom bar
- **THEN** the changes are persisted exactly as with the desktop `Save` button and the bar and the tab indicator disappear
