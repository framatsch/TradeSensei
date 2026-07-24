## ADDED Requirements

### Requirement: Link Trade To Playbook
The system SHALL provide an MCP tool `link_trade_playbook` that sets or clears the linked playbook of a trade owned by the authenticated user. Setting requires a `playbook_id` that also belongs to the user; clearing removes the existing link.

#### Scenario: Link an owned trade to an owned playbook
- **WHEN** the authenticated user calls `link_trade_playbook` with an owned `trade_id` and an owned `playbook_id`
- **THEN** the system sets the trade's `playbook_id` to that playbook and returns the updated trade id and playbook id

#### Scenario: Clear a trade's playbook link
- **WHEN** the user calls `link_trade_playbook` with an owned `trade_id` and an explicit request to clear the link
- **THEN** the system sets the trade's `playbook_id` to null and returns the updated trade id with a null playbook id

#### Scenario: Link to a non-owned or unknown playbook
- **WHEN** the user calls `link_trade_playbook` with a `playbook_id` that does not belong to them or does not exist
- **THEN** the tool returns an error indicating the playbook was not found and the trade link is unchanged

#### Scenario: Link a non-owned or unknown trade
- **WHEN** the user calls `link_trade_playbook` with a `trade_id` that does not belong to them or does not exist
- **THEN** the tool returns an error indicating the trade was not found

### Requirement: Trade Playbook Link Audit Logging
The system SHALL emit an audit event when a trade's playbook link is set or cleared via MCP, recording only safe metadata (the trade identifier and the target playbook identifier or null).

#### Scenario: Audit event on link change
- **WHEN** `link_trade_playbook` successfully sets or clears a trade's playbook link
- **THEN** the system records a `trade.playbook_linked` audit event whose metadata contains the user id, trade id, and the resulting playbook id (or null)
