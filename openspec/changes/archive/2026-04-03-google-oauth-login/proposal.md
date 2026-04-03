## Why

Users currently must register with a username and password, which adds friction to onboarding. Supporting Google OAuth allows users to sign in with an existing Google account — no password to create or remember.

## What Changes

- Add Google OAuth 2.0 login flow on the backend (redirect + callback endpoints)
- Extend the `users` table with `provider` and `provider_id` columns to support OAuth accounts
- Make `hashed_password` nullable for OAuth-only users
- Install `authlib` (backend) and configure `next-auth` (frontend)
- Add a "Sign in with Google" button to the login and register pages
- Google-authenticated users receive the same JWT access/refresh token pair as password users

## Capabilities

### New Capabilities

- `google-oauth`: Google OAuth 2.0 authorization code flow — backend redirect, callback, user lookup/creation, and JWT issuance

### Modified Capabilities

- `user-auth`: `hashed_password` becomes nullable; users now have a `provider` field (`local` vs `google`)

## Impact

**Backend:**
- `backend/app/models/user.py` — add `provider`, `provider_id` columns; make `hashed_password` nullable
- `backend/app/api/v1/auth.py` — add `GET /auth/google` and `GET /auth/google/callback` routes
- `backend/app/services/auth_service.py` — add `google_oauth_login` method
- `backend/app/repositories/user_repository.py` — add `get_by_provider_id` lookup
- `backend/app/core/config.py` — add `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`
- New Alembic migration for schema changes
- New dependency: `authlib>=1.3`

**Frontend:**
- `frontend/` — install and configure `next-auth` with Google provider
- `frontend/app/api/auth/[...nextauth]/route.ts` — NextAuth route handler
- `frontend/components/auth/LoginForm.tsx` — add "Sign in with Google" button
- `frontend/components/auth/RegisterForm.tsx` — add "Sign in with Google" button
- `frontend/lib/api.ts` — adapt token injection to work with NextAuth session

**Infrastructure:**
- `.env` / `.env.example` — add `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `NEXTAUTH_SECRET`, `NEXTAUTH_URL`
