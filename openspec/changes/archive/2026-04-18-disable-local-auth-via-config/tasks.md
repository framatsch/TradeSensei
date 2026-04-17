## 1. Backend — Config & Auth Config Endpoint

- [x] 1.1 Add `local_auth_disabled: bool = False` field to `Settings` in `app/core/config.py`
- [x] 1.2 Add `local_auth_enabled: bool` field to `AuthConfigResponse` schema in `app/api/v1/auth.py`
- [x] 1.3 Implement safety-guard logic in the `/auth/config` handler: if `local_auth_disabled=True` but no external provider is configured, log a warning and return `local_auth_enabled=True`
- [x] 1.4 Return `local_auth_enabled=False` when `local_auth_disabled=True` and at least one provider is configured

## 2. Backend — Tests

- [x] 2.1 Unit test: `local_auth_enabled=true` when flag is unset (default)
- [x] 2.2 Unit test: `local_auth_enabled=false` when flag is set and OIDC is configured
- [x] 2.3 Unit test: `local_auth_enabled=true` (safety guard) when flag is set but no provider is configured

## 3. Frontend — Auth Config Type & Hook

- [x] 3.1 Add `local_auth_enabled: boolean` to the `AuthConfig` TypeScript type in `lib/types.ts` (or wherever the config type lives)
- [x] 3.2 Verify the existing `useAuthConfig` hook (or equivalent fetch) passes `local_auth_enabled` through to consumers

## 4. Frontend — Login Form Conditional Rendering

- [x] 4.1 In `LoginForm.tsx`, wrap the username/password fields and Sign-In button in a `local_auth_enabled` check — render nothing when `false`
- [x] 4.2 Hide the "Register" / "Create account" link when `local_auth_enabled` is `false`

## 5. Frontend — Auto-Redirect Logic

- [x] 5.1 In `app/(auth)/login/page.tsx`, after fetching auth config: if `local_auth_enabled=false` and exactly one provider is active, redirect immediately to that provider's proxy URL (`/api/proxy/api/v1/auth/oidc` or `/api/proxy/api/v1/auth/google`)
- [x] 5.2 Ensure the redirect does not render the login page (use Next.js `redirect()` or an early return with `useEffect`)

## 6. Docs & Deployment

- [x] 6.1 Add `LOCAL_AUTH_DISABLED` to `.env.example` with a comment explaining the safety guard
- [x] 6.2 Update `AGENTS.md` / deployment docs to mention the new env var
