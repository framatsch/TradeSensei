## ADDED Requirements

### Requirement: Expose Archive and Unarchive actions
The system SHALL support explicit Archive and Unarchive actions for both tags (taxonomies) and metrics (annotation definitions) inside their respective Details Panels.

#### Scenario: Archiving a tag
- **WHEN** user clicks "Archive" on an active tag inside the details panel
- **THEN** system SHALL set the tag's archived status to true and render it with an Archived badge

#### Scenario: Unarchiving a tag
- **WHEN** user clicks "Unarchive" on an archived tag inside the details panel
- **THEN** system SHALL set the tag's archived status to false and restore it to active status

### Requirement: Show Archived Filter Toggle
The system SHALL provide a "Show Archived" toggle in both global Library grids (Tags and Metrics) to show or hide archived definitions.

#### Scenario: Show Archived toggled off
- **WHEN** "Show Archived" toggle is off
- **THEN** system SHALL hide all archived tags and metrics from the Library grid lists

#### Scenario: Show Archived toggled on
- **WHEN** "Show Archived" toggle is on
- **THEN** system SHALL display both active and archived tags and metrics in the Library grid lists
