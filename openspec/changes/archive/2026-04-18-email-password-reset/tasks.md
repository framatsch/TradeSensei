## 1. Backend — Config & Token Infrastructure

- [x] 1.1 Add SMTP settings to `Settings` in `backend/app/core/config.py`: `smtp_host`, `smtp_port` (default 587), `smtp_user`, `smtp_password`, `email_from`, `smtp_tls` (default True).
- [x] 1.2 Add `password_reset_enabled` computed property to `Settings`: `True` when all SMTP fields are set and `local_auth_enabled` is `True`.
- [x] 1.3 Add `create_password_reset_token(user_id) → str` to `backend/app/core/security.py`: JWT with `"pwreset": True`, unique `jti`, 1-hour expiry.
- [x] 1.4 Add `consume_password_reset_token(token, db) → uuid` to `backend/app/core/security.py`: validates signature, `pwreset` claim, expiry, and replay via `used_otts`. Raises `InvalidTokenError` on any failure.

## 2. Backend — Email Service

- [x] 2.1 Create `backend/app/core/email.py` with `send_password_reset_email(to_address, reset_url)`: builds HTML + plain-text MIME message and sends via `smtplib` wrapped in `asyncio.to_thread()`.
- [x] 2.2 Write the reset email template inline in `email.py`: subject "Reset your TradeSensei password", body includes the reset link, 1-hour validity notice, and "If you didn't request this, ignore this email."

## 3. Backend — Schemas & Endpoints

- [x] 3.1 Add `ForgotPasswordRequest` and `ResetPasswordRequest` Pydantic schemas to `backend/app/schemas/auth.py`.
- [x] 3.2 Add `password_reset_enabled: bool` field to `AuthConfigResponse` schema.
- [x] 3.3 Update `get_config()` endpoint in `backend/app/api/v1/auth.py` to populate `password_reset_enabled` from `settings.password_reset_enabled`.
- [x] 3.4 Implement `POST /auth/forgot-password` in `auth.py`: look up user by email, check `hashed_password IS NOT NULL`, generate token, call `send_password_reset_email()`, always return 200. Return 503 if SMTP not configured.
- [x] 3.5 Implement `POST /auth/reset-password` in `auth.py`: call `consume_password_reset_token()`, hash new password, update `hashed_password`, increment `refresh_token_version`, return 200.

## 4. Backend — Tests

- [x] 4.1 Unit tests for `create_password_reset_token` and `consume_password_reset_token` in `backend/tests/unit/`.
- [x] 4.2 Integration tests for `POST /auth/forgot-password`: known user, unknown email, OAuth-only user, SMTP not configured.
- [x] 4.3 Integration tests for `POST /auth/reset-password`: valid token, expired token, replayed token, password too short.
- [x] 4.4 Integration test for `GET /auth/config` returning `password_reset_enabled` correctly.

## 5. Frontend — API Client & Types

- [x] 5.1 Regenerate the TypeScript API client (`/openapi-sync`) after the backend endpoint changes are in place.
- [x] 5.2 Add `password_reset_enabled` to the `AuthConfig` TypeScript type in `frontend/lib/types.ts` if not auto-generated.

## 6. Frontend — Pages & Components

- [x] 6.1 Create `frontend/app/(auth)/forgot-password/page.tsx`: email input form, submit calls `POST /auth/forgot-password`, shows static success message after submission regardless of response.
- [x] 6.2 Create `frontend/app/(auth)/reset-password/page.tsx`: reads `token` from query params (redirect to `/forgot-password` if absent), new-password + confirm-password fields, submits to `POST /auth/reset-password`, redirects to `/login?reset=success` on success, shows error state on 401.
- [x] 6.3 Update `frontend/components/auth/LoginForm.tsx`: render "Forgot password?" link below the password field only when `auth_config.password_reset_enabled === true`.
- [x] 6.4 Update `frontend/app/(auth)/login/page.tsx`: show a success notice when `?reset=success` is in the query string (e.g. "Your password has been reset. You can now sign in.").
