## ADDED Requirements

### Requirement: Library Metrics tab manages annotation definitions
The system SHALL provide a `/dashboard/library/metrics` route rendering an Annotation Manager that lists all non-archived annotation definitions and allows creating, editing, and archiving them.

#### Scenario: List non-archived annotation definitions
- **WHEN** the user navigates to Library > Metrics
- **THEN** all non-archived annotation definitions are shown, each displaying name, type badge, scope badge, optional description, and optional icon identifier

#### Scenario: Create annotation definition
- **WHEN** the user fills in name, type, and scope and submits the "New Metric" form
- **THEN** a new annotation definition is created and immediately appears in the list

#### Scenario: Type selector shows four options
- **WHEN** the create form is open
- **THEN** a type selector is visible with options: "Integer", "Float", "Boolean", "Enum"

#### Scenario: Scale labels shown only for Enum type
- **WHEN** the user selects type "Enum"
- **THEN** a scale_labels input is revealed allowing the user to define allowed string values

#### Scenario: Archive annotation definition
- **WHEN** the user archives a definition with existing assignments
- **THEN** the definition is soft-deleted and disappears from the active list

#### Scenario: Hard-delete definition when unused
- **WHEN** the user deletes a definition with no assignments
- **THEN** the definition is permanently removed from the database
