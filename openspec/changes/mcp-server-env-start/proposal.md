## Why

Currently, integrating the TradeSensei MCP server with AI tools like OpenCode or Claude Desktop lacks clear architectural separation and documentation. The MCP server runs on the main REST API port, making it difficult to restrict access strictly to internal networks or API gateways. Furthermore, developers need a clear, documented process on how to generate a Personal Access Token (PAT) and configure the secure MCP connection—especially overcoming Claude Desktop's limitation of only supporting `stdio` transport natively.

## What Changes

- Isolate the MCP endpoints to run on a dedicated port (e.g., 8001) via a separate Uvicorn entrypoint. This enables fine-grained ingress control (e.g., exposing REST publicly but keeping MCP internal).
- Create a comprehensive "How-To" guide detailing the process of generating a Personal Access Token (PAT) for the MCP server.
- Provide step-by-step instructions on integrating the MCP server with Claude Desktop using the official `@modelcontextprotocol/sse-proxy` to bridge Claude's local `stdio` to our backend's `SSE` protocol.
- Ensure the backend properly supports token-based authentication via PAT for the MCP server.

## Capabilities

### New Capabilities
- `mcp-secure-integration`: Documentation and functionality covering token generation, client configuration using `sse-proxy`, and secure injection of the PAT via Authorization headers.

### Modified Capabilities
- `mcp-integration`: Enhance the existing MCP integration to run on a dedicated port separate from the main FastAPI application for improved network isolation.

## Impact

- **Architecture**: A new entrypoint (`mcp_main.py`) will be created to run the MCP API on a separate port.
- **Documentation**: New How-To guides added to the `docs/` directory explaining the proxy setup.
- **Security**: Promotes secure, authenticated connections (PAT) while allowing network-level isolation of AI integration endpoints.