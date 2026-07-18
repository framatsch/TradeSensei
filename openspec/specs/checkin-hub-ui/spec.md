## Purpose
Market check-in pillar for tradesensei: the dedicated `/dashboard/checkins` view for logging daily market context, sentiment, and behavioral notes, decoupled from trade execution data.

## UI Mockup — Market Check-in Pillar (`/dashboard/checkins`)

The prompt does not provide an ASCII mockup for this pillar, but specifies the following UI
components which together define the layout:

```
+---------------------------------------------------------------------------------+
| [ 🍱 ] > MARKET CHECK-IN                            Portfolio: [ Default ▼ ]   |
+----------------------+----------------------------------------------------------+
| [timeline / dates]   |  DATE: 03.05.2026                                        |
|                      |                                                          |
|                      |  Market Regime:                                          |
|                      |  [ Bullish ] [ Bearish ] [ Sideways ] [ Volatile ]       |
|                      |  (color-coded pill buttons, selected = highlighted)      |
|                      |                                                          |
|                      |  Notes:  [ Write | Preview ]                             |
|                      |  +----------------------------------------------------+ |
|                      |  | ## Today's market context...                       | |
|                      |  | (Markdown editor)                                  | |
|                      |  +----------------------------------------------------+ |
|                      |                                                          |
|                      |  Screenshots:  [ + Upload ]                              |
|                      |  [ 🖼 thumb1 ×] [ 🖼 thumb2 ×]                           |
|                      |                                                          |
|                      |  News Links: [ https://... ] [+]                         |
|                      |  Custom Metrics: mood-level [3]  rule-followed [✓]       |
|                      |                                                          |
|                      |  [ Save Check-in ]          [ Delete ]                  |
+----------------------+----------------------------------------------------------+
```

**Key layout rules from prompt:**
- Regime selection: color-coded **pill buttons** (not a `<select>` dropdown)
- Notes: **Markdown editor** with Write/Preview tab toggle
- Screenshots: **two-step upload** — select file → presigned PUT → render thumbnail
## Requirements
### Requirement: Notes field uses a Markdown editor
The Notes input in the Daily Check-in form SHALL be a Markdown editor — not a plain textarea. The editor SHALL support a split or tabbed view (Write / Preview) so the user can toggle between editing raw Markdown and seeing the rendered output.

#### Scenario: Markdown is rendered in preview mode
- **WHEN** the user switches to the Preview tab
- **THEN** the notes content is rendered as formatted Markdown (headings, bold, lists, etc.)

#### Scenario: Markdown editor is the default input
- **WHEN** the user opens the Daily Check-in form
- **THEN** the Notes field renders as a Markdown editor, not a plain textarea

### Requirement: Market Regime selection uses color-coded pill buttons
The Market Phase (Market Regime) selection SHALL be rendered as a row of color-coded pill/badge buttons, not a `<select>` dropdown. Each pill SHALL display the phase label and use the phase's `color_hex` for its accent color. The selected pill SHALL be visually highlighted.

#### Scenario: Regime pills are rendered from active market phases
- **WHEN** the user opens the Daily Check-in form
- **THEN** one pill button is shown per active `MarketPhaseDefinition`, styled with its `color_hex`

#### Scenario: Clicking a pill selects the regime
- **WHEN** the user clicks a regime pill
- **THEN** that pill is highlighted as active and the `market_phase` value is set to the phase's `name`

#### Scenario: Clicking the active pill deselects it
- **WHEN** the user clicks the currently selected regime pill
- **THEN** the selection is cleared (`market_phase` becomes null)

### Requirement: Two-step screenshot upload flow
The Daily Check-in form SHALL provide a screenshot upload UI. Step 1: the user selects or drops an image file, the frontend requests a presigned PUT URL from `POST /api/v1/checkins/screenshot-upload-url`, then uploads the file directly to S3. Step 2: after successful upload, the public URL is appended to `screenshot_urls` and rendered as a thumbnail preview in the form.

#### Scenario: User uploads a screenshot
- **WHEN** the user selects an image file in the screenshot upload area
- **THEN** the frontend requests a presigned URL, uploads the file to S3, and adds the returned public URL to the form state

#### Scenario: Uploaded screenshots appear as thumbnails
- **WHEN** at least one screenshot URL is in the form state
- **THEN** each screenshot is rendered as a small thumbnail with a remove button

#### Scenario: Screenshot can be removed before saving
- **WHEN** the user clicks the remove button on a screenshot thumbnail
- **THEN** that URL is removed from the form state (it is NOT deleted from S3)

#### Scenario: Storage not configured — upload button is disabled
- **WHEN** the backend returns HTTP 503 for the presigned URL request
- **THEN** the upload area shows a "Screenshot upload unavailable" message and disables the upload input

### Requirement: Check-in sidebar renders mini calendar at top and view toggles at bottom
The Check-in sidebar SHALL render the mini month calendar in the upper section and the view-toggle buttons (Timeline / Model Book) in the lower section. The calendar SHALL be the first visible element inside the sidebar; the toggle buttons SHALL be the last.

#### Scenario: Calendar appears above view toggles on desktop
- **WHEN** the user views any check-in route on a desktop viewport
- **THEN** the mini calendar is rendered above the Timeline / Model Book toggle buttons in the sidebar

#### Scenario: Toggle buttons are at the bottom of the sidebar
- **WHEN** the user views any check-in route
- **THEN** the "Timeline" and "Model Book" buttons are the bottom-most elements of the sidebar

### Requirement: Mini calendar day click navigates to the check-in form for that date
Clicking a day in the mini calendar SHALL navigate the user to `/dashboard/checkins/[date]` where `[date]` is formatted as `YYYY-MM-DD`. That route SHALL render the check-in form pre-populated for the selected date, allowing the user to create or edit that day's entry.

#### Scenario: Clicking a day with an existing check-in opens the edit form
- **WHEN** the user clicks a day in the mini calendar that has a regime-color dot
- **THEN** the browser navigates to `/dashboard/checkins/YYYY-MM-DD`
- **AND** the form is pre-populated with the existing check-in data for that date

#### Scenario: Clicking a day without a check-in opens a blank form
- **WHEN** the user clicks a day in the mini calendar that has no regime-color dot
- **THEN** the browser navigates to `/dashboard/checkins/YYYY-MM-DD`
- **AND** the form is empty and ready for a new entry

#### Scenario: Non-existent date route does not produce a 404
- **WHEN** the user navigates directly to `/dashboard/checkins/2026-05-03`
- **THEN** the check-in form for that date is rendered without a 404 error

### Requirement: Timeline view screenshot thumbnails do not load full-resolution images
Screenshot thumbnails in the Timeline view SHALL be rendered at a maximum display width of 120px and SHALL NOT cause the browser to download the full-resolution source file. The frontend SHALL use Next.js `<Image>` with an explicit `width={120}` to trigger server-side image optimisation.

#### Scenario: Thumbnails are visually limited to 120px
- **WHEN** the user views the Timeline with check-in entries that have screenshots
- **THEN** each thumbnail is displayed at a maximum of 120px wide

#### Scenario: Thumbnail network request is for a resized image
- **WHEN** the browser fetches a thumbnail in the Timeline view
- **THEN** the network request is for an optimised/resized image variant, not the original full-resolution file

