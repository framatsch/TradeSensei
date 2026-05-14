## MODIFIED Requirements

### Requirement: Taxonomy dropdown in Trade Detail filters by trades scope
The system SHALL filter taxonomy options shown in Trade Detail's multi-select to only taxonomies with `scope = trades` or `scope = both`. Taxonomies scoped exclusively to check-ins SHALL NOT appear in the Trade Detail form.

#### Scenario: Trade Detail shows only trade-scoped taxonomies
- **WHEN** the user opens the Trade Detail and expands the taxonomy/tags multi-select
- **THEN** only taxonomies with `scope = trades` or `scope = both` are shown as options

#### Scenario: Check-in-only taxonomy hidden from Trade Detail
- **WHEN** a taxonomy exists with `scope = checkins`
- **THEN** it does NOT appear in the Trade Detail taxonomy selector

#### Scenario: Playwright TC-077 uses taxonomy UI
- **WHEN** TC-077 runs to test inline tag editing in the trade detail
- **THEN** it interacts with the taxonomy multi-select (backed by `/api/v1/taxonomies`)
- **AND** no request is made to `/api/v1/tags`

#### Scenario: Playwright global-setup seeds taxonomies not legacy tags
- **WHEN** the global-setup runs before the E2E test suite
- **THEN** test taxonomies are created via `POST /api/v1/taxonomies` with `scope = trades`
- **AND** no requests are made to `POST /api/v1/tags`
