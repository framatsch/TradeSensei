# Authentication Guide

This guide covers the authentication system for the Trade Sensei platform, including JWT-based login, password reset, and OpenID Connect (OIDC) integration.

---

## Overview

Trade Sensei uses a multi-method authentication system:

- **Local authentication** — username/email + password with bcrypt hashing
- **Google OAuth 2.0** — federated login via Google accounts
- **Generic OIDC** — OpenID Connect providers (Authentik, Keycloak, etc.)
- **Password reset** — self-service email-based password recovery

All authentication endpoints are under `/api/v1/auth`. The system issues short-lived access tokens (15 minutes) and long-lived refresh tokens (7 days) stored as httpOnly cookies.

### Token Flow

1. User logs in with credentials or OAuth provider
2. Backend issues an **access token** (JWT, 15 min lifetime) in the response body
3. Backend sets a **refresh token** (JWT, 7 day lifetime) as an httpOnly Secure cookie
4. Client includes the access token in the `Authorization: Bearer <token>` header for subsequent requests
5. When the access token expires, the client exchanges the refresh token cookie for a new pair via `POST /auth/refresh`

---

# Local Authentication (Username/Password)

## Registration

Create a new user account with a username, email, and password.

**Endpoint:** `POST /api/v1/auth/register`

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "trader_alice",
    "email": "alice@example.com",
    "password": "SecurePassword123!"
  }'
```

**Response (201 Created):**
```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "trader_alice",
    "email": "alice@example.com",
    "is_active": true,
    "created_at": "2024-03-15T10:30:00Z"
  }
}
```

**Error responses:**
- `409 Conflict` — Username or email already registered
- `422 Unprocessable Entity` — Validation error (e.g., password too short, invalid email format)

**Password requirements:**
- Minimum 8 characters
- No other complexity rules enforced (users should choose strong passwords)

## Login

Authenticate with username (or email) and password to obtain tokens.

**Endpoint:** `POST /api/v1/auth/token`

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=trader_alice&password=SecurePassword123!"
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

The response also sets an httpOnly Secure cookie:
```
Set-Cookie: refresh_token=<jwt>; HttpOnly; Secure; SameSite=Strict; Max-Age=604800; Path=/api/v1/auth
```

**Error responses:**
- `401 Unauthorized` — Incorrect username/email or password
- `422 Unprocessable Entity` — Missing or malformed form fields

**Using the access token:**
```bash
curl -X GET http://localhost:8000/api/v1/trades \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## Token Refresh

Exchange the refresh token cookie for a new access token and rotated refresh token.

**Endpoint:** `POST /api/v1/auth/refresh`

**Request:**
```bash
# The refresh_token cookie is automatically sent by the browser
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Cookie: refresh_token=<jwt>"
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

A new refresh token is set in the cookie (token rotation).

**Error responses:**
- `401 Unauthorized` — Refresh token is missing, invalid, expired, or has been revoked

## Logout

Invalidate all refresh tokens for the authenticated user and clear the refresh token cookie.

**Endpoint:** `POST /api/v1/auth/logout`

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer <access_token>"
```

**Response (204 No Content):**
No response body. The refresh token cookie is deleted.

**Error responses:**
- `401 Unauthorized` — Missing or invalid access token

---

# Password Reset

## Overview

Users can request a password reset email if they forget their password. The system sends a link with a one-time token valid for 1 hour.

**Prerequisites:**
- SMTP server must be configured (see section below)
- Local authentication must be enabled (not disabled via `LOCAL_AUTH_DISABLED=true` without an external provider)

**Important note:** Password reset is automatically enabled once SMTP is fully configured. There's no separate feature flag — just set all 4 required SMTP environment variables.

## Request Password Reset

Send a password-reset email to the given address.

**Endpoint:** `POST /api/v1/auth/forgot-password`

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com"}'
```

**Response (200 OK):**
```json
{
  "detail": "If an account with that email exists, a reset link has been sent."
}
```

**Important:** The endpoint always returns 200 and the same message, regardless of whether the email is registered. This prevents user enumeration attacks.

**Error responses:**
- `503 Service Unavailable` — Password reset is not configured on the server (see "SMTP Configuration" below)

## Reset Password

Set a new password using the token from the email link.

**Endpoint:** `POST /api/v1/auth/reset-password`

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "new_password": "NewSecurePassword456!"
  }'
```

