## ADDED Requirements

### Requirement: MCP SSE endpoint requires a valid PAT
The system SHALL return 401 when the `Authorization` header is missing or contains an invalid/expired PAT.

#### Scenario: Missing auth returns 401
- **WHEN** a request is made to `GET /mcp/sse` without an Authorization header
- **THEN** the response is 401

#### Scenario: Invalid PAT returns 401
- **WHEN** a request is made to `GET /mcp/sse` with an invalid token
- **THEN** the response is 401

### Requirement: MCP SSE endpoint returns a streaming response with ready event
The system SHALL respond to authenticated requests with `Content-Type: text/event-stream` and emit a `ready` event containing the `message_endpoint` URL.

#### Scenario: Valid PAT returns SSE stream
- **WHEN** an authenticated request is made to `GET /mcp/sse` with a valid PAT
- **THEN** the response Content-Type is `text/event-stream` and the first event is `event: ready`

### Requirement: MCP SSE session_id is validated
The system SHALL reject a `session_id` query parameter that does not match the allowed pattern `[A-Za-z0-9_-]{1,64}`.

#### Scenario: Invalid session_id format returns 400
- **WHEN** a request is made with a `session_id` containing special characters not in the allowed set
- **THEN** the response is 400

#### Scenario: Valid session_id is echoed in ready event
- **WHEN** a request is made with a valid `session_id`
- **THEN** the ready event payload includes the `session_id` field

### Requirement: MCP messages endpoint requires a valid PAT
The system SHALL return 401 for unauthenticated requests to `POST /mcp/messages`.

#### Scenario: Unauthenticated message request returns 401
- **WHEN** a request is made to `POST /mcp/messages` without a valid PAT
- **THEN** the response is 401
