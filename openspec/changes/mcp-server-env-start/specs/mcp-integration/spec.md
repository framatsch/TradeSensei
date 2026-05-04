## MODIFIED Requirements

### Requirement: MCP Server Initialization
The MCP Server SHALL start up and bind to a dedicated host and port separated from the main REST API, establishing a secure connection requiring PAT authentication.

#### Scenario: Startup on a Dedicated Port
- **WHEN** the TradeSensei backend is launched
- **THEN** the MCP specific routes MUST be accessible via a dedicated entrypoint (e.g., `uvicorn app.mcp_main:app --port 8001`) to allow isolated network ingress rules.