**Response (200 OK):**
```json
{
  "detail": "Password updated successfully."
}
```

**Error responses:**
- `401 Unauthorized` — Token is invalid, expired, or already used
- `422 Unprocessable Entity` — Validation error (e.g., password too short)

**Side effects:**
- All existing refresh tokens for the user are invalidated (user is logged out on all devices)

## SMTP Configuration

### What SMTP Configuration Enables

Once SMTP is fully configured, the following endpoints automatically become available:
- `POST /api/v1/auth/forgot-password` — Request password reset email
- `POST /api/v1/auth/reset-password` — Reset password with token
- Password reset link is embedded in emails sent to users

The backend automatically detects whether password reset is enabled by checking if **all 4 required variables** are set.

### Required Environment Variables

To enable password reset, you **must** configure all four of these environment variables (not just some):

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `SMTP_HOST` | SMTP server hostname | `smtp.gmail.com` | ✅ Yes |
| `SMTP_PORT` | SMTP server port | `587` | No (defaults to 587) |
| `SMTP_USER` | SMTP authentication username | `noreply@example.com` | ✅ Yes |
| `SMTP_PASSWORD` | SMTP authentication password | `your-app-specific-password` | ✅ Yes |
| `EMAIL_FROM` | **Sender email address** (often forgotten!) | `noreply@example.com` | ✅ Yes |
| `SMTP_TLS` | Use STARTTLS for encryption | `true` | No (defaults to true) |

**⚠️ Important:** If any of the 4 required variables (`SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM`) are missing, password reset will not work and the endpoint will return `503 Service Unavailable`.

### Example Configuration for Gmail

To use Gmail as your SMTP provider:

**Prerequisites:**
1. Enable 2-factor authentication on your Google account
2. Generate an [app-specific password](https://myaccount.google.com/apppasswords)

**Set these environment variables:**

```dotenv
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
EMAIL_FROM=your-email@gmail.com
SMTP_TLS=true
```

### Example Configuration for Other SMTP Providers

For Outlook, Yahoo, SendGrid, or other SMTP providers, refer to their documentation for the correct hostname and port. The setup is identical — just replace `SMTP_HOST`, `SMTP_USER`, and `SMTP_PASSWORD`.

### Debugging SMTP Configuration

**To verify your SMTP configuration is correct:**

```bash
# 1. Check that all required variables are set
echo "SMTP_HOST: $SMTP_HOST"
echo "SMTP_USER: $SMTP_USER"
echo "SMTP_PASSWORD: [hidden]"
echo "EMAIL_FROM: $EMAIL_FROM"

# 2. Check the backend logs for SMTP errors
docker logs tradesensei-backend | grep -i smtp

# 3. Try requesting a password reset and check if the email arrives
curl -X POST http://localhost:8000/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "your-test-email@example.com"}'

# 4. If you get 503, one or more required SMTP variables are missing
# If you get 200 but no email arrives, check logs for SMTP errors
```

**Common issues:**
- **503 Service Unavailable** — One or more required variables are missing. Check that `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, and `EMAIL_FROM` are all set.
- **Email not received** — Check backend logs for SMTP errors. For Gmail, ensure you're using an [app-specific password](https://myaccount.google.com/apppasswords), not your regular password.
- **TLS errors** — If using port 587, ensure `SMTP_TLS=true`. If using port 465, you may need `SMTP_TLS=false` (implicit SSL).

## Testing Password Reset Locally

To test password reset without deploying a real SMTP server:

### Option 1: Use MailHog (Recommended for Local Development)

MailHog is a lightweight local SMTP server with a web UI for inspecting sent emails. No external dependencies.

**Step 1: Start MailHog**
```bash
docker run -d -p 1025:1025 -p 8025:8025 mailhog/mailhog
```

This starts:
- **SMTP server** on port 1025 (for the backend)
- **Web UI** on port 8025 (for viewing emails)

**Step 2: Configure the backend `.env`**
```dotenv
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USER=
SMTP_PASSWORD=
EMAIL_FROM=noreply@example.com
SMTP_TLS=false
```

Note: `SMTP_USER` and `SMTP_PASSWORD` can be empty for MailHog.

**Step 3: Test the flow**

```bash
# 1. Create an account
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "TestPassword123!"
  }'

