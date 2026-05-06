## ADDED Requirements

### Requirement: Centralized Help Dictionary
The system SHALL maintain a centralized, single-source dictionary for all help content in the platform.

#### Scenario: Dictionary access
- **WHEN** a component requests help content by a unique ID
- **THEN** the system SHALL return the corresponding label, summary, and detail text.

### Requirement: Playbook Help Content
The help dictionary SHALL include specific entries for Playbook features, including Playbook types, setup rules, and execution tracking.

#### Scenario: Playbook help lookup
- **WHEN** a user hovers over a "Playbook" help icon
- **THEN** the system SHALL display the "Playbook" summary from the centralized dictionary.

### Requirement: Portfolio Help Content
The help dictionary SHALL include specific entries for Portfolio features, including equity curves, risk allocation, and multi-account views.

#### Scenario: Portfolio help lookup
- **WHEN** a user hovers over a "Portfolio" help icon
- **THEN** the system SHALL display the "Portfolio" summary from the centralized dictionary.

### Requirement: Market Check-in Help Content
The help dictionary SHALL include specific entries for Market Check-in features, including pre-market bias, daily focus, and review cycles.

#### Scenario: Check-in help lookup
- **WHEN** a user hovers over a "Check-in" help icon
- **THEN** the system SHALL display the "Check-in" summary from the centralized dictionary.
