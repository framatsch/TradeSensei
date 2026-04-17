## Context

The app already has a `/api/v1/auth/config` endpoint that returns which providers are active (`google_enabled`, `oidc_enabled`, `oidc_provider_name`). The frontend reads this on load and conditionally renders the Google/OIDC buttons. Local auth currently has no corresponding flag — the form is always shown.

Backend config lives in `app/core/config.py` (pydantic-settings). OIDC already uses an `oidc_enabled: bool` pattern. The same approach can be applied symmetrically for local auth.

## Goals / Non-Goals

**Goals:**
- Single env var `LOCAL_AUTH_DISABLED=true` disables local login UI
- Safety guard: flag is ignored (with a logged warning) when no external provider is configured
- Auto-redirect when local auth is disabled and exactly one provider is active
- No API endpoint removal — local auth endpoints remain available for admin tooling / scripts

**Non-Goals:**
- Hard removal of `/auth/token` or `/auth/register` endpoints
- Per-user auth method restrictions
- Admin UI for toggling auth methods at runtime (env var only)
- Rate limiting or brute-force protection on the local endpoints (separate concern)

## Decisions

**Decision 1: Env var name `LOCAL_AUTH_DISABLED` (opt-out, default false)**
- Alternatives considered: `LOCAL_AUTH_ENABLED=true` (opt-in) — inverted logic; existing deployments would break if default changed accidentally. Opt-out is safer: existing deployments change nothing.
- `LOCAL_AUTH_DISABLED` follows the existing pattern of feature flags in this codebase (e.g., `OIDC_ENABLED`).

**Decision 2: Safety guard in backend, not frontend**
- The guard (require ≥1 external provider) lives in `settings` / the `/auth/config` logic, not in the frontend.
- Reason: the frontend could be bypassed. A misconfigured backend (no providers + local disabled) would silently lock everyone out. Better to catch it server-side and log a warning.

**Decision 3: Auto-redirect on frontend, not backend**
- When exactly one provider is configured and local auth is disabled, the login page redirects to that provider without rendering the login UI.
- This is a UX decision: implemented in `login/page.tsx` using the config response, consistent with how existing provider buttons work.
- The backend makes no assumptions about redirect logic — it only reports config state.

**Decision 4: `/auth/config` response extended, not a new endpoint**
- Add `local_auth_enabled: bool` to the existing `AuthConfigResponse` schema.
- Keeps the frontend's single config-fetch pattern intact.

## Risks / Trade-offs

- **Lockout risk** → Mitigation: safety guard in backend; unit test that asserts `local_auth_enabled` stays `true` when no provider is configured even if `LOCAL_AUTH_DISABLED=true`.
- **Auto-redirect UX** → Mitigation: only redirect when exactly one provider is active; if two providers are configured and local is off, show the provider buttons normally.
- **Existing sessions unaffected** → No migration needed; flag only affects the login UI, not token validation.

## Migration Plan

1. Deploy with `LOCAL_AUTH_DISABLED` unset (default `false`) — no behaviour change.
2. Configure external provider(s) first, verify login works.
3. Set `LOCAL_AUTH_DISABLED=true`, redeploy — local form disappears, provider button(s) remain.
4. Rollback: unset `LOCAL_AUTH_DISABLED` and redeploy — local form reappears immediately.
