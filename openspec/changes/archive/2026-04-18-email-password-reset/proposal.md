## Why

Users with local accounts have no self-service way to recover access if they forget their password — currently the only option is an admin running `reset_password.py` on the server. A standard "Forgot Password" email flow removes this operational burden and makes the app usable in production without server access.

## What Changes

- Add SMTP configuration to `Settings` (host, port, user, password, sender, TLS flag).
- Add `POST /api/v1/auth/forgot-password` endpoint: accepts an email address and sends a reset link if the account exists and has a local password.
- Add `POST /api/v1/auth/reset-password` endpoint: validates the reset token and sets the new password.
- Extend `GET /api/v1/auth/config` to include `password_reset_enabled: bool`.
- Add a frontend `/forgot-password` page with an email form.
- Add a frontend `/reset-password` page that validates the token and shows a new-password form.
- Show a "Forgot password?" link on the login page only when `password_reset_enabled` is true.

## Capabilities

### New Capabilities
- `email-password-reset`: Self-service password reset via email token — request flow, token generation/validation, password update, and frontend pages.

### Modified Capabilities
- `local-auth-toggle`: `GET /auth/config` gains a `password_reset_enabled` field derived from SMTP config + local auth status.

## Impact

- **Backend**: New endpoints in `auth.py`; new `EmailService` module; new `create_password_reset_token` / `consume_password_reset_token` functions in `security.py` (reusing `used_otts` + JWT); 5 new SMTP fields in `config.py`. No DB migration needed.
- **Frontend**: Two new pages (`/forgot-password`, `/reset-password`); one new link in `LoginForm`.
- **Dependencies**: No new packages — uses Python `smtplib` + `email.mime` from stdlib.
- **Config**: Operators must set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM` to enable the feature.
