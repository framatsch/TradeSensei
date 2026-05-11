## ADDED Requirements

### Requirement: Trade metadata assignable at creation time via two-step flow
The system SHALL support assigning taxonomies and annotation values during new trade creation via a two-step flow: (1) create the trade, (2) assign metadata in parallel. This is a frontend-only concern; the backend assignment endpoints remain unchanged.

#### Scenario: Taxonomy IDs assigned after trade creation
- **WHEN** the user creates a trade with one or more taxonomy IDs selected in the form
- **THEN** after the `POST /api/v1/trades` call returns 201, the system calls `POST /api/v1/trades/{id}/taxonomies` for each selected taxonomy ID
- **THEN** the user is navigated to the trade detail page after all calls complete (or fail non-fatally)

#### Scenario: Annotation values assigned after trade creation
- **WHEN** the user creates a trade with annotation values filled in
- **THEN** after the `POST /api/v1/trades` call returns 201, the system calls `POST /api/v1/trades/{id}/annotations/{definition_id}` for each non-empty annotation value
- **THEN** the user is navigated to the trade detail page after all calls complete (or fail non-fatally)

#### Scenario: Metadata assignment failure is non-fatal
- **WHEN** one or more metadata assignment calls fail after a successful trade creation
- **THEN** the user is still navigated to the trade detail page
- **THEN** a non-blocking error notification is shown indicating partial metadata assignment failure
