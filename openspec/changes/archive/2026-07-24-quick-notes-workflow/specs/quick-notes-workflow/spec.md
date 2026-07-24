## ADDED Requirements

### Requirement: Feature toggle for Quick Notes
The system SHALL allow users to enable or disable Quick Notes visibility via a per-user feature flag `enable_quick_notes` stored in `UserSettings.features`. The flag SHALL follow the existing convention where a missing flag reads as disabled; existing users SHALL be migrated to `enable_quick_notes = true` so current behavior is preserved.

#### Scenario: User disables Quick Notes
- **WHEN** the user sets `enable_quick_notes` to false in the Features settings tab
- **THEN** the Quick Notes count and inline add button in the TradeRow are hidden
- **AND** the Quick Notes list (NoteList) in Trade Details is hidden

#### Scenario: Existing user after migration
- **WHEN** a user that existed before this change loads the app
- **THEN** `enable_quick_notes` is `true` for them
- **AND** Quick Notes remain visible exactly as before

### Requirement: Rename main journal field to `journal`
The system SHALL rename the Trade main journal field `trade.notes` to `trade.journal` across the database column, ORM model, Trade Pydantic schemas, generated OpenAPI client, and frontend Trade types, to match the "Journal" UI label and remove the collision with the Quick Notes relationship `trade.trade_notes`. The rename SHALL be scoped to the Trade entity only and SHALL NOT affect `DailyCheckin.notes` or Quick Notes (`trade_notes` / `TradeNote`), which keep their current names.

#### Scenario: Developer fetches a trade
- **WHEN** fetching a trade from the API
- **THEN** the returned object exposes the main journal text as `journal` instead of `notes`
- **AND** the Quick Notes are still exposed as `trade_notes`

#### Scenario: Daily check-in is unaffected
- **WHEN** fetching a daily check-in from the API
- **THEN** its `notes` field is unchanged

### Requirement: Import Quick Notes into Journal
The system SHALL provide a button to import existing Quick Notes into the main draft Journal when editing a trade, and SHALL delete the imported Quick Notes only when the trade is saved.

#### Scenario: User imports Quick Notes
- **WHEN** the user clicks "Import Quick Notes" while editing the QualitativeMetadataPanel in write mode
- **THEN** the system records the IDs of the Quick Notes present at that moment
- **AND** formats them as Markdown bullet points, including the timestamp and the emotion when present
- **AND** appends them to the end of the journal draft textarea
- **AND** disables the "Import Quick Notes" button until the edit is saved or reset

#### Scenario: Imported Quick Notes are deleted on Save
- **WHEN** the user clicks "Save Trade" after importing Quick Notes
- **THEN** the draft journal text is persisted first
- **AND** only the Quick Notes whose IDs were recorded at import time are deleted
- **AND** Quick Notes created after the import are preserved

#### Scenario: User abandons the edit without saving
- **WHEN** the user imports Quick Notes but leaves without saving the trade
- **THEN** no Quick Notes are deleted
- **AND** the appended draft journal text is discarded

#### Scenario: Quick Note without an emotion
- **WHEN** a Quick Note has no emotion value
- **THEN** its imported bullet is formatted as `* **[HH:MM]** Content` without an empty emotion segment
