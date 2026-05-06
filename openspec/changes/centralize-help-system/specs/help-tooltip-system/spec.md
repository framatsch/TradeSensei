## ADDED Requirements

### Requirement: Reusable Hover-Card Tooltips
The system SHALL provide a reusable `HelpTooltip` component that displays help content from the centralized dictionary on hover.

#### Scenario: Tooltip display on hover
- **WHEN** a user hovers over the `HelpTooltip` component
- **THEN** a hover-card SHALL appear showing the summary text of the metric or feature.

### Requirement: Link to Full Documentation
The `HelpTooltip` component SHALL include a link or button to open the full help page at the relevant anchor.

#### Scenario: Navigation to full help
- **WHEN** a user clicks the "Read more" link in the hover-card
- **THEN** the system SHALL navigate to the `/help#anchor` page in the current or new window.
