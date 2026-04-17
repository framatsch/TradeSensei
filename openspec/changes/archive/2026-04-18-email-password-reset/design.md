## Context

Local-auth users currently have no self-service recovery path. The existing `reset_password.py` CLI tool requires server access, which is impractical for end users. The application already has a JWT + `used_otts` one-time-token (OTT) infrastructure used for OAuth callback exchange — this same pattern is well-suited for password reset tokens.

No SMTP infrastructure exists yet. The feature must be opt-in: if SMTP is not configured, the "Forgot password?" link must not appear and the endpoints must not expose whether a user exists.

## Goals / Non-Goals

**Goals:**
- Self-service password reset via time-limited email token.
- Reuse the existing `used_otts` + JWT machinery (no new DB table).
- Feature-gate entirely behind SMTP configuration — invisible when unconfigured.
- Invalidate all active sessions on reset (`refresh_token_version++`).
- Only available to users with a local password (`hashed_password IS NOT NULL`).

**Non-Goals:**
- Password reset for OAuth-only users (no `hashed_password`).
- Email templating engine / i18n.
- Rate limiting on the forgot-password endpoint (out of scope for now).
- Admin-triggered password reset email (CLI tool already covers that).

## Decisions

### 1. Token: Reuse JWT + `used_otts`, new claim type

The OTT infrastructure already solves exactly the right problem: signed, short-lived, single-use tokens with replay protection via DB. A password reset token is identical except:
- Claim: `"pwreset": True` instead of `"ott": True`
- Expiry: 1 hour instead of 60 seconds

Two new functions in `security.py`:
- `create_password_reset_token(user_id) → str`
- `consume_password_reset_token(token, db) → uuid` (raises `InvalidTokenError` on failure)

**Alternative considered:** Separate `password_reset_tokens` table with `token_hash + expires_at + used_at`.
**Rejected:** More schema, a migration, and more code for no meaningful security gain over the JWT approach. The `used_otts` table already provides replay protection.

### 2. Email: stdlib `smtplib` + `email.mime`, no new package

Python's standard library covers everything needed: SMTP auth, STARTTLS, HTML email bodies.

Config fields added to `Settings`:
```
smtp_host: str | None = None
smtp_port: int = 587
smtp_user: str | None = None
smtp_password: str | None = None
email_from: str | None = None
smtp_tls: bool = True          # STARTTLS
```

`password_reset_enabled` derived property:
```python
@property
def password_reset_enabled(self) -> bool:
    return bool(self.smtp_host and self.smtp_user and self.smtp_password
                and self.email_from and self.local_auth_is_enabled)
```

**Alternative considered:** `fastapi-mail`, `aiosmtplib`.
**Rejected:** Avoids adding a dependency for a handful of stdlib calls.

### 3. Security: Always return 200 on `/forgot-password`

The endpoint MUST NOT reveal whether an email address is registered. It always returns `{"detail": "If an account with that email exists, a reset link has been sent."}` — regardless of whether the user was found.

Email is only sent when: user found AND `hashed_password IS NOT NULL`.

### 4. Frontend visibility gated on `password_reset_enabled`

`GET /auth/config` is extended with `password_reset_enabled: bool`. The "Forgot password?" link on the login page is only rendered when this flag is `true`. This mirrors the existing `local_auth_enabled` / `google_enabled` pattern exactly.

### 5. Token delivered in URL query param

Reset link format: `{FRONTEND_URL}/reset-password?token=<jwt>`

The frontend page extracts the token from the query string and POSTs it with the new password. The token is single-use — after consumption it's recorded in `used_otts`.

## Risks / Trade-offs

- **SMTP credentials in env vars** → Standard practice for self-hosted apps. Secrets should be stored in k8s Secrets, not ConfigMaps.
- **No rate limiting on `/forgot-password`** → Could be used to enumerate timing differences. The "always 200" rule mitigates enumeration; rate limiting is a future hardening task.
- **Token in URL** → Logged in access logs / browser history. Mitigation: 1-hour expiry + single-use. Standard practice for password reset flows.
- **smtplib is synchronous** → Email send blocks the event loop. Mitigation: wrap in `asyncio.to_thread()` (same pattern used for Alembic migrations at startup).
