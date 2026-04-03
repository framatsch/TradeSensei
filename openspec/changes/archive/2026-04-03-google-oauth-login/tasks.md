## 1. Backend — Dependencies & Config

- [x] 1.1 Add `authlib>=1.3` to `backend/pyproject.toml` and run `uv lock`
- [x] 1.2 Add `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` fields to `backend/app/core/config.py`
- [x] 1.3 Update `.env.example` with the three new Google env vars and `NEXTAUTH_SECRET`, `NEXTAUTH_URL`

## 2. Backend — Database Migration

- [x] 2.1 Add `provider VARCHAR(20) NOT NULL DEFAULT 'local'` and `provider_id VARCHAR(255) NULL` columns to the `users` ORM model (`backend/app/models/user.py`)
- [x] 2.2 Make `hashed_password` nullable in the ORM model
- [x] 2.3 Create Alembic migration: add `provider`, `provider_id` columns; make `hashed_password` nullable; add unique index on `(provider, provider_id)` where `provider_id IS NOT NULL`
- [x]  2.4 Apply migration and verify it runs cleanly

## 3. Backend — Repository & Service

- [x] 3.1 Add `get_by_provider_id(provider: str, provider_id: str)` method to `backend/app/repositories/user_repository.py`
- [x] 3.2 Add `create_oauth_user(email, username, provider, provider_id)` method to `user_repository.py`
- [x] 3.3 Add `link_google_account(user_id, provider_id)` method to `user_repository.py`
- [x] 3.4 Update `login` in `backend/app/services/auth_service.py` to reject password login for `provider != 'local'` accounts (HTTP 401 `oauth_account_no_password`)
- [x] 3.5 Add `google_oauth_login(google_id_token_data)` method to `auth_service.py`: lookup by `provider_id`, fallback to email link, fallback to create new user, issue JWT pair + one-time token
- [x] 3.6 Implement one-time token generation and validation in `backend/app/core/security.py` (short-lived JWT with `jti` claim stored in a simple in-memory dict or DB-backed set)

## 4. Backend — Routes

- [x] 4.1 Add `GET /api/v1/auth/google` route to `backend/app/api/v1/auth.py` — redirects to Google authorization URL using `authlib`
- [x] 4.2 Add `GET /api/v1/auth/google/callback` route — validates state, exchanges code, calls `auth_service.google_oauth_login`, sets refresh cookie, redirects to frontend `/auth/callback?token=<one_time_token>`
- [x] 4.3 Add `POST /api/v1/auth/google/exchange` route — accepts one-time token body, returns `TokenResponse`
- [x] 4.4 Register the new routes in the FastAPI app router

## 5. Backend — OpenAPI & Schemas

- [x] 5.1 Add `OAuthExchangeRequest` Pydantic schema (`one_time_token: str`) to `backend/app/schemas/auth.py`
- [x] 5.2 Annotate new routes with correct response models, status codes, and docstrings

## 6. Frontend — Dependencies & NextAuth Config

- [x] 6.1 Add `next-auth` to `frontend/package.json` and run `npm install`
- [x] 6.2 Create `frontend/app/api/auth/[...nextauth]/route.ts` with Google provider configured (client ID/secret from env)
- [x] 6.3 Add `NEXTAUTH_SECRET`, `NEXTAUTH_URL`, `NEXT_PUBLIC_GOOGLE_CLIENT_ID` to `frontend/.env.example`

## 7. Frontend — OAuth Callback Page

- [x] 7.1 Create `frontend/app/(auth)/auth/callback/page.tsx` — reads `?token=` from URL, posts to `/api/v1/auth/google/exchange`, stores access token in Zustand store, redirects to `/dashboard`
- [x] 7.2 Handle error query params (`?error=oauth_cancelled`, etc.) with user-friendly message on the login page

## 8. Frontend — UI

- [x] 8.1 Add `GoogleSignInButton` component to `frontend/components/auth/` (calls `signIn("google")` from next-auth)
- [x] 8.2 Add the button and a visual divider to `frontend/components/auth/LoginForm.tsx`
- [x] 8.3 Add the button and a visual divider to `frontend/components/auth/RegisterForm.tsx`

## 9. API Client Sync

- [x] 9.1 Run `openapi-sync` skill to regenerate the frontend TypeScript API client after backend route changes

## 10. Tests

- [x] 10.1 Unit tests for `auth_service.google_oauth_login` — new user, email link, existing Google user (mock repository)
- [x] 10.2 Unit tests for one-time token generate/validate in `security.py`
- [x] 10.3 Integration tests for `GET /auth/google` (verify redirect), `POST /auth/google/exchange` (valid + expired token)
- [x] 10.4 Test that password login returns 401 for a Google-only account

## 11. Lint & Type Check

- [x] 11.1 Run `lint-check` skill — fix any ruff or mypy errors introduced by the new code
