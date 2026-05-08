# mcp-integration Specification

## Purpose
TBD - created by archiving change mcp-integration. Update Purpose after archive.
## Requirements
### Requirement: MCP SSE Initialization Endpoint
The system SHALL provide a GET endpoint at `/mcp/sse` to initialize Server-Sent Events for MCP clients.

#### Scenario: Successful SSE initialization
- **WHEN** an MCP client connects to `/mcp/sse` with a valid PAT in the Authorization header
- **THEN** the server establishes an SSE connection and returns the initial configuration

#### Scenario: Unauthorized SSE initialization
- **WHEN** an MCP client connects to `/mcp/sse` with an invalid, expired, or revoked PAT
- **THEN** the server rejects the connection with a 401 Unauthorized error

### Requirement: MCP Message Processing Endpoint
The system SHALL provide a POST endpoint at `/mcp/messages` to receive and process MCP requests.

#### Scenario: Process valid MCP message
- **WHEN** an MCP client sends a valid JSON-RPC message to `/mcp/messages` with a valid PAT
- **THEN** the server processes the message and responds or pushes the response via SSE

#### Scenario: Reject unauthorized MCP message
- **WHEN** an MCP client sends a message to `/mcp/messages` with an invalid PAT
- **THEN** the server returns a 401 Unauthorized error

### Requirement: PAT Authentication Dependency
The system SHALL verify the Bearer token against the PAT database by hashing the provided token and matching it against stored active (unrevoked, non-expired) tokens.

#### Scenario: Token verification
- **WHEN** an API request arrives with a Bearer token
- **THEN** the system hashes the token, looks up the corresponding PAT record, checks `is_revoked` and `expires_at`, and injects the associated `User` context if valid

