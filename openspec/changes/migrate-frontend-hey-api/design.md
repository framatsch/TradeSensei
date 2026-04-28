## Context

The frontend currently uses `axios` as the HTTP client configured with a base URL of `/api/proxy` and an interceptor that attaches a JWT from `localStorage`. A newly generated `@hey-api` SDK has been introduced but is currently unconfigured, leading to API calls being made to `localhost:8000` without authentication headers. The `api.ts` file acts as the central Axios client, while the generated SDK is located in `frontend/lib/api/`. Consolidating all frontend-to-backend communication under the typed `@hey-api` client improves type safety and removes technical debt.

## Goals / Non-Goals

**Goals:**
- Configure the `@hey-api` generated client globally with the correct base URL (`/api/proxy`).
- Ensure every request made via `@hey-api` automatically attaches the user's `access_token` from `localStorage` for secure, authenticated access.
- Implement global error handling (specifically `401 Unauthorized`) in the `@hey-api` client to log users out when their session expires.
- Refactor all existing frontend components, stores, and React Query hooks to use the generated `@hey-api` functions.
- Ensure that users can only interact with their own data (enforced by the backend via JWT, securely passed by the frontend).
- Remove the `axios` dependency and the legacy `api.ts` file.

**Non-Goals:**
- Changing backend API logic or authentication mechanisms.
- Changing the way the Next.js API proxy (`/api/proxy/[...path]/route.ts`) operates.
- Modifying React Query configurations or caching strategies, other than swapping the fetch function from Axios to Hey-API.

## Decisions

**1. Client Initialization Location:**
- *Decision*: Create an initialization function `initializeApiClient` in a new file `frontend/lib/api/init.ts` and call it at the application entry point (`frontend/app/providers.tsx`).
- *Rationale*: This ensures the API client is configured (base URL and interceptors) once when the application loads, before any components or stores make API calls. This aligns with how `useAppContextStore.getState().hydrate()` is currently called.

**2. Interceptor Pattern:**
- *Decision*: Use the interceptor functionality built into the `@hey-api/client-fetch` SDK (via `client.interceptors`). 
- *Rationale*: The generated client supports `request`, `response`, and `error` interceptors out of the box, mimicking the Axios pattern closely. This makes migration of the existing Axios interceptors straightforward and robust. 

**3. Token Storage:**
- *Decision*: Continue using `localStorage.getItem("access_token")`.
- *Rationale*: Modifying the storage mechanism (e.g., to HttpOnly cookies) is out of scope for this change and should be tackled as a separate security enhancement if desired later. This migration focuses purely on client unification.

## Risks / Trade-offs

- **Risk**: Missed API calls during the refactor causing broken functionality.
  *Mitigation*: Use comprehensive IDE search (`grep`) for all imports of the old `apiClient` or `axios` in the `frontend/` directory to ensure every single call is updated.
- **Risk**: Type mismatches between Axios responses (`res.data`) and Hey-API responses (`res.data` vs `res.error`).
  *Mitigation*: The `@hey-api/client-fetch` SDK returns `{ data, error, response, request }` by default. Refactoring will require careful attention to unwrap `.data` properly and check for `.error`. We will configure the client or manually handle `throwOnError: true` if needed, but standardizing on unwrap patterns is preferred.
