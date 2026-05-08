## UI Mockup

```
=== CHECKIN SIDEBAR (persistent) ===
+-----------------------------+
| < May 2026 >                |
| Mo Tu We Th Fr Sa Su        |
|  -  -  -  -  1  2  3●      |
|  4  5  6  7  8  9  10      |
|  ...                        |
| (● = regime-color dot)      |
|-----------------------------|
| [ Timeline ] [ Model Book ] |
+-----------------------------+

=== TIMELINE VIEW (/dashboard/checkins) ===
+------------------------------------------------------------------+
| [ 🍱 ] > MARKET CHECK-IN              Portfolio: [ Default ▼ ]   |
+-----------------------------+------------------------------------+
| < May 2026 >                | [ BULLISH ●] [SIDEWAYS ●] [...]    |
| Mo Tu We Th Fr Sa Su        |                                    |
|  1  2  3● 4  5  6  7        | === May 3, 2026 ===                 |
|  ...                        | +-------+  ### FOMC Aftermath       |
|-----------------------------|  | THUMB |  Market reacted to 50bps |
| [ Timeline ] [ Model Book ] | +-------+  Focus: 9/10             |
+-----------------------------+                                    |
                               | === May 2, 2026 ===               |
                               | +-------+  ### Quiet day          |
                               | | THUMB |  Missed setup.          |
                               +-------+                           |
+------------------------------------------------------------------+

=== MODEL BOOK VIEW (/dashboard/checkins?view=modelbook) ===
+------------------------------------------------------------------+
| [ ▼ Filters: Date Range | Regime ]    [ Items per page: 24 ▼ ]   |
|                                                                  |
| +------------------+ +------------------+ +------------------+  |
| |                  | |                  | |                  |  |
| |  LARGE THUMBNAIL | |  LARGE THUMBNAIL | |  LARGE THUMBNAIL |  |
| |   (click→expand) | |   (click→expand) | |   (click→expand) |  |
| |                  | |                  | |                  |  |
| +------------------+ +------------------+ +------------------+  |
|  May 3 • Bullish        May 2 • Sideways    May 1 • Bearish      |
|                                                                  |
|         < 1 2 3 >                                                |
+------------------------------------------------------------------+
```

**Key layout rules from mockup:**
- Checkin sidebar is ~220px wide, always visible on desktop on all `/dashboard/checkins` routes.
- Global sidebar is hidden on all `/dashboard/checkins` routes.
- Sidebar top: mini-calendar (month navigation, day grid, regime-color dots).
- Sidebar bottom: view toggle buttons (Timeline | Model Book).
- Regime filter pills appear at the top of the main content area — styled with `color_hex`.
- Timeline: card-per-day layout with thumbnail on left, Markdown text on right.
- Model Book: responsive grid (3-col desktop, 2-col tablet), thumbnails only, text hidden.
- Lightbox opens on thumbnail click for both views.
- No full-resolution images ever rendered in list/grid views.

## Requirements

### Requirement: Checkin pillar has a dedicated layout that hides the global sidebar
When any `/dashboard/checkins` route is active, the global `DashboardLayout` sidebar SHALL be hidden and replaced by the `CheckinSidebar`.

#### Scenario: Global sidebar is hidden on checkin routes
- **WHEN** the user navigates to `/dashboard/checkins`
- **THEN** the global navigation sidebar is not rendered
- **AND** the `CheckinSidebar` is rendered in its place

### Requirement: CheckinSidebar contains a mini-calendar and view toggles
The sidebar SHALL render a month mini-calendar and a view-mode toggle section.

#### Scenario: Mini-calendar shows days with check-in indicators
- **WHEN** the user views the CheckinSidebar for a given month
- **THEN** days that have saved check-ins display a colored dot indicator
- **AND** the dot color matches the `MarketRegimeDefinition.color_hex` of that day's regime
- **AND** days without check-ins display no indicator

#### Scenario: Mini-calendar month navigation
- **WHEN** the user clicks the `<` or `>` arrows in the mini-calendar
- **THEN** the calendar advances to the previous or next month
- **AND** the `month` URL param is updated (format: `YYYY-MM`)

#### Scenario: Clicking a calendar day navigates to that check-in
- **WHEN** the user clicks a day that has a check-in dot
- **THEN** the browser navigates to `/dashboard/checkins/{YYYY-MM-DD}`

#### Scenario: View toggle buttons switch the active view mode
- **WHEN** the user clicks "Timeline"
- **THEN** the `view` URL param is set to `timeline` and the Timeline view renders
- **WHEN** the user clicks "Model Book"
- **THEN** the `view` URL param is set to `modelbook` and the Model Book view renders
- **AND** the active toggle button is visually highlighted

### Requirement: Regime filter pills appear in the main content area
A row of `MarketRegimeDefinition` pills SHALL appear above the content in both views.

#### Scenario: Regime pills are styled with color_hex
- **WHEN** the page renders
- **THEN** each active regime pill displays with a border or background derived from its `color_hex`
- **AND** clicking a pill sets the `regime` URL param to that regime's ID
- **AND** clicking the active pill again clears the `regime` URL param

### Requirement: Timeline view renders entries as text-first cards with inline thumbnails
The Timeline view SHALL display check-in entries in reverse-chronological order.

#### Scenario: Timeline entry structure
- **WHEN** the user is in Timeline view
- **THEN** each entry shows the date heading, regime pill, Markdown notes rendered as HTML, and screenshots as small thumbnails (max 120px wide)
- **AND** thumbnails use `loading="lazy"` and are capped at their display size (no full-res download)

#### Scenario: Thumbnail click opens Lightbox
- **WHEN** the user clicks a thumbnail in Timeline view
- **THEN** an overlay Lightbox opens showing the full-resolution image
- **AND** pressing Escape or clicking outside closes the Lightbox

### Requirement: Model Book view renders a paginated image grid
The Model Book view SHALL display screenshots as large thumbnails in a responsive grid.

#### Scenario: Model Book grid layout
- **WHEN** the user is in Model Book view
- **THEN** screenshots are displayed in a 3-column grid (desktop) or 2-column grid (tablet)
- **AND** Markdown text is NOT rendered (hidden)
- **AND** each card shows only the thumbnail, date, and regime label below

#### Scenario: Model Book collapsible filter panel
- **WHEN** the user clicks "▼ Filters" in Model Book view
- **THEN** the filter panel expands showing Date Range pickers and Regime selector
- **AND** changes are reflected in the URL params

#### Scenario: Model Book pagination
- **WHEN** the Model Book has more items than the selected `per_page` value
- **THEN** pagination controls are shown (prev/next, page numbers)
- **AND** `page` and `per_page` URL params are updated on navigation
- **AND** `per_page` options are: 12, 24, 48

#### Scenario: Page resets to 1 when filter changes
- **WHEN** the user changes the regime or date range filter
- **THEN** the `page` URL param resets to 1

#### Scenario: Model Book thumbnail click opens Lightbox
- **WHEN** the user clicks a thumbnail in Model Book view
- **THEN** the Lightbox opens with the full-resolution image

### Requirement: Lightbox displays full-resolution image in an overlay
The Lightbox SHALL render as a full-screen overlay modal.

#### Scenario: Lightbox renders full-resolution image
- **WHEN** the Lightbox is open
- **THEN** it renders the image at its natural/full resolution within the viewport
- **AND** the surrounding page is dimmed

#### Scenario: Lightbox closes on Escape or backdrop click
- **WHEN** the user presses Escape or clicks outside the image
- **THEN** the Lightbox closes

### Requirement: Global color coding applies color_hex consistently
`MarketRegimeDefinition.color_hex` MUST be applied to: calendar day dots, active regime pill (border/background), timeline card left accent border, Model Book card top accent border.

#### Scenario: Color hex is applied to all four surfaces
- **WHEN** a check-in with a regime is rendered
- **THEN** the timeline card has a left border in `color_hex`
- **AND** the Model Book card has a top border in `color_hex`
- **AND** the calendar dot matches `color_hex`
- **AND** the regime pill uses `color_hex` for its border

### Requirement: Check-in form dynamically renders fields from CheckinFieldDefinition
The form for creating/editing a check-in SHALL render inputs based on active `CheckinFieldDefinition` records.

#### Scenario: Integer fields render as sliders
- **WHEN** an active `CheckinFieldDefinition` has `field_type === 'integer'`
- **THEN** a range slider (min: 1, max: 10) is rendered with the field's label
- **AND** the value is stored in `custom_metrics[field_name]`

#### Scenario: Boolean fields render as toggles
- **WHEN** an active `CheckinFieldDefinition` has `field_type === 'boolean'`
- **THEN** a toggle switch is rendered with the field's label
- **AND** the value is stored in `custom_metrics[field_name]`

### Requirement: All filter/view state is URL-synced
All operative state in the Check-in pillar SHALL be reflected in URL search parameters.

#### Scenario: URL params are preserved on reload
- **WHEN** the user sets view=modelbook, regime=bullish, page=2
- **THEN** reloading the page restores the same view, filter, and pagination state
