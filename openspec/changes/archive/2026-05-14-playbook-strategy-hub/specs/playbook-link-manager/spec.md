## ADDED Requirements

### Requirement: Add labeled external link to playbook
The system SHALL allow adding a labeled external URL to a playbook. Each link has a required `label` (display name) and a required `url`.

#### Scenario: Successful addition
- **WHEN** a POST request provides a valid `label` (non-empty, max 200 chars) and HTTP/HTTPS `url` for an owned playbook
- **THEN** the system creates a `playbook_links` row and returns 201 with `id`, `label`, `url`, `created_at`

#### Scenario: Invalid URL rejected
- **WHEN** a POST request provides a `url` that is not a valid HTTP/HTTPS URL
- **THEN** the system returns 422

#### Scenario: Missing label rejected
- **WHEN** a POST request omits `label` or provides an empty string
- **THEN** the system returns 422

#### Scenario: Playbook not owned by user
- **WHEN** the request targets a playbook not owned by the authenticated user
- **THEN** the system returns 404

### Requirement: List links for playbook
The system SHALL return all labeled links for a playbook.

#### Scenario: Returns link list
- **WHEN** a GET request is sent for links of an owned playbook
- **THEN** the system returns 200 with a list of `id`, `label`, `url`, `created_at` ordered by `created_at` ascending

#### Scenario: Returns empty list when no links
- **WHEN** a GET request is sent for a playbook with no links
- **THEN** the system returns 200 with an empty list

### Requirement: Delete playbook link
The system SHALL allow deleting a link from a playbook.

#### Scenario: Successful deletion
- **WHEN** a DELETE request targets an existing link on an owned playbook
- **THEN** the link row is removed and the system returns 204

#### Scenario: Link not found returns 404
- **WHEN** a DELETE request targets a link ID that does not exist on the playbook
- **THEN** the system returns 404

#### Scenario: Links cascade-deleted on playbook delete
- **WHEN** a playbook is deleted
- **THEN** all `playbook_links` rows for that playbook are removed (CASCADE)
