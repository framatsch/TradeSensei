## Context

External AI assistants like Claude Desktop and Cursor use the Model Context Protocol (MCP) to interact with tools. To allow these assistants to connect to the Trade Sensei application securely, we need to implement the MCP transport (SSE and messaging) and a mechanism for authenticating those connections. A Personal Access Token (PAT) system is the standard approach for API/integration access.

## Goals / Non-Goals

**Goals:**
- Implement a `PersonalAccessToken` database model.
- Provide API endpoints for CRUD operations on PATs (`/api/v1/settings/tokens`).
- Provide an UI in Settings to generate, list, and revoke PATs.
- Implement MCP endpoints (`/mcp/sse`, `/mcp/messages`) protected by PATs, mounted directly in `main.py` outside the versioned v1 router.

**Non-Goals:**
- OAuth2 integration for third-party apps (this is strictly for PATs).
- Scoped tokens (tokens have full access as the user).
- Implementing MCP tools/prompts (this design focuses on integration & auth infrastructure).

## Decisions

- **Token Storage**: Tokens will be generated using `secrets.token_urlsafe()`. Only a SHA-256 hash of the token will be stored in the DB. SHA-256 (not bcrypt) is the correct choice here: PATs are already high-entropy random strings, so slow adaptive hashing provides no additional benefit. More importantly, SHA-256 is deterministic and keyless, which allows a direct `WHERE token_hash = ?` DB lookup — bcrypt would require loading and verifying every token individually, which does not scale.
- **Token Viewing**: The plaintext token will be returned exactly once upon creation.
- **Revocation**: Instead of hard-deleting tokens, they will be marked as `is_revoked = true` to preserve audit history and avoid orphaned records if referenced elsewhere in logs.
- **Authentication**: MCP routes will use a FastAPI Dependency that extracts the PAT from the `Authorization: Bearer <PAT>` header, computes its SHA-256 hash, and performs a direct DB lookup. The final string comparison MUST use `hmac.compare_digest()` (already present in `app/core/security.py`) to prevent timing attacks. The dependency then verifies expiration/revocation and injects the `User` into the request.
- **MCP Router Placement**: The MCP router (`/mcp/sse`, `/mcp/messages`) is mounted directly in `main.py` outside the versioned `/api/v1` prefix. This follows MCP protocol conventions. The `AuditMiddleware` in `main.py` covers all routes by default, so audit logging applies here as well.

## Risks / Trade-offs

- **Risk**: Users losing their token and being unable to retrieve it.
  - **Mitigation**: Clear UI messaging indicating the token will only be shown once, and offering an easy way to revoke and generate a new one.
- **Risk**: Token leakage by the user.
  - **Mitigation**: Expiration dates (30 days, 90 days, 1 year) are supported. Revocation capability is provided.