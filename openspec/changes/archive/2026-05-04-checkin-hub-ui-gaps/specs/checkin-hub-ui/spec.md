## ADDED Requirements

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
