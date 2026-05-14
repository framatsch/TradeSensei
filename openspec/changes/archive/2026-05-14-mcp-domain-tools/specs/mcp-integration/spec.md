## MODIFIED Requirements

### Requirement: MCP Message Processing Endpoint
The system SHALL provide a POST endpoint at `/mcp/messages` to receive and process MCP requests, including tool discovery and tool invocation methods.

#### Scenario: Process valid MCP message
- **WHEN** an MCP client sends a valid JSON-RPC message to `/mcp/messages` with a valid PAT
- **THEN** the server processes the message and returns a synchronous JSON-RPC response

#### Scenario: Reject unauthorized MCP message
- **WHEN** an MCP client sends a message to `/mcp/messages` with an invalid PAT
- **THEN** the server returns a 401 Unauthorized error

#### Scenario: Process tools/list
- **WHEN** an authenticated client sends `{ "method": "tools/list" }`
- **THEN** the server responds with all available domain tool descriptors

#### Scenario: Process tools/call
- **WHEN** an authenticated client sends `{ "method": "tools/call", "params": { "name": "<tool>", "arguments": {...} } }`
- **THEN** the server dispatches to the named tool handler and returns its result

#### Scenario: Unknown tool name
- **WHEN** an authenticated client sends `tools/call` with an unrecognized tool name
- **THEN** the server returns `{ "error": { "code": -32601, "message": "Unknown tool: <name>" } }`

## MODIFIED Requirements

### Requirement: MCP Capabilities Declaration
The system SHALL declare tool capabilities in the `initialize` response.

#### Scenario: Initialize returns tool manifest
- **WHEN** an authenticated client sends `{ "method": "initialize" }`
- **THEN** `capabilities.tools` in the response is non-empty and reflects the available domain tools
