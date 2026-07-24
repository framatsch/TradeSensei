## ADDED Requirements

### Requirement: Download Trade Attachments
The system SHALL provide an MCP tool `get_trade_attachments` that returns the image attachments of a trade owned by the authenticated user. The tool SHALL accept a `format` argument of `image` (default) or `url`: `image` returns the image bytes as MCP image content blocks (base64 with mime type); `url` returns presigned GET URLs as text.

#### Scenario: Fetch trade charts as image blocks
- **WHEN** the authenticated user calls `get_trade_attachments` with an owned `trade_id` and no `format` (default `image`)
- **THEN** the tool returns the trade's images as MCP image content blocks containing base64 data and the correct mime type

#### Scenario: Fetch trade charts as presigned URLs
- **WHEN** the user calls `get_trade_attachments` with an owned `trade_id` and `format` set to `url`
- **THEN** the tool returns presigned GET URLs for the trade's images as text rather than base64 blocks

#### Scenario: Trade with no attachments
- **WHEN** the user calls `get_trade_attachments` for an owned trade that has no images
- **THEN** the tool returns an empty attachment result without error

#### Scenario: Non-owned or unknown trade
- **WHEN** the user calls `get_trade_attachments` with a `trade_id` that does not belong to them or does not exist
- **THEN** the tool returns an error indicating the trade was not found

### Requirement: Download Playbook Attachments
The system SHALL provide an MCP tool `get_playbook_attachments` that returns the image attachments and labeled links of a playbook owned by the authenticated user, honouring the same `format` argument (`image` default, or `url`) for the images and returning links as text (label and URL).

#### Scenario: Fetch playbook attachments and links
- **WHEN** the authenticated user calls `get_playbook_attachments` with an owned `playbook_id`
- **THEN** the tool returns the playbook's image attachments (as image blocks by default) and its labeled links as text

#### Scenario: Non-owned or unknown playbook
- **WHEN** the user calls `get_playbook_attachments` with a `playbook_id` that does not belong to them or does not exist
- **THEN** the tool returns an error indicating the playbook was not found

### Requirement: Attachment Context Guardrails
The system SHALL bound attachment responses to protect the model context window by limiting the number of attachments returned per call and the size of any inline base64 image. When the number of available attachments exceeds the per-call maximum, the response SHALL be truncated to the maximum and indicate that truncation occurred. When an individual image exceeds the maximum inline byte size, the tool SHALL return a presigned URL for that image instead of base64 data.

#### Scenario: More attachments than the per-call limit
- **WHEN** an owned trade or playbook has more attachments than the configured maximum and the user requests them
- **THEN** the tool returns at most the configured maximum number of attachments and signals that the result was truncated

#### Scenario: Oversized image falls back to URL
- **WHEN** an individual attachment's byte size exceeds the configured inline image limit while `format` is `image`
- **THEN** the tool returns a presigned URL for that attachment instead of embedding its base64 data

#### Scenario: Storage retrieval failure for one image
- **WHEN** the storage backend cannot return the bytes for one attachment during an `image`-format request
- **THEN** the tool degrades that attachment to a URL or error entry without failing the entire call
