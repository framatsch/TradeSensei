## Why

Self-hosted deployments that use a central identity provider (Authentik, Google Workspace, etc.) should be able to disable the local username/password form entirely — eliminating a redundant login path and reducing the attack surface. Currently local auth is always shown regardless of which external providers are configured.

## What Changes

- New backend config flag `LOCAL_AUTH_DISABLED` (env var, default `false`) — when `true`, the `/auth/config` response sets `local_auth_enabled: false`.
- Safety guard: `LOCAL_AUTH_DISABLED=true` is a no-op if no external provider (Google OAuth or OIDC) is configured; the backend logs a warning and keeps local auth enabled.
- Frontend: when `local_auth_enabled=false`, the username/password form and the "Register" link are hidden; only external provider buttons are shown.
- Auto-redirect: if local auth is disabled and exactly one external provider is configured, the login page skips rendering entirely and redirects straight to that provider.
- `POST /api/v1/auth/token` and `POST /api/v1/auth/register` remain functional at the API level (no hard removal) — they simply become unreachable via the UI.

## Capabilities

### New Capabilities
- `local-auth-toggle`: Config-driven flag to disable the local login form and register flow in the UI, with a safety guard that requires at least one external provider to be active.

### Modified Capabilities

## Impact

- **Backend**: `app/core/config.py` (new field), `app/api/v1/auth.py` (`/auth/config` response)
- **Frontend**: `components/auth/LoginForm.tsx` (conditional rendering), `app/(auth)/login/page.tsx` (auto-redirect logic)
- **Deployment**: new optional env var `LOCAL_AUTH_DISABLED=true`
- **No breaking API changes** — existing endpoints unchanged
