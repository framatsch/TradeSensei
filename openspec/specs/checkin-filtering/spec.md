## Purpose
Define how daily check-ins can be filtered by indexed market targets and media presence.

## Requirements

### Requirement: Filter Check-ins by Target Indices
The system SHALL allow users to filter their daily check-ins by one or more target indices (e.g. S&P 500).

#### Scenario: User filters check-ins by an index
- **WHEN** the user selects "S&P 500" from the target index filter dropdown
- **THEN** the system returns only check-ins that are linked to the "S&P 500" index

### Requirement: Filter Check-ins by Media Presence
The system SHALL allow users to filter their daily check-ins to only show entries that contain at least one screenshot/image attachment.

#### Scenario: User toggles "Has Media" filter
- **WHEN** the user toggles on the "Has Media" filter
- **THEN** the system returns only check-ins where `screenshot_keys` is not null and has a length > 0
