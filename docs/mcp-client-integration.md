## MCP Client Integration Guide

### Claude Desktop Configuration (using SSE Proxy)

Create or edit `claude_desktop_config.json` to include the following `sse_proxy` block. This tells Claude Desktop to launch the official `@modelcontextprotocol/sse-proxy` which translates stdio to the MCP SSE endpoint and injects the PAT.

```json
{
  "sse_proxy": {
    "command": "npx",
    "args": [
      "-y",
      "@modelcontextprotocol/sse-proxy",
      "http://localhost:8000/mcp/sse"
    ],
    "env": {
      "AUTHORIZATION": "Bearer <YOUR_PAT>"
    }
  }
}
```

Replace `<YOUR_PAT>` with the token generated in the previous section.

### OpenCode Configuration Example

For OpenCode, set the `AUTHORIZATION` environment variable before invoking the client:

```bash
export AUTHORIZATION="Bearer <YOUR_PAT>"
opencode --mcp http://localhost:8000/mcp/sse
```

## Generating a Personal Access Token (PAT)

1. Log in to the Trade Sensei web UI.
2. Navigate to **Settings → API Tokens**.
3. Click **Create New Token**.
4. Give the token a descriptive name (e.g., `MCP Integration`) and set the **Scope** to *MCP*.
5. Click **Generate**. The token will be displayed **once** – copy it safely.
6. Store the token in a secure location (e.g., password manager) and treat it like a password.

### Using the PAT with the MCP Server

The MCP server expects the token in the `Authorization` header as a Bearer token:

```
Authorization: Bearer <YOUR_PAT>
```

All MCP endpoints (`/mcp/*`) will reject requests without a valid PAT with `401 Unauthorized`.

### Token Rotation

- Tokens can be revoked from the **API Tokens** page.
- After revocation, generate a new token and update your client configuration.
- Rotate tokens regularly (e.g., every 90 days) to reduce risk.


### Generating a Personal Access Token (PAT)

1. Log in to the Trade Sensei web UI.
2. Navigate to **Settings → API Tokens**.
3. Click **Create New Token**.
4. Give the token a descriptive name (e.g., `MCP Integration`) and set the **Scope** to *MCP*.
5. Click **Generate**. The token will be displayed **once** – copy it safely.
6. Store the token in a secure location (e.g., password manager) and treat it like a password.

### Using the PAT with the MCP Server

The MCP server expects the token in the `Authorization` header as a Bearer token:

```
Authorization: Bearer <YOUR_PAT>
```

All MCP endpoints (`/mcp/*`) will reject requests without a valid PAT with `401 Unauthorized`.

### Token Rotation

- Tokens can be revoked from the **API Tokens** page.
- After revocation, generate a new token and update your client configuration.
- Rotate tokens regularly (e.g., every 90 days) to reduce risk.
