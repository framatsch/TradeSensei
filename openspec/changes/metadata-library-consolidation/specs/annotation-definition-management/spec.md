## ADDED Requirements

### Requirement: Annotation definition dropdown in Trade Detail filters by trades scope
The system SHALL filter annotation definition options shown in Trade Detail to only those with `scope = trades` or `scope = both`. Definitions scoped exclusively to check-ins SHALL NOT appear in Trade Detail forms.

#### Scenario: Trade Detail shows only trade-scoped annotation definitions
- **WHEN** the user opens the Trade Detail annotation/metrics section
- **THEN** only annotation definitions with `scope = trades` or `scope = both` are listed

#### Scenario: Check-in-only annotation hidden from Trade Detail
- **WHEN** an annotation definition exists with `scope = checkins`
- **THEN** it does NOT appear in the Trade Detail annotation selector
