## Context

The platform currently uses a stateless JWT auth scheme (access token in `localStorage`, refresh token in `httpOnly` cookie). Authentication is credential-only — username + bcrypt password. There is no social login infrastructure.

The `users` table has a non-nullable `hashed_password` column and no `provider` concept. The frontend uses a custom Zustand auth store with Axios interceptors; no auth library is present.

**Constraints:**
- Keep the existing JWT token strategy intact — Google-authed users receive the same access/refresh token pair
- `next-auth` is allowed on the frontend (user decision)
- Google OAuth only (no other providers in scope)
- No password for Google-only accounts — `hashed_password` must become nullable

---

## Goals / Non-Goals

**Goals:**
- Authorization Code Flow with Google: browser redirects to Google, Google redirects back, backend validates and issues JWT
- New users created automatically on first Google login
- Existing users with the same email address are linked to the Google provider
- Frontend shows a "Sign in with Google" button on login and register pages
- Backend emits the same JWT access + refresh tokens as password login

**Non-Goals:**
- Account merging UI (user-facing provider management)
- Multiple OAuth providers (GitHub, Facebook, etc.) — schema must support it but only Google is wired
- Forced re-auth or step-up auth flows
- Server-side rendering of protected pages with NextAuth session (keep client-side guard)

---

## Decisions

### 1. Backend handles the OAuth flow (not frontend)

**Decision:** The backend owns the full Authorization Code Flow. The frontend only redirects the browser to `GET /api/v1/auth/google`, then handles the result after callback.

**Rationale:** Keeps the client secret server-side. The frontend receives the same JWT it already knows how to handle — no new token format, no NextAuth session syncing.

**Alternative considered:** NextAuth handling the full flow on the frontend. Rejected because it would require NextAuth to also issue the project's JWT or replace it, which breaks the existing API client auth interceptor.

### 2. `authlib` for the backend OAuth client

**Decision:** Use `authlib>=1.3` (specifically `authlib.integrations.starlette_client`) for the Google OAuth client.

**Rationale:** Actively maintained, FastAPI-native async support, minimal boilerplate. Handles PKCE, state verification, and token exchange correctly.

**Alternative considered:** `python-social-auth`, `oauthlib`. Both are heavier and less idiomatic for async FastAPI.

### 3. NextAuth on the frontend — as a thin redirect coordinator only

**Decision:** Install `next-auth` but use it minimally: only to initiate the Google redirect (`signIn("google")`) and expose the resulting JWT to the existing Zustand store. The backend remains the source of truth.

**Rationale:** NextAuth's Google provider handles the PKCE/state details on the client side cleanly. The "Sign in with Google" button just calls `signIn("google")` — no custom redirect logic needed.

**Alternative considered:** Plain link to `/api/v1/auth/google` in the backend. Simpler but less maintainable; NextAuth integration also opens the door for future providers.

### 4. `provider` + `provider_id` columns on `users`

**Decision:** Add two columns to `users`: `provider VARCHAR(20)` (default `'local'`) and `provider_id VARCHAR(255)` (nullable, unique with provider).

**Rationale:** Supports future providers without schema changes. `'local'` for password users, `'google'` for Google. Unique constraint on `(provider, provider_id)` prevents duplicate OAuth accounts.

**Alternative considered:** Separate `oauth_accounts` table. Overkill for the current scope (one provider, no multi-account merging).

### 5. Post-callback redirect with tokens in query string (short-lived)

**Decision:** After successful OAuth callback, the backend issues a short-lived (60s) one-time token in the redirect URL (`/auth/callback?token=<jwt>`), which the frontend exchanges for the full access token.

**Rationale:** Avoids storing tokens in URL fragments (visible in server logs). The one-time token minimizes exposure window.

**Alternative considered:** POST to a frontend endpoint. Not possible from a server-side redirect. Setting cookies directly and skipping the frontend exchange was considered but complicates the existing cookie scope strategy.

---

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Token in redirect URL leaks in browser history | Use one-time short-lived token (60s TTL), immediately invalidated after use |
| Email not verified by Google | Check `email_verified` field in Google's ID token; reject if false |
| Existing local user with same email as Google account | Auto-link: update `provider`/`provider_id` on first Google login if email matches — user is informed via UI |
| `hashed_password` nullable breaks existing code | Audit all places that read `hashed_password`; guard with `if user.hashed_password is None` in `verify_password` |
| `next-auth` session and custom JWT coexistence | NextAuth session is not used for API calls; only the backend JWT is stored in `localStorage` via existing Zustand store |

---

## Migration Plan

1. Add Alembic migration: `provider VARCHAR(20) DEFAULT 'local' NOT NULL`, `provider_id VARCHAR(255) NULL`, `hashed_password` becomes nullable, unique index on `(provider, provider_id)`
2. Backfill existing rows: all existing users get `provider = 'local'`
3. Deploy backend with new env vars (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`)
4. Deploy frontend with `NEXTAUTH_SECRET`, `NEXTAUTH_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`

**Rollback:** Drop the two new columns (non-destructive), revert migration, remove new routes. Existing users are unaffected.

---

## Open Questions

- Should Google-authed users be blocked from later setting a password (keep them Google-only permanently), or should a future "set password" endpoint be planned? Current scope: Google-only is permanent for this iteration.
- `GOOGLE_REDIRECT_URI` value in production vs. development — must be configured per environment in Google Cloud Console.
