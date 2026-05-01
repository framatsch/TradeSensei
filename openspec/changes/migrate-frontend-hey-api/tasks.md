## 1. Client Initialization

- [x] 1.1 Create `frontend/lib/api/init.ts` and implement `initializeApiClient` function.
- [x] 1.2 Configure the `@hey-api` client base URL to `/api/proxy`.
- [x] 1.3 Add a request interceptor to the `@hey-api` client to inject the `Authorization` header using `localStorage.getItem("access_token")`.
- [x] 1.4 Add a response interceptor to the `@hey-api` client to catch `401 Unauthorized` responses and redirect the user to `/login`.
- [x] 1.5 Update `frontend/app/providers.tsx` to import and call `initializeApiClient()` when the application starts.

## 2. API Call Migration

- [x] 2.1 Search the `frontend/` directory for all imports of `frontend/lib/api.ts` (e.g., `import apiClient from "@/lib/api"`).
- [x] 2.2 Refactor authentication and user-related components/stores to use the generated SDK functions instead of Axios.
- [x] 2.3 Refactor portfolio-related components/stores to use the generated SDK functions instead of Axios.
- [x] 2.4 Refactor trade-related components/stores to use the generated SDK functions instead of Axios.
- [x] 2.5 Refactor any remaining API calls (e.g., playbook, metrics, tagging) to use the generated SDK functions.

## 3. Cleanup and Verification

- [x] 3.1 Verify that the frontend builds without type errors (`npm run build` or `tsc --noEmit`).
- [x] 3.2 Ensure the legacy `frontend/lib/api.ts` file is completely deleted.
- [x] 3.3 Remove the `axios` dependency from `frontend/package.json` and run `npm install`.
- [x] 3.4 Test the portfolio creation flow in the UI to ensure the original bug is resolved and authentication works correctly.

## 4. Bug Fixes & Hardening (OCR Code Review 2026-04-29)

> All items below are derived from OCR session `2026-04-29-devel`, verdict: REQUEST CHANGES.
> Blocker first, then should-fix, then suggestions.

### 4.1 — BLOCKER: Remove deprecated trades endpoint fallback

- [x] 4.1 In `frontend/hooks/useTrades.ts`, remove the deprecated endpoint fallback path entirely.

### 4.2 — Should Fix: Canonical error extractor

- [x] 4.2 Create `frontend/lib/api/errors.ts` with an `extractApiError(error: unknown): string` helper that reads the parsed error body from the `@hey-api` SDK (top-level `detail` field), falls back to a generic message, and never throws. Apply it in all ~24 hooks/components that currently cast errors to `{ response?: { data?: { detail?: string } } }`.

### 4.3 — Should Fix: Fix OAuth callback — wrong header passing

- [x] 4.3 In `frontend/app/(auth)/auth/callback/page.tsx`, remove the `body: { headers: { Authorization: ... } }` argument from the `/api/v1/users/me` call (the JWT interceptor in `init.ts` already handles the header). Replace both raw `client` calls in that file with the named SDK functions (`googleExchangeApiV1AuthGoogleExchangePost`, `getMeApiV1UsersMeGet`).

### 4.4 — Should Fix: Add error interceptor for 401 on network failures

- [x] 4.4 In `frontend/lib/api/init.ts`, add `client.interceptors.error.use(...)` after the response interceptor to handle 401 on network-level failures (timeout, proxy 502, DNS). Mirror the same logout + redirect logic as the response interceptor.

### 4.5 — Should Fix: Migrate Pattern C callers to named SDK functions

- [x] 4.5 Refactor `frontend/hooks/useExecutions.ts` (all 7 operations) from raw `client` + `as any` double-await (Pattern C) to the named SDK functions already exported from `@/lib/api/index`. Apply the same to `RegisterForm.tsx`, `forgot-password/page.tsx`, and `reset-password/page.tsx`.

### 4.6 — Should Fix: Fix `throw error` that can throw `undefined`

- [x] 4.6 In all migrated hooks that use `if (error || !data) throw error`, replace the throw with `throw error ?? new Error("Request failed: no data returned")`. Affected files include `useAccounts.ts`, `useNotes.ts`, `usePlaybooks.ts`, `useSavedTradeFilters.ts`, and ~11 others.

### 4.7 — Suggestion: Fix duplicate HTML IDs in PortfolioSettings

- [x] 4.7 In `frontend/components/settings/PortfolioSettings.tsx`, replace the hardcoded `id="portfolio-name"` and `id="portfolio-currency"` strings with React's `useId()` hook to generate unique IDs per form instance, preventing the accessibility regression introduced by the `htmlFor`/`id` fix.

### 4.8 — Suggestion: Set /api/proxy as default baseUrl in generator config

- [x] 4.8 Update `frontend/openapi-ts.config.ts` to write `/api/proxy` as the default `baseUrl` in the generated `client.gen.ts`. This eliminates the timing dependency on `initializeApiClient()` running before any requests and survives regeneration.

### 4.9 — Suggestion: Fix or remove unused `useRegister` hook

- [x] 4.9 In `frontend/hooks/useAuth.ts`, restore `setToken` (and the follow-up `loginApiV1AuthTokenPost` call) in `useRegister.onSuccess`, or remove the export entirely. The hook is currently unused — `RegisterForm.tsx` duplicates the logic inline — and silently broken if it were wired up.
