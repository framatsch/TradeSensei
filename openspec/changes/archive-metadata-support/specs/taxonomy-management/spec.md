## ADDED Requirements

### Requirement: Cascade Hard-Deletion with Danger Zone
The system SHALL support cascading hard-deletion for taxonomies (tags) with active assignments, secured by text-typing validation inside a frontend Danger Zone.

#### Scenario: Deleting taxonomy with assignments
- **WHEN** user initiates delete on a taxonomy with active assignments, is shown the Danger Zone warning, types the exact tag name, and confirms
- **THEN** system SHALL cascade delete all intermediate trade, check-in, and playbook association rows and permanently hard-delete the taxonomy definition
