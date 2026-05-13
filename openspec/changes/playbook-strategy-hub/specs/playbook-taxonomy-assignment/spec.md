## ADDED Requirements

### Requirement: Assign taxonomy to playbook
The system SHALL allow assigning a non-archived taxonomy with `scope = playbook` or `scope = both` to a playbook owned by the authenticated user.

#### Scenario: Successful assignment
- **WHEN** a POST request assigns a non-archived taxonomy with `scope = playbook` or `scope = both` to a playbook
- **THEN** the system creates the assignment and returns 201 with `playbook_id` and `taxonomy_id`

#### Scenario: Scope mismatch rejected — trades scope
- **WHEN** a POST request attempts to assign a taxonomy with `scope = trades` to a playbook
- **THEN** the system returns 422 with a message indicating scope mismatch

#### Scenario: Scope mismatch rejected — checkins scope
- **WHEN** a POST request attempts to assign a taxonomy with `scope = checkins` to a playbook
- **THEN** the system returns 422 with a message indicating scope mismatch

#### Scenario: Archived taxonomy rejected
- **WHEN** a POST request attempts to assign a taxonomy with `is_archived = true` to a playbook
- **THEN** the system returns 422

#### Scenario: Duplicate assignment rejected
- **WHEN** a POST request assigns a taxonomy that is already assigned to the same playbook
- **THEN** the system returns 409 Conflict

#### Scenario: Assignment restricted to owning user
- **WHEN** a POST request assigns a taxonomy to a playbook not owned by the authenticated user
- **THEN** the system returns 404

#### Scenario: Assignment cascade-deleted on playbook delete
- **WHEN** a playbook is deleted
- **THEN** all `playbook_taxonomies` rows for that playbook are also deleted (CASCADE)

### Requirement: List taxonomy assignments for playbook
The system SHALL return all taxonomy assignments for a playbook owned by the authenticated user.

#### Scenario: Returns assigned taxonomies
- **WHEN** a GET request is sent for taxonomy assignments of an owned playbook
- **THEN** the system returns 200 with a list of taxonomy objects including `id`, `name`, `scope`, `color_hex`, `icon_identifier`

#### Scenario: Returns empty list when none assigned
- **WHEN** a GET request is sent for a playbook with no taxonomy assignments
- **THEN** the system returns 200 with an empty list

### Requirement: Remove taxonomy assignment from playbook
The system SHALL allow removing a taxonomy assignment from a playbook.

#### Scenario: Successful removal
- **WHEN** a DELETE request targets an existing playbook-taxonomy assignment
- **THEN** the assignment row is removed and the system returns 204

#### Scenario: Non-existent assignment returns 404
- **WHEN** a DELETE request targets a taxonomy not assigned to the playbook
- **THEN** the system returns 404
