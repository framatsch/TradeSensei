## ADDED Requirements

### Requirement: Generate PAT for MCP
Users MUST be able to generate a Personal Access Token (PAT) specifically meant to authenticate connections to the MCP server. The token generation process MUST be documented.

#### Scenario: User follows token generation guide
- **WHEN** a user reads the MCP integration guide
- **THEN** the guide provides clear, step-by-step instructions on generating a PAT via the platform's UI or CLI.

### Requirement: Configure Claude Desktop via SSE Proxy
Clients like Claude Desktop that require `stdio` transport MUST be able to connect to the backend's SSE endpoint using a proxy that injects the PAT.

#### Scenario: Configuring Claude Desktop MCP integration
- **WHEN** a user configures `claude_desktop_config.json`
- **THEN** the configuration specifies the `npx @modelcontextprotocol/sse-proxy` command, pointing to the dedicated MCP port (e.g., `http://localhost:8001/mcp/sse`), and passes the PAT via the `AUTHORIZATION` environment variable.