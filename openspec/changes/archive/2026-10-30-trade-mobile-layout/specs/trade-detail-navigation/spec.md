## ADDED Requirements

### Requirement: Trade navigation layout reference
The Trade Detail page (`/dashboard/trades/[id]`) SHALL render Previous/Next trade navigation on all viewports according to the reference wireframes below. The mobile placement is defined in `trade-detail-mobile-ui` (Header Card row 1 and row 3).

```text
Desktop (lg+)
+--------------------------------------------------------------------------------+
| [<- Back to Trades]                        [‹ Previous]   3 / 128   [Next ›]   |   nav row
+--------------------------------------------------------------------------------+
| AAPL ⧉ [LONG] [STK]                         Final P&L   [Closed]   |  [⋯]      |   existing header
| Opened: Oct 24, 2026 9:41 AM • Closed: Oct 25, 2026 3:12 PM        |           |   (unchanged)
+--------------------------------------------------------------------------------+

Tooltips:  [‹ Previous]  →  "Previous: MSFT (←)"
           [Next ›]      →  "Next: TSLA (→)"
           3 / 128       →  "Position in your filtered trade list (View: Swing A+)"

Mobile (< lg) — see trade-detail-mobile-ui
+------------------------------------------+
| [<-]  AAPL ⧉             [‹] [›]  [⋯]   |
|       ...                        3 / 128 |
+------------------------------------------+

Without list context (deep link, other entry point)
+--------------------------------------------------------------------------------+
| [<- Back to Trades]                                                            |   no nav controls
+--------------------------------------------------------------------------------+
```

#### Scenario: Navigation controls on desktop
- **WHEN** a user opens a trade from the trades list on a `1440×900` viewport
- **THEN** the nav row shows `Back to Trades` on the left and `Previous`, the position indicator and `Next` on the right, and the existing header below is unchanged

### Requirement: Trade list context is stored in the browser session
Whenever the Trades list (`/dashboard/trades`) loads a page of trades, the system SHALL store a **trade list context** in `sessionStorage` (scoped to the browser tab, surviving reloads) containing: the active portfolio ID, the effective filters actually sent to the API (including the enforced status), the sort, the page size, the list URL query string (including `view_id`), the active saved-view name (if any), the total trade count, and for every loaded page its cursor, its ordered trade IDs and its next cursor.

When the filters, sort, page size or portfolio change, the stored context SHALL be replaced by a new context starting at page 1. Loading further pages of the same query SHALL append to the existing context. When the list refetches a page (e.g. after a bulk action), the stored IDs for that page SHALL be updated.

#### Scenario: Context is created from the list
- **WHEN** the user applies the filter `Winners`, sorts by `P&L: highest`, and the first page loads
- **THEN** `sessionStorage` contains a trade list context with these filters and sort, the total count, and page 1 with its ordered trade IDs

#### Scenario: Changing filters replaces the context
- **WHEN** the user has browsed to page 3 and then changes a filter
- **THEN** the stored context is replaced by a context containing only page 1 of the new filter

#### Scenario: Context is tab-scoped
- **WHEN** the user opens the app in a new browser tab
- **THEN** no trade list context from the other tab is available

### Requirement: Previous and Next trade navigation follows the stored list context
On the Trade Detail page, when a trade list context exists for the active portfolio and contains the current trade ID, the system SHALL show `Previous` and `Next` controls that navigate to the adjacent trade in the stored list order (`Previous` = the trade listed directly above, `Next` = the trade listed directly below, using the stored filters and sort):
- Within a page, the adjacent ID SHALL be taken from the stored page.
- At the first trade of a page, `Previous` SHALL use the last ID of the previous stored page.
- At the last trade of a page, `Next` SHALL load the next page using the stored next cursor, filters, sort and page size (via the same trades query as the list), append it to the context, and navigate to its first trade.
- `Previous` SHALL be disabled on the first trade of the list; `Next` SHALL be disabled on the last trade of the list (no next cursor). While the next page is loading, `Next` SHALL show a loading state.

Navigation SHALL replace the current history entry (`router.replace`), so the browser Back button returns to the page the user came from rather than stepping through every visited trade.

When no context exists, the context belongs to another portfolio, or the current trade ID is not part of the stored context, the `Previous`/`Next` controls and the position indicator SHALL NOT be rendered.

#### Scenario: Navigating to the next trade within a page
- **WHEN** the user is on the 3rd trade of the stored page 1 and clicks `Next`
- **THEN** the router replaces the URL with the 4th trade of page 1

#### Scenario: Navigating across a page boundary
- **WHEN** the user is on the last trade of the last stored page and a next cursor exists, and the user clicks `Next`
- **THEN** the next page is fetched with the stored filters and sort, appended to the context, and the user is taken to its first trade

#### Scenario: Previous across a page boundary
- **WHEN** the user is on the first trade of stored page 2 and clicks `Previous`
- **THEN** the user is taken to the last trade of stored page 1 without an additional list request

#### Scenario: Boundaries disable controls
- **WHEN** the user is on the first trade of the filtered list
- **THEN** `Previous` is disabled and `Next` is enabled

#### Scenario: Deep link without context
- **WHEN** the user opens `/dashboard/trades/<id>` directly in a new tab
- **THEN** neither `Previous`/`Next` nor the position indicator is rendered

#### Scenario: Trade not in context
- **WHEN** a trade list context exists but the user opens a trade that is not part of it (e.g. from a dashboard widget)
- **THEN** neither `Previous`/`Next` nor the position indicator is rendered

### Requirement: Position indicator shows place in the filtered list
When navigation controls are rendered, the system SHALL show a position indicator `<position> / <total>` between (desktop) or next to (mobile) the controls, where `position` is the 1-based index of the current trade across all stored pages and `total` is the stored total trade count. Its tooltip SHALL name the list source: the saved-view name if one is active, otherwise `Filtered trade list` when filters are active, otherwise `All trades`.

#### Scenario: Position on second page
- **WHEN** the page size is 20 and the user views the 5th trade of stored page 2 with a total of 128
- **THEN** the indicator reads `25 / 128`

### Requirement: Keyboard shortcuts for Previous and Next
On the Trade Detail page, pressing `ArrowLeft` SHALL trigger `Previous` and pressing `ArrowRight` SHALL trigger `Next`, with the same enabled/disabled rules as the buttons. The shortcuts SHALL NOT trigger when:
- focus is in an `input`, `textarea`, `select` or `contenteditable` element,
- any modifier key (`Alt`, `Ctrl`, `Meta`, `Shift`) is pressed,
- the event was already handled (`defaultPrevented`),
- a modal, dialog, dropdown menu or image lightbox is open.

The buttons' tooltips SHALL mention the shortcut and the adjacent trade's symbol when known (e.g. `Next: TSLA (→)`).

#### Scenario: Arrow key navigates
- **WHEN** the user presses `ArrowRight` on a trade detail page with an enabled `Next`
- **THEN** the user is taken to the next trade

#### Scenario: Arrow key ignored while typing
- **WHEN** the journal textarea or the stop-loss input has focus and the user presses `ArrowLeft`
- **THEN** the caret moves in the field and no navigation happens

#### Scenario: Arrow key ignored with open lightbox
- **WHEN** a screenshot lightbox or the `Correct Trade` modal is open and the user presses `ArrowRight`
- **THEN** no trade navigation happens

### Requirement: Unsaved journal changes are protected on navigation
When the Qualitative Analysis & Metadata panel has unsaved changes and the user triggers `Previous` or `Next` (button or keyboard), the system SHALL ask for confirmation (`Discard unsaved changes to this trade?`) before navigating. Cancelling SHALL keep the user on the current trade with the draft intact.

#### Scenario: Cancel keeps draft
- **WHEN** the journal has unsaved text, the user presses `ArrowRight` and cancels the confirmation
- **THEN** the user stays on the current trade and the unsaved text is still present

### Requirement: Back to Trades restores the list filters
When a trade list context exists for the active portfolio, the `Back to Trades` link (desktop and mobile) SHALL navigate to `/dashboard/trades` with the stored list URL query string, so filters, sort, page size and active saved view are restored. Without a context it SHALL link to `/dashboard/trades`.

#### Scenario: Returning to the filtered list
- **WHEN** the user opened a trade from a list filtered by `Winners` and sorted by P&L, navigated with `Next` twice, and clicks `Back to Trades`
- **THEN** the trades list opens with the `Winners` filter and P&L sort applied
