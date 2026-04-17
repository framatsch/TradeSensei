## MODIFIED Requirements

### Requirement: Config flag disables local auth
The backend SHALL expose a `LOCAL_AUTH_DISABLED` environment variable (boolean, default `false`). When `true` and at least one external provider is configured, the `/api/v1/auth/config` response SHALL include `local_auth_enabled: false`. When no external provider is configured, the flag SHALL be ignored and `local_auth_enabled: true` SHALL be returned, with a warning logged at startup.

The response SHALL also include `password_reset_enabled: bool`, derived as `true` when SMTP is fully configured (`SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM` are all set) AND `local_auth_enabled` is `true`.

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

#### Scenario: password_reset_enabled when SMTP configured
- **WHEN** `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, and `EMAIL_FROM` are all set and `local_auth_enabled` is `true`
- **THEN** `GET /api/v1/auth/config` returns `password_reset_enabled: true`

#### Scenario: password_reset_enabled false when SMTP not configured
- **WHEN** any required SMTP setting is absent
- **THEN** `GET /api/v1/auth/config` returns `password_reset_enabled: false`

#### Scenario: password_reset_enabled false when local auth disabled
- **WHEN** `local_auth_enabled` is `false`
- **THEN** `GET /api/v1/auth/config` returns `password_reset_enabled: false`
