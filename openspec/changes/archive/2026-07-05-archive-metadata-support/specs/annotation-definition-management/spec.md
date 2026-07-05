## ADDED Requirements

### Requirement: Cascade Hard-Deletion with Danger Zone
The system SHALL support cascading hard-deletion for annotation definitions (metrics) with active assignments, secured by text-typing validation inside a frontend Danger Zone.

#### Scenario: Deleting metric with assignments
- **WHEN** user initiates delete on a metric with active assignments, is shown the Danger Zone warning, types the exact metric name, and confirms
- **THEN** system SHALL cascade delete all intermediate trade and check-in association rows and permanently hard-delete the annotation definition
