## Why

Trade Sensei requires integration with the Model Context Protocol (MCP) to allow external AI assistants (like Cursor, Claude) to securely interact with the application. A Personal Access Token (PAT) system is needed to authenticate these external MCP clients securely and manage their access lifecycles.

## What Changes

- Add a new Personal Access Token (PAT) management system (database model, API endpoints, UI).
- Add new endpoints for MCP communication (`/mcp/sse` and `/mcp/messages`) secured by PATs.
- Provide a user interface in settings to generate, view, and revoke PATs.
- Tokens will be stored as cryptographic hashes; plain text is only shown once upon creation.

## Capabilities

### New Capabilities
- `pat-management`: Management of Personal Access Tokens (creation, listing, revocation).
- `mcp-integration`: Endpoints and authentication logic for the Model Context Protocol.

### Modified Capabilities
- None

## Impact

- Database schema: new table for PATs.
- API layer: new settings and MCP endpoints.
- Frontend UI: new section in the user settings for managing API & Tokens.
- Authentication flow: new PAT-based dependency for specific routes.