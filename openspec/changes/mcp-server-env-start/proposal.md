## Why

Currently, integrating the TradeSensei MCP server with AI tools like OpenCode or Claude Desktop lacks clear architectural controls and documentation. We want to be able to enable or disable the MCP server easily via an environment variable without deploying a completely separate process, making it configurable but unified within the main backend API. Furthermore, developers need a clear, documented process on how to generate a Personal Access Token (PAT) and configure the secure MCP connection—especially overcoming Claude Desktop's limitation of only supporting `stdio` transport natively.

## What Changes

- Add a toggleable environment variable (`MCP_ENABLED`) to the FastAPI backend to enable or disable the MCP endpoints within the main REST API.
- Create a comprehensive "How-To" guide detailing the process of generating a Personal Access Token (PAT) for the MCP server.
- Provide step-by-step instructions on integrating the MCP server with Claude Desktop using the official `@modelcontextprotocol/sse-proxy` to bridge Claude's local `stdio` to our backend's `SSE` protocol.
- Ensure the backend properly supports token-based authentication via PAT for the MCP server.

## Capabilities

### New Capabilities
- `mcp-secure-integration`: Documentation and functionality covering token generation, client configuration using `sse-proxy`, and secure injection of the PAT via Authorization headers.

### Modified Capabilities
- `mcp-integration`: Enhance the existing MCP integration to be toggled via an environment variable instead of a dedicated port for improved configuration management.

## Impact

- **Architecture**: A new `MCP_ENABLED` boolean environment variable controls the mounting of the `mcp_router` in `main.py`. The secondary `mcp_main.py` entrypoint and Docker container are removed.
- **Documentation**: New How-To guides added to the `docs/` directory explaining the proxy setup.
- **Security**: Promotes secure, authenticated connections (PAT) with simple environment-level controls to toggle availability.