## ADDED Requirements

### Requirement: Taxonomy dropdown in Trade Detail filters by trades scope
The system SHALL filter taxonomy options shown in Trade Detail's multi-select to only taxonomies with `scope = trades` or `scope = both`. Taxonomies scoped exclusively to check-ins SHALL NOT appear in the Trade Detail form.

#### Scenario: Trade Detail shows only trade-scoped taxonomies
- **WHEN** the user opens the Trade Detail and expands the taxonomy/tags multi-select
- **THEN** only taxonomies with `scope = trades` or `scope = both` are shown as options

#### Scenario: Check-in-only taxonomy hidden from Trade Detail
- **WHEN** a taxonomy exists with `scope = checkins`
- **THEN** it does NOT appear in the Trade Detail taxonomy selector
