## ADDED Requirements

### Requirement: Config flag disables local auth
The backend SHALL expose a `LOCAL_AUTH_DISABLED` environment variable (boolean, default `false`). When `true` and at least one external provider is configured, the `/api/v1/auth/config` response SHALL include `local_auth_enabled: false`. When no external provider is configured, the flag SHALL be ignored and `local_auth_enabled: true` SHALL be returned, with a warning logged at startup.

#### Scenario: Local auth disabled with OIDC provider configured
- **WHEN** `LOCAL_AUTH_DISABLED=true` and OIDC is configured
- **THEN** `GET /api/v1/auth/config` returns `local_auth_enabled: false`

#### Scenario: Local auth disabled with Google OAuth configured
- **WHEN** `LOCAL_AUTH_DISABLED=true` and Google OAuth credentials are set
- **THEN** `GET /api/v1/auth/config` returns `local_auth_enabled: false`

#### Scenario: Safety guard — no external provider configured
- **WHEN** `LOCAL_AUTH_DISABLED=true` but neither Google nor OIDC is configured
- **THEN** `GET /api/v1/auth/config` returns `local_auth_enabled: true` (flag is ignored)

#### Scenario: Default behaviour unchanged
- **WHEN** `LOCAL_AUTH_DISABLED` is not set (or `false`)
- **THEN** `GET /api/v1/auth/config` returns `local_auth_enabled: true`

---

### Requirement: Login form hidden when local auth disabled
The frontend SHALL hide the username/password form fields, the "Sign In" button, and the "Register" link when the auth config response contains `local_auth_enabled: false`.

#### Scenario: Local form hidden
- **WHEN** `local_auth_enabled` is `false` in the auth config
- **THEN** the login page shows only external provider button(s) and no username/password inputs

#### Scenario: Register link hidden
- **WHEN** `local_auth_enabled` is `false`
- **THEN** the "Create an account" / "Register" link is not rendered on the login page

#### Scenario: Local form shown by default
- **WHEN** `local_auth_enabled` is `true` (default)
- **THEN** the login page renders username/password form exactly as before

---

### Requirement: Auto-redirect when single provider and local auth disabled
The frontend login page SHALL automatically redirect to the external provider's auth URL when `local_auth_enabled` is `false` and exactly one external provider is enabled, without rendering any login UI.

#### Scenario: Auto-redirect to OIDC
- **WHEN** `local_auth_enabled: false` and only OIDC is configured
- **THEN** visiting `/login` immediately redirects to `/api/proxy/api/v1/auth/oidc`

#### Scenario: Auto-redirect to Google
- **WHEN** `local_auth_enabled: false` and only Google OAuth is configured
- **THEN** visiting `/login` immediately redirects to `/api/proxy/api/v1/auth/google`

#### Scenario: No auto-redirect when multiple providers
- **WHEN** `local_auth_enabled: false` and both Google and OIDC are configured
- **THEN** visiting `/login` renders the login page with both provider buttons (no auto-redirect)
