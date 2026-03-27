## ADDED Requirements

### Requirement: Optimistic playbook creation display
The system SHALL immediately display newly created playbooks in the playbook list without waiting for server confirmation.

#### Scenario: Playbook appears immediately after creation
- **WHEN** user creates a new playbook and the form submits
- **THEN** the new playbook appears in the playbook list instantly
- **AND** subsequent playbook creations show their results immediately (not delayed until next item is created)

#### Scenario: Optimistic state rolls back on error
- **WHEN** server rejects the playbook creation (e.g., validation error)
- **THEN** the optimistically added playbook is removed from the list
- **AND** user sees an error message

### Requirement: Optimistic tag creation display
The system SHALL immediately display newly created tags in the tag list without waiting for server confirmation.

#### Scenario: Tag appears immediately after creation
- **WHEN** user creates a new tag and the form submits
- **THEN** the new tag appears in the tag list instantly
- **AND** subsequent tag creations show their results immediately (not delayed until next item is created)

#### Scenario: Optimistic state rolls back on error
- **WHEN** server rejects the tag creation
- **THEN** the optimistically added tag is removed from the list
- **AND** user sees an error message

## MODIFIED Requirements

### Requirement: Filter trades by tags
The system SHALL allow users to filter trades by one or more tags.

#### Scenario: Apply tag filter
- **WHEN** user selects one or more tags in the trades filter panel
- **THEN** the trades table displays only trades matching those tags
- **AND** the URL is updated with tag_ids query parameters (e.g., `?tag_ids=1&tag_ids=2`)

#### Scenario: Clear tag filter
- **WHEN** user deselects all tags
- **THEN** the trades table shows all trades again
- **AND** tag_ids query parameters are removed from URL

#### Scenario: Tag filter loads with data
- **WHEN** the trades overview page loads
- **THEN** available tags are loaded and displayed in the filter panel
- **AND** while tags are loading, a "Loading tags..." indicator is shown

#### Scenario: Multiple tag selections work together
- **WHEN** user selects multiple tags simultaneously
- **THEN** trades matching ANY of the selected tags are displayed (OR logic)

### Requirement: Filter trades by account
The system SHALL allow users to filter trades by account, visible to all users regardless of account count.

#### Scenario: Account filter visible for all users
- **WHEN** the trades overview page loads
- **THEN** the account filter is displayed for users with 1 or more accounts
- **AND** the filter is not hidden based on account count

#### Scenario: Apply account filter
- **WHEN** user selects an account from the filter dropdown
- **THEN** the trades table displays only trades from that account
- **AND** the URL is updated with account_id query parameter

#### Scenario: Account filter loads with data
- **WHEN** the trades overview page loads
- **THEN** available accounts are loaded and displayed in the filter dropdown
- **AND** while accounts are loading, a "Loading accounts..." indicator is shown

### Requirement: Filter trades by playbook
The system SHALL allow users to filter trades by playbook (strategy) when playbooks exist.

#### Scenario: Playbook filter visible when playbooks exist
- **WHEN** the trades overview page loads and user has created playbooks
- **THEN** the playbook filter is displayed in the filter panel
- **AND** the filter is only shown when at least one playbook exists

#### Scenario: Apply playbook filter
- **WHEN** user selects a playbook from the filter dropdown
- **THEN** the trades table displays only trades linked to that playbook
- **AND** the URL is updated with playbook_id query parameter

#### Scenario: Clear playbook filter
- **WHEN** user deselects the playbook or selects "All playbooks"
- **THEN** the trades table shows all trades again
- **AND** playbook_id query parameter is removed from URL

#### Scenario: Playbook filter loads with data
- **WHEN** the trades overview page loads
- **THEN** available playbooks are loaded and displayed in the filter dropdown
- **AND** while playbooks are loading, a "Loading playbooks..." indicator is shown

### Requirement: Combined filtering on trades
The system SHALL support filtering trades by multiple filter types simultaneously.

#### Scenario: Apply multiple filters together
- **WHEN** user applies filters for account AND tags AND playbook
- **THEN** the trades table displays only trades matching ALL selected filters
- **AND** the URL contains all active filter parameters (e.g., `?account_id=1&tag_ids=2&playbook_id=3`)

#### Scenario: Clear one filter type
- **WHEN** user removes a single filter (e.g., clears tags but keeps account filter)
- **THEN** remaining filters continue to apply
- **AND** cleared filter parameters are removed from URL
