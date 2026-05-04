## Context

The TradeSensei platform provides native Server-Sent Events (SSE) for MCP on the backend, secured by Personal Access Tokens (PAT). However, for enterprise deployment, the MCP endpoints should be able to be disabled via configuration. Furthermore, AI assistants like Claude Desktop only support `stdio` transport natively, requiring a bridge to connect to our SSE endpoints. Clear guidelines are needed to configure this secure setup.

## Goals / Non-Goals

**Goals:**
- Provide a configuration toggle (`MCP_ENABLED`) to optionally expose the MCP server on the main REST API.
- Document the process for generating a Personal Access Token (PAT) for MCP communication.
- Document the exact configuration required for Claude Desktop to connect to the SSE endpoint using a stdio-to-SSE proxy and the generated PAT.

**Non-Goals:**
- Altering the core protocol of MCP.
- Building a custom stdio-to-SSE bridge (we will use the official `@modelcontextprotocol/sse-proxy`).
- Building a new authentication mechanism (we will leverage the existing PAT system).

## Decisions

### D1: Use Existing PAT Infrastructure
Instead of creating a separate token system, we will utilize the platform's existing Personal Access Token (PAT) infrastructure. The token will be passed via the `Authorization: Bearer <TOKEN>` header. This keeps authentication centralized and audited.

### D2: Unified Process with Feature Flag
Instead of running a separate Uvicorn worker specifically for MCP on port 8001, we will unify the application into a single process. A boolean environment variable `MCP_ENABLED` in `config.py` will dictate whether the `mcp_router` is mounted into the main FastAPI application on startup. This simplifies local development and reduces Docker resource usage.

### D3: Stdio to SSE Bridge for Claude
Since Claude Desktop currently only supports `stdio` communication for MCP servers, the documentation will instruct users to utilize the official `@modelcontextprotocol/sse-proxy` via `npx`. This proxy will run locally, speak `stdio` to Claude, and translate the communication to `SSE` against our main REST API port (8000), injecting the PAT into the headers.

## Risks / Trade-offs

- **Risk**: Storing PATs in plain text in client configuration files.
  - **Mitigation**: Document security best practices, emphasizing that configuration files should have strict file permissions and tokens should be rotated regularly.