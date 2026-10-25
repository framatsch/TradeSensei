## MODIFIED Requirements

### Requirement: Notes field uses a Markdown editor
The Notes input in the Daily Check-in view SHALL be a Markdown editor rendered in the Left Main Pane of the check-in detail layout — not a plain narrow textarea. The editor SHALL support `Write`, `Preview`, and desktop `Split` (side-by-side Write + Preview) tabs using GitHub Flavored Markdown (`remark-gfm`) and HTML sanitization (`rehype-sanitize`), with a minimum height of `400px` and automatic vertical resizing in write mode.

#### Scenario: Markdown is rendered in preview mode
- **WHEN** the user switches to the Preview or Split tab or views the check-in in read mode
- **THEN** the notes content is rendered as formatted GFM Markdown (headings, bold, lists, tables, blockquotes)

#### Scenario: Markdown editor is the default input in edit mode
- **WHEN** the user opens the Daily Check-in form in edit mode
- **THEN** the Notes field renders as an auto-growing Markdown editor with Write, Preview, and Split tabs

## ADDED Requirements

### Requirement: Daily Check-in detail page uses unified full-width layout with right side pane and entry navigation
The system SHALL render `/dashboard/checkins/[date]` using the same full-width document-first layout as Playbook details (removing the narrow `max-w-3xl` wrapper):
1. A full-width **Header Card** containing:
   - Row 1: `Back to Timeline` link, the formatted date heading with `< Previous Entry` and `Next Entry >` navigation buttons (which navigate to the chronologically previous or next existing check-in entry and are disabled when no earlier/later entry exists), and action buttons (`Delete` and `Edit Check-in` in read mode; `Delete` [if existing], `Cancel`, `Save` [also bound to `Cmd/Ctrl + S`], and `Save & Close` in edit mode).
   - Row 2: `Target Market Indexes` pill bar (selectable toggle pills in edit mode; clickable badges with direct TradingView chart links in read mode).
2. On desktop viewports (`lg` and above), a two-column body (`flex-row gap-6`):
   - **Left Main Pane (`flex-1`)**: `Market Notes` card (Markdown document in read mode; auto-growing Markdown editor in edit mode).
   - **Right Side Pane (`w-[360px] xl:w-[420px]`)**: Three stacked cards in the exact same order as Playbooks:
     1. `Tags & Annotations` card (Check-in taxonomy tag pills and typed `AnnotationEditor` fields).
     2. `Screenshots & Charts` card (16:9 visual thumbnail grid with lightbox preview on click and `ScreenshotUploader` drop/paste zone in edit mode).
     3. `News Links` card (external news links list and URL add input in edit mode).

#### Scenario: User navigates to previous or next existing check-in entry from header
- **WHEN** the user clicks the `Previous Entry` or `Next Entry` button in the `/dashboard/checkins/[date]` header
- **THEN** the router navigates to `/dashboard/checkins/<adjacent-existing-entry-YYYY-MM-DD>`, and the button is disabled when no earlier or later check-in entry exists

#### Scenario: Action controls are accessible in the top header bar
- **WHEN** the user views or edits a daily check-in at `/dashboard/checkins/[date]`
- **THEN** the `Edit Check-in` button (in read mode) or `Save` and `Save & Close` buttons (in edit mode) are visible in the top header card without scrolling to the bottom of the page

#### Scenario: Clicking Save or pressing Cmd/Ctrl+S saves check-in and remains in edit mode
- **WHEN** the user clicks `Save` or presses `Cmd/Ctrl + S` in check-in edit mode
- **THEN** the check-in (including any buffered tags and annotations if newly created) is saved and the view remains in edit mode

#### Scenario: Clicking Save & Close saves check-in and returns to read mode
- **WHEN** the user clicks `Save & Close` in check-in edit mode
- **THEN** the check-in (including any buffered tags and annotations if newly created) is saved, `isEditMode` transitions to `false`, and `?edit=true` is removed from the URL

### Requirement: Daily Check-in mobile view provides a segmented switcher between Document and Details & Media
On viewports below `lg` (`< 1024px`), the `/dashboard/checkins/[date]` view SHALL render the same segmented 2-tab switcher (`Document` and `Details & Media` with a total item count badge) directly below the Header Card as Playbooks. Both panes SHALL remain mounted in the DOM so switching tabs preserves unsaved form state.

#### Scenario: Mobile defaults to Document tab and switches to Details & Media
- **WHEN** a user opens `/dashboard/checkins/[date]` on a mobile viewport (`< lg`)
- **THEN** the `Document` tab is active by default showing the `Market Notes` pane, and clicking `Details & Media` reveals the Side Pane (`Tags & Annotations`, `Screenshots & Charts`, `News Links`)
