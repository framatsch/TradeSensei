## MODIFIED Requirements

### Requirement: User can create a daily check-in
The system MUST allow users to create a daily check-in that captures pre/post-market sentiment, playbook adherence, custom metrics, and multiple associated market indices.

#### Scenario: User creates a check-in with multiple market indices
- **WHEN** the user submits a check-in form with an array of `target_index_ids`
- **THEN** the system validates the IDs belong to the user, saves the check-in, and creates the appropriate junction table associations

#### Scenario: User creates a check-in without market indices
- **WHEN** the user submits a check-in form with an empty `target_index_ids` array
- **THEN** the system saves the check-in successfully without any index associations

### Requirement: User can update a daily check-in
The system MUST allow users to update an existing daily check-in, including modifying the list of associated market indices.

#### Scenario: User updates target indices on an existing check-in
- **WHEN** the user edits a check-in, adding new IDs to `target_index_ids` and removing others
- **THEN** the system synchronizes the junction table to reflect the exact provided array of IDs
