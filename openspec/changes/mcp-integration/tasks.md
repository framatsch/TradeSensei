## 1. Backend Data Model & DB

- [ ] 1.1 Create `PersonalAccessToken` SQLAlchemy model (fields: `id`, `user_id`, `name`, `token_hash` (SHA-256), `created_at`, `expires_at`, `is_revoked`, `last_used_at`) in a new file `backend/app/models/pat.py`.
- [ ] 1.2 Create Pydantic schemas for PAT generation request/response and listing in `backend/app/schemas/pat.py`. The response schema MUST NOT expose `token_hash`.
- [ ] 1.3 Generate Alembic migration for the new PAT table and apply it.

## 2. Backend Security & Dependencies

- [ ] 2.1 Implement `generate_pat()` (using `secrets.token_urlsafe`) and `hash_pat(token: str) -> str` (SHA-256 via `hashlib`) in `backend/app/core/security.py`.
- [ ] 2.2 Create a FastAPI Dependency `get_current_user_from_pat` in `backend/app/api/deps.py` that extracts the Bearer token, computes its SHA-256 hash, looks up the PAT via `WHERE token_hash = ?`, verifies `is_revoked` and `expires_at`, updates `last_used_at`, and injects the `User`. Use `hmac.compare_digest()` for the final hash comparison.

## 3. Backend API Endpoints

- [ ] 3.1 Implement PAT endpoints (`POST /api/v1/settings/tokens`, `GET /api/v1/settings/tokens`, `DELETE /api/v1/settings/tokens/{id}`) in `backend/app/api/v1/settings.py` and register in `backend/app/api/v1/router.py`.
- [ ] 3.2 Implement MCP SSE endpoint (`GET /mcp/sse`) secured with `get_current_user_from_pat`.
- [ ] 3.3 Implement MCP message endpoint (`POST /mcp/messages`) secured with `get_current_user_from_pat`.
- [ ] 3.4 Mount the MCP router directly in `backend/app/main.py` (outside the `/api/v1` prefix).
- [ ] 3.5 Add manual audit events: `pat.created` on token creation (log `token_id`, never the token value), `pat.revoked` on deletion. Both in the service layer.
- [ ] 3.6 Add backend unit tests for SHA-256 hashing, `get_current_user_from_pat` dependency (valid token, expired, revoked, missing), and PAT CRUD endpoints.

## 4. Frontend Settings UI

- [ ] 4.1 Update OpenAPI client via the `openapi-sync` skill to include the new PAT endpoints.
- [ ] 4.2 Add "API & Tokens" tab to the Settings view (`frontend/src/app/(dashboard)/settings/page.tsx`).
- [ ] 4.3 Create `TokenList` component to fetch and display the user's tokens (columns: Name, Created, Expires, Last Used, Status, Action).
- [ ] 4.4 Create `GenerateTokenModal` component to gather token name and expiration and call the POST API.
- [ ] 4.5 Create `TokenDisplayModal` component to show the plaintext token exactly once with a "Copy" button and a clear warning that it will not be shown again.
- [ ] 4.6 Implement token revocation action (DELETE call + optimistic UI update) via the `TokenList` component.
