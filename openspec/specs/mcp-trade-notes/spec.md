# mcp-trade-notes Specification

## Purpose

MCP tools to add, edit, and delete a trade's timestamped quick notes, and to edit (replace/append) the trade's main journal `notes` field.

## Requirements

### Requirement: Append Trade Quick Note
The system SHALL provide an MCP tool `add_trade_note` that appends a new timestamped quick note (the trade's quick-note collection) to a trade owned by the authenticated user, accepting note content and an optional emotion label, and returning the created note's identifier and creation timestamp.

#### Scenario: Add a note to an owned trade
- **WHEN** the authenticated user calls `add_trade_note` with a `trade_id` that belongs to them and non-empty note content
- **THEN** the system creates a new trade note associated with that trade and the user, and returns the new note's id and created_at

#### Scenario: Add a note with an emotion label
- **WHEN** the user calls `add_trade_note` with valid content and an optional emotion value
- **THEN** the created note stores the provided emotion alongside the content

#### Scenario: Adding a note to a non-owned or unknown trade
- **WHEN** the user calls `add_trade_note` with a `trade_id` that does not belong to them or does not exist
- **THEN** the tool returns an error indicating the trade was not found and no note is created

### Requirement: Update Trade Quick Note
The system SHALL provide an MCP tool `update_trade_note` that edits an existing quick note owned by the authenticated user, identified by its note UUID and its parent trade UUID, allowing the content and/or the emotion label to be changed, and returning the updated note's identifier and update timestamp.

#### Scenario: Edit an owned quick note
- **WHEN** the authenticated user calls `update_trade_note` with a `trade_id` and `note_id` that belong to them and new content and/or emotion
- **THEN** the system updates the note's provided fields and returns the note id and updated_at

#### Scenario: Editing a non-owned or unknown quick note
- **WHEN** the user calls `update_trade_note` with a `note_id` that does not belong to them, does not exist, or does not belong to the given `trade_id`
- **THEN** the tool returns an error indicating the note was not found and nothing is changed

### Requirement: Delete Trade Quick Note
The system SHALL provide an MCP tool `delete_trade_note` that removes an existing quick note owned by the authenticated user, identified by its note UUID and its parent trade UUID.

#### Scenario: Delete an owned quick note
- **WHEN** the authenticated user calls `delete_trade_note` with a `trade_id` and `note_id` that belong to them
- **THEN** the system deletes the note and returns a success result

#### Scenario: Deleting a non-owned or unknown quick note
- **WHEN** the user calls `delete_trade_note` with a `note_id` that does not belong to them, does not exist, or does not belong to the given `trade_id`
- **THEN** the tool returns an error indicating the note was not found and nothing is deleted

### Requirement: Edit Trade Journal Notes
The system SHALL provide an MCP tool `update_trade_journal` that sets or appends to the main journal `notes` field of a single trade owned by the authenticated user. The tool SHALL accept a `mode` of `replace` (default) or `append`: `replace` overwrites the `notes` field; `append` adds the provided text to the end of any existing journal text.

#### Scenario: Replace the journal notes of an owned trade
- **WHEN** the authenticated user calls `update_trade_journal` with an owned `trade_id`, journal text, and mode `replace` (or no mode)
- **THEN** the trade's `notes` field is set to the provided text and the tool returns the trade id

#### Scenario: Append to the journal notes of an owned trade
- **WHEN** the user calls `update_trade_journal` with an owned `trade_id`, journal text, and mode `append`
- **THEN** the provided text is appended to the trade's existing `notes` and the tool returns the trade id

#### Scenario: Editing journal notes of a non-owned or unknown trade
- **WHEN** the user calls `update_trade_journal` with a `trade_id` that does not belong to them or does not exist
- **THEN** the tool returns an error indicating the trade was not found and nothing is changed

### Requirement: Trade Note Audit Logging
The system SHALL emit audit events when a trade quick note is added, updated, or deleted, or when the trade journal notes are edited via MCP, recording only safe metadata (the trade identifier and, where applicable, the note identifier) and never the note or journal content or any sensitive values.

#### Scenario: Audit event on note creation
- **WHEN** `add_trade_note` successfully creates a note
- **THEN** the system records a `trade.note_added` audit event whose metadata contains the user id, trade id, and note id, and excludes the note content

#### Scenario: Audit event on note update
- **WHEN** `update_trade_note` successfully updates a note
- **THEN** the system records a `trade.note_updated` audit event whose metadata contains the user id, trade id, and note id, and excludes the note content

#### Scenario: Audit event on note deletion
- **WHEN** `delete_trade_note` successfully deletes a note
- **THEN** the system records a `trade.note_deleted` audit event whose metadata contains the user id, trade id, and note id

#### Scenario: Audit event on journal edit
- **WHEN** `update_trade_journal` successfully changes a trade's journal notes
- **THEN** the system records a `trade.journal_updated` audit event whose metadata contains the user id and trade id, and excludes the journal content
