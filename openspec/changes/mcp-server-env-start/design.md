## Context

The TradeSensei platform provides native Server-Sent Events (SSE) for MCP on the backend, secured by Personal Access Tokens (PAT). However, for enterprise deployment, the MCP endpoints should be isolated from the main public REST API. Furthermore, AI assistants like Claude Desktop only support `stdio` transport natively, requiring a bridge to connect to our SSE endpoints. Clear guidelines are needed to configure this secure setup.

## Goals / Non-Goals

**Goals:**
- Isolate the MCP server on a dedicated port (e.g., 8001) to allow internal-only network ingress.
- Document the process for generating a Personal Access Token (PAT) for MCP communication.
- Document the exact configuration required for Claude Desktop to connect to the SSE endpoint using a stdio-to-SSE proxy and the generated PAT.

**Non-Goals:**
- Altering the core protocol of MCP.
- Building a custom stdio-to-SSE bridge (we will use the official `@modelcontextprotocol/sse-proxy`).
- Building a new authentication mechanism (we will leverage the existing PAT system).

## Decisions

### D1: Use Existing PAT Infrastructure
Instead of creating a separate token system, we will utilize the platform's existing Personal Access Token (PAT) infrastructure. The token will be passed via the `Authorization: Bearer <TOKEN>` header. This keeps authentication centralized and audited.

### D2: Dedicated Port Architecture
To allow strict network boundaries (e.g., public ingress for REST, internal ingress for MCP), the MCP API will be served via a dedicated entrypoint (e.g., `app/mcp_main.py`). This allows running a separate Uvicorn worker specifically for MCP on port 8001 without interfering with port 8000.

### D3: Stdio to SSE Bridge for Claude
Since Claude Desktop currently only supports `stdio` communication for MCP servers, the documentation will instruct users to utilize the official `@modelcontextprotocol/sse-proxy` via `npx`. This proxy will run locally, speak `stdio` to Claude, and translate the communication to `SSE` against our dedicated port (8001), injecting the PAT into the headers.

## Risks / Trade-offs

- **Risk**: Operational complexity increases by managing two Uvicorn processes.
  - **Mitigation**: Update `docker-compose.yml` to clearly define the new service or port mappings, making it transparent for local development.
- **Risk**: Storing PATs in plain text in client configuration files.
  - **Mitigation**: Document security best practices, emphasizing that configuration files should have strict file permissions and tokens should be rotated regularly.