## 1. Code Changes

- [x] 1.1 Create `backend/app/mcp_main.py` as a dedicated FastAPI entrypoint that only includes the MCP router.
- [x] 1.2 Update `docker-compose.yml` to start the MCP server process alongside the main API (or expose port 8001).
- [x] 2.1 Write `docs/mcp-client-integration.md` explaining how to generate a Personal Access Token (PAT).
- [x] 2.2 Add configuration examples to the documentation for Claude Desktop's `claude_desktop_config.json` demonstrating the use of `npx @modelcontextprotocol/sse-proxy` and the `AUTHORIZATION` environment variable.
- [x] 2.3 Add configuration examples to the documentation for OpenCode demonstrating PAT usage.
- [x] 2.4 Update `README.md` referencing the new dedicated port architecture and integration guide.