# 2. Request password reset
curl -X POST http://localhost:8000/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# 3. Open MailHog web UI and view the email
# Visit: http://localhost:8025
# You'll see the password reset link with the token
```

**Step 4: Extract the reset token and use it**

From the email displayed in MailHog, copy the reset URL and extract the token:

```bash
# Example URL from email: http://localhost:3000/reset-password?token=eyJhbGciOi...
# Extract the token value and use it:

curl -X POST http://localhost:8000/api/v1/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "token": "eyJhbGciOi...",
    "new_password": "NewPassword456!"
  }'
```

### Option 2: Use Gmail (For Production-Like Testing)

To test with a real email provider (Gmail):

**Step 1: Prepare your Google account**
1. Enable 2-factor authentication on your Google account
2. Go to [Google Account Security](https://myaccount.google.com/security)
3. Scroll to "Your Google Account" → "App passwords"
4. Generate an app-specific password (select "Mail" and "Windows Computer" or similar)
5. Copy the generated 16-character password

**Step 2: Configure the backend `.env`**
```dotenv
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-actual-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
EMAIL_FROM=your-actual-email@gmail.com
SMTP_TLS=true
```

**Step 3: Test the flow**

Same as MailHog above, but emails will be sent to your actual Gmail inbox.

---

# Google OAuth 2.0

## Overview

Google OAuth allows users to log in using their Google account. The system automatically provisions a local account on first login and links subsequent logins to the same account.

## Prerequisites

1. A Google Cloud project
2. OAuth 2.0 credentials (Client ID and Client Secret)
3. Registered redirect URI

## Setup

**Step 1: Create a Google Cloud project**

1. Open [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown and select **New Project**
3. Enter a project name (e.g., "Trade Sensei") and click **Create**

**Step 2: Enable the Google+ API**

1. In the Cloud Console, go to **APIs & Services → Library**
2. Search for "Google+ API" and click **Enable**

**Step 3: Create OAuth 2.0 credentials**

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth 2.0 Client ID**
3. Select **Web application** as the application type
4. Under **Authorized redirect URIs**, add:
   - For local development: `http://localhost:8000/api/v1/auth/google/callback`
   - For production: `https://your-domain.com/api/v1/auth/google/callback`
5. Click **Create** and copy the **Client ID** and **Client Secret**

**Step 4: Configure environment variables**

Add these to your `.env` file:

```dotenv
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
```

## Google OAuth Flow

**1. Initiate login**

Redirect the user to the Google authorization page:

```bash
curl -X GET http://localhost:8000/api/v1/auth/google
```

This redirects to Google's authorization URL. The user grants access to their profile and email.

**2. Handle callback**

Google redirects back to `/api/v1/auth/google/callback` with an authorization code. The backend:
- Exchanges the code for an ID token
- Extracts the user's email and name
- Provisions or links the local account
- Sets the refresh token cookie
- Redirects to the frontend with a one-time token: `https://localhost:3000/auth/callback?token=<one-time-token>`

**3. Exchange one-time token**

The frontend exchanges the one-time token for an access token:

```bash
curl -X POST http://localhost:8000/api/v1/auth/google/exchange \
  -H "Content-Type: application/json" \
  -d '{"one_time_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

## Account Linking

When a user logs in with Google:

1. **Existing OAuth user** — If a user with the same Google `sub` (subject ID) exists, they are logged in
2. **Existing local user** — If a user with the same email exists, their account is automatically linked to Google
3. **New user** — If no match is found, a new OAuth-only account is created with an auto-generated username

## Testing Locally

For local testing, you can use the same Google OAuth credentials as production, or create a separate test project. Make sure to add `http://localhost:8000/api/v1/auth/google/callback` to the authorized redirect URIs.

---

# OpenID Connect (OIDC)

## Overview

Generic OIDC support allows integration with any OIDC-compliant provider, including:
- **Authentik** — self-hosted identity provider
- **Keycloak** — open-source identity and access management
- **Auth0** — commercial identity platform
- **Okta** — enterprise identity management
- Any other OIDC-compliant provider

## Prerequisites

1. An OIDC provider with a public configuration URL
2. A registered application/client in the provider
3. Client ID and Client Secret
4. Registered redirect URI

## Generic OIDC Setup

**Step 1: Register the application**

In your OIDC provider, create a new application/client with:
- **Application type:** Web application
- **Redirect URI:** `http://localhost:8000/api/v1/auth/oidc/callback` (local) or `https://your-domain.com/api/v1/auth/oidc/callback` (production)
- **Scopes:** `openid`, `email`, `profile`

Copy the **Client ID** and **Client Secret**.

**Step 2: Find the configuration URL**

Most OIDC providers expose a `.well-known/openid-configuration` endpoint. Examples:

- **Authentik:** `https://auth.example.com/application/o/<app-slug>/.well-known/openid-configuration`
- **Keycloak:** `https://keycloak.example.com/realms/<realm>/.well-known/openid-configuration`
- **Auth0:** `https://<domain>.auth0.com/.well-known/openid-configuration`

**Step 3: Configure environment variables**

```dotenv
OIDC_ENABLED=true
OIDC_PROVIDER_NAME=Authentik
OIDC_CONFIGURATION_URL=https://auth.example.com/application/o/tradesensei/.well-known/openid-configuration
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret
OIDC_REDIRECT_URI=http://localhost:8000/api/v1/auth/oidc/callback
```

## OIDC Flow

The flow is identical to Google OAuth:

**1. Initiate login**

```bash
curl -X GET http://localhost:8000/api/v1/auth/oidc
```

Redirects to the OIDC provider's authorization page.

**2. Handle callback**

The provider redirects back to `/api/v1/auth/oidc/callback`. The backend:
- Exchanges the authorization code for tokens
- Extracts user info (email, name, etc.)
- Provisions or links the local account
- Sets the refresh token cookie
- Redirects to the frontend with a one-time token

**3. Exchange one-time token**

```bash
curl -X POST http://localhost:8000/api/v1/auth/oidc/exchange \
  -H "Content-Type: application/json" \
  -d '{"one_time_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}'
```

## Authentik Setup (Example)

Authentik is a self-hosted identity provider. Here's how to set it up with Trade Sensei:

### Step 1: Create an Application in Authentik

1. Log in to Authentik admin panel
2. Go to **Applications → Applications**
3. Click **Create**
4. Fill in:
   - **Name:** Trade Sensei
   - **Slug:** tradesensei
   - **Provider:** Create a new OAuth2/OpenID Connect provider
5. In the provider settings:
   - **Redirect URIs:** `http://localhost:8000/api/v1/auth/oidc/callback`
   - **Scopes:** `openid`, `email`, `profile`
6. Save and note the **Client ID** and **Client Secret**

### Step 2: Get the Configuration URL

The configuration URL is:
```
https://your-authentik-instance.com/application/o/tradesensei/.well-known/openid-configuration
```

### Step 3: Configure Trade Sensei

```dotenv
OIDC_ENABLED=true
OIDC_PROVIDER_NAME=Authentik
OIDC_CONFIGURATION_URL=https://your-authentik-instance.com/application/o/tradesensei/.well-known/openid-configuration
OIDC_CLIENT_ID=<client-id-from-authentik>
OIDC_CLIENT_SECRET=<client-secret-from-authentik>
OIDC_REDIRECT_URI=http://localhost:8000/api/v1/auth/oidc/callback
```

### Step 4: Test the Flow

Navigate to `http://localhost:3000/login` and click the Authentik login button.

---

# OIDC-Only Configuration

To disable traditional password login and use only OIDC (or Google OAuth), set:

```dotenv
LOCAL_AUTH_DISABLED=true
```

**Important:** This flag is ignored if no external provider (Google or OIDC) is configured. This prevents accidental lockout.

## Behavior

When `LOCAL_AUTH_DISABLED=true` and at least one external provider is configured:

- The login page hides the username/password form
- Only OAuth/OIDC buttons are shown
- Users cannot register with a password
- Existing local accounts can still log in with their password (for migration purposes)

## Migrating Existing Users

If you have existing local accounts and want to switch to OIDC-only:

1. **Phase 1:** Enable OIDC alongside local auth
   - Users can log in with either method
   - Accounts with matching emails are automatically linked

2. **Phase 2:** Set `LOCAL_AUTH_DISABLED=true`
   - New users can only use OIDC
   - Existing users can still use their password (for backward compatibility)

3. **Phase 3 (optional):** Disable password login entirely
   - Require all users to use OIDC
   - This requires code changes to remove password login support

---

# Authentication Configuration Endpoint

The frontend can query the authentication configuration to determine which login methods are available.

**Endpoint:** `GET /api/v1/auth/config`

**Response:**
```json
{
  "google_enabled": true,
  "oidc": {
    "enabled": true,
    "provider_name": "Authentik"
  },
  "local_auth_enabled": true,
  "password_reset_enabled": true
}
```

This endpoint is used by the frontend to:
- Show/hide login buttons
- Display the correct provider name
- Enable/disable the password reset form

---

# Troubleshooting

### Password Reset Email Not Received

**Check SMTP configuration:**
```bash
# Verify all SMTP variables are set
echo $SMTP_HOST $SMTP_PORT $SMTP_USER $EMAIL_FROM
```

**Check logs:**
```bash
# Look for SMTP errors in the backend logs
docker logs tradesensei-backend | grep -i smtp
```

**Test with MailHog:**
Use MailHog (see section 3.3) to verify emails are being sent.

### Google OAuth Redirect URI Mismatch

**Error:** `redirect_uri_mismatch`

**Solution:**
1. Check that `GOOGLE_REDIRECT_URI` matches exactly what's registered in Google Cloud Console
2. Ensure the protocol (http/https) matches
3. Ensure the port number matches (e.g., `:8000` for local development)

### OIDC Configuration Not Found

**Error:** `OIDC is not configured or enabled`

**Solution:**
1. Verify `OIDC_ENABLED=true` is set
2. Verify `OIDC_CONFIGURATION_URL` is correct and accessible
3. Test the configuration URL in a browser:
   ```bash
   curl https://your-provider.com/application/o/app/.well-known/openid-configuration
   ```

### Refresh Token Expired

**Error:** `401 Unauthorized — Invalid or expired refresh token`

**Solution:**
- Refresh tokens expire after 7 days
- User must log in again
- This is expected behavior for security

### Account Linking Not Working

**Symptom:** User logs in with Google, but a new account is created instead of linking to existing account

**Cause:** Email addresses don't match

**Solution:**
1. Ensure the email in the OIDC provider matches the email in the local account
2. Check that the OIDC provider is returning the email in the user info
3. For Authentik, verify the email attribute is mapped correctly

---

# API Reference

### Authentication Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/auth/register` | Register a new user |
| `POST` | `/api/v1/auth/token` | Login with username/password |
| `POST` | `/api/v1/auth/refresh` | Refresh access token |
| `POST` | `/api/v1/auth/logout` | Logout and invalidate refresh tokens |
| `GET` | `/api/v1/auth/config` | Get authentication configuration |
| `POST` | `/api/v1/auth/forgot-password` | Request password reset email |
| `POST` | `/api/v1/auth/reset-password` | Reset password with token |
| `GET` | `/api/v1/auth/google` | Initiate Google OAuth |
| `GET` | `/api/v1/auth/google/callback` | Google OAuth callback |
| `POST` | `/api/v1/auth/google/exchange` | Exchange one-time OAuth token |
| `GET` | `/api/v1/auth/oidc` | Initiate OIDC login |
| `GET` | `/api/v1/auth/oidc/callback` | OIDC callback |
| `POST` | `/api/v1/auth/oidc/exchange` | Exchange one-time OIDC token |

### Source Files

- **Route handlers:** `backend/app/api/v1/auth.py`
- **Business logic:** `backend/app/services/auth_service.py`
- **Configuration:** `backend/app/core/config.py`
- **Security utilities:** `backend/app/core/security.py`
- **Email utilities:** `backend/app/core/email.py`
- **User model:** `backend/app/models/user.py`
- **Schemas:** `backend/app/schemas/auth.py`, `backend/app/schemas/user.py`

---

# Security Considerations

### Token Security

- **Access tokens** are short-lived (15 minutes) to limit exposure if compromised
- **Refresh tokens** are stored as httpOnly Secure cookies, preventing JavaScript access
- **Token rotation** on refresh invalidates old tokens
- **Token versioning** allows instant logout across all devices

### Password Security

- Passwords are hashed with bcrypt (not stored in plain text)
- Password reset tokens are single-use and expire after 1 hour
- Password reset invalidates all active sessions

### OIDC Security

- OIDC uses industry-standard OAuth 2.0 Authorization Code Flow
- State parameter prevents CSRF attacks
- Email verification is required before account provisioning

### Email Security

- Password reset emails are sent over TLS
- Reset links include a cryptographically signed token
- Tokens are single-use and expire quickly

---

# Environment Variables Reference

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `SECRET_KEY` | `str` | — | Yes | 32+ character key for JWT signing |
| `LOCAL_AUTH_DISABLED` | `bool` | `false` | No | Hide password login form (requires external provider) |
| `GOOGLE_CLIENT_ID` | `str` | — | No | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | `str` | — | No | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | `str` | `http://localhost:8000/api/v1/auth/google/callback` | No | Google OAuth redirect URI |
| `OIDC_ENABLED` | `bool` | `false` | No | Enable generic OIDC provider |
| `OIDC_PROVIDER_NAME` | `str` | `OpenID Connect` | No | Display name for OIDC provider |
| `OIDC_CONFIGURATION_URL` | `str` | — | No | OIDC provider configuration URL |
| `OIDC_CLIENT_ID` | `str` | — | No | OIDC client ID |
| `OIDC_CLIENT_SECRET` | `str` | — | No | OIDC client secret |
| `OIDC_REDIRECT_URI` | `str` | `http://localhost:8000/api/v1/auth/oidc/callback` | No | OIDC redirect URI |
| `SMTP_HOST` | `str` | — | No | SMTP server hostname |
| `SMTP_PORT` | `int` | `587` | No | SMTP server port |
| `SMTP_USER` | `str` | — | No | SMTP authentication username |
| `SMTP_PASSWORD` | `str` | — | No | SMTP authentication password |
| `EMAIL_FROM` | `str` | — | No | Sender email address |
| `SMTP_TLS` | `bool` | `true` | No | Use STARTTLS for SMTP |

---

# Deployment & Configuration Summary

This section provides a quick reference for environment variables and their placement, especially relevant for Kubernetes deployments.

## Local Authentication (Username/Password)

| Variable | Placement | Description |
|----------|-----------|-------------|
| `SECRET_KEY` | **Backend** | JWT signature key (Min 32 chars) |
| `ALLOWED_HOSTS` | **Backend** | CORS allowed origins |
| `DATABASE_URL` | **Backend** | Database connection string |

*Note: No special variables are required for the frontend.*

## Password Reset (SMTP) — Complete Checklist

To enable password reset, you **must** set all 4 required variables on the **Backend**:

| Variable | Placement | Description | Required |
|----------|-----------|-------------|----------|
| `SMTP_HOST` | **Backend** | SMTP server hostname (e.g., `smtp.gmail.com`) | ✅ Yes |
| `SMTP_PORT` | **Backend** | SMTP server port (defaults to 587) | No |
| `SMTP_USER` | **Backend** | SMTP authentication username | ✅ Yes |
| `SMTP_PASSWORD` | **Backend** | SMTP authentication password (Secret) | ✅ Yes |
| `EMAIL_FROM` | **Backend** | **Sender email address** ⚠️ Often forgotten! | ✅ Yes |
| `SMTP_TLS` | **Backend** | Use STARTTLS (defaults to true) | No |

**If any of the 4 required variables are missing:**
- `POST /api/v1/auth/forgot-password` returns `503 Service Unavailable`
- Password reset will not work
- Check the backend logs: `docker logs tradesensei-backend | grep -i smtp`

**Why Backend?** The backend handles all email-sending logic. The frontend triggers the request via API but never touches SMTP.

## Disabling Local Authentication

To enforce OIDC/Google login only, follow these steps:

1.  **Requirement:** Ensure Google or OIDC is configured and working.
2.  **Configuration:** Set `LOCAL_AUTH_DISABLED=true` in the **Backend**.
3.  **Effect:** The frontend automatically hides the password form based on the `/api/v1/auth/config` endpoint.

| Variable | Placement | Description |
|----------|-----------|-------------|
| `LOCAL_AUTH_DISABLED` | **Backend** | Set to `true` to hide local login (requires external provider) |

## Google OAuth 2.0 Login

| Variable | Placement | Description |
|----------|-----------|-------------|
| `GOOGLE_CLIENT_ID` | **Backend** | Google OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | **Backend** | Google OAuth Client Secret (Secret) |
| `GOOGLE_REDIRECT_URI` | **Backend** | e.g. `https://app.com/api/v1/auth/google/callback` |

## OIDC Configuration

| Variable | Placement | Description |
|----------|-----------|-------------|
| `OIDC_ENABLED` | **Backend** | Set to `true` to enable OIDC |
| `OIDC_PROVIDER_NAME` | **Backend** | Display name (e.g., `Authentik`, `Keycloak`) |
| `OIDC_CONFIGURATION_URL` | **Backend** | OIDC provider `.well-known/openid-configuration` URL |
| `OIDC_CLIENT_ID` | **Backend** | OIDC client ID |
| `OIDC_CLIENT_SECRET` | **Backend** | OIDC client secret (Secret) |
| `OIDC_REDIRECT_URI` | **Backend** | e.g. `https://app.com/api/v1/auth/oidc/callback` |

## Kubernetes Deployment Best Practices

*   **Separation:** Backend and Frontend variables must be configured in their respective deployment manifests.
*   **Secrets:** Use Kubernetes `Secret` for sensitive values: `SECRET_KEY`, `GOOGLE_CLIENT_SECRET`, `OIDC_CLIENT_SECRET`, `SMTP_PASSWORD`.
*   **ConfigMaps:** Use `ConfigMap` for non-sensitive data like `SMTP_HOST`, `GOOGLE_CLIENT_ID`, `OIDC_PROVIDER_NAME`, or `ALLOWED_HOSTS`.
*   **Injection:** SMTP, OAuth, and OIDC variables **must** be injected into the backend deployment only.

## Quick Troubleshooting for Password Reset

| Problem | Cause | Solution |
|---------|-------|----------|
| `503 Service Unavailable` on forgot-password | One or more SMTP variables missing | Verify all 4 are set: `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM` |
| Email not received | SMTP credentials wrong or TLS error | Test with MailHog first (see Password Reset section) |
| Gmail: "Invalid credentials" | Using regular password instead of app password | Generate app-specific password at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) |
| Backend logs show SMTP errors | TLS/port mismatch | Port 587 = STARTTLS (SMTP_TLS=true), Port 465 = implicit SSL (SMTP_TLS=false) |

---

## Summary

This authentication guide covers:

1. **Local Auth** (username/password) — Registration, login, token refresh, logout
2. **Password Reset** — SMTP configuration checklist, testing with MailHog/Gmail, troubleshooting
3. **Google OAuth** — Setup in Google Cloud Console, callback flow, account linking
4. **OIDC** — Generic setup with examples for Authentik, Keycloak, Auth0
5. **OIDC-Only Mode** — Disable local auth and enforce federation
6. **Deployment & Configuration** — Variable placement, Kubernetes best practices, troubleshooting table

**Key Takeaway:** If password reset is not working after you configured SMTP, check that **all 4 required variables are set**: `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM`. Even one missing will cause a `503 Service Unavailable` error.

---

**Last updated:** 2026-04-19
