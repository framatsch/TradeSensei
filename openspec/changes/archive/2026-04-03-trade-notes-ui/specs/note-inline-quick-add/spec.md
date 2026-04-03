## ADDED Requirements

### Requirement: Inline quick-note in trade table
The system SHALL allow users to add a new note to a trade directly from the trade list row, without navigating to the trade detail page.

Each trade row in `TradeTable` SHALL show a note icon button. Clicking the icon SHALL expand an inline `QuickNoteInput` below the row. The `QuickNoteInput` SHALL have a single textarea and a "Save" button. On save, the note is created via `POST /trades/{id}/notes` and the expanded row is collapsed.

The note icon SHALL show a visual indicator (e.g., badge or filled vs. outline icon) when the trade already has one or more notes.

#### Scenario: Note icon expands inline input
- **WHEN** the user clicks the note icon on a trade row
- **THEN** a textarea and "Save" button appear directly below that row in the table

#### Scenario: Saving a quick note creates the note
- **WHEN** the user types content and clicks "Save"
- **THEN** the note is created via the API, the row collapses, and the note icon updates to reflect the trade now has notes

#### Scenario: Empty quick note cannot be saved
- **WHEN** the textarea is empty and the user clicks "Save"
- **THEN** the button is disabled and no API request is made

#### Scenario: Note icon shows indicator when notes exist
- **WHEN** a trade has one or more existing notes
- **THEN** the note icon in the trade row shows a filled/colored indicator distinguishing it from trades with no notes
