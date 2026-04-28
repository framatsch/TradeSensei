## Why

The frontend currently uses two different API clients: a legacy Axios instance (`frontend/lib/api.ts`) and a newly generated `@hey-api/client-fetch` SDK (`frontend/lib/api/client.gen.ts`). The generated client is not properly configured with the authorization token or the correct base URL (`/api/proxy`), which causes authentication and CORS errors when used. Maintaining two clients is significant technical debt and prevents the frontend from fully leveraging the type safety and auto-updating benefits of the OpenAPI-generated SDK. Consolidating the API layer ensures consistent behavior, better security (authorization headers applied correctly everywhere), and eliminates boilerplate.

## What Changes

- **Configure Generated SDK**: Initialize the `@hey-api` client to use `/api/proxy` as the base URL and attach the JWT token from `localStorage` to all requests.
- **Global Error Handling**: Add a response interceptor to the `@hey-api` client to handle 401 Unauthorized errors and trigger a logout.
- **Migrate API Calls**: Replace all legacy Axios API calls across the frontend (components, stores, React Query hooks) with the typsafe `@hey-api` client functions.
- **Remove Legacy Client**: Delete `frontend/lib/api.ts` and remove the `axios` dependency once the migration is complete.

## Capabilities

### New Capabilities
- `frontend-api-client`: A centralized, typsafe, auto-generated API client that handles authentication, base URL routing, and global error handling for all frontend-backend communication.

### Modified Capabilities
- None

## Impact

- All frontend files that currently import `frontend/lib/api.ts` (Axios) will be refactored to use the generated functions from `frontend/lib/api/`.
- Frontend dependencies: The `axios` package will be removed.
- Security: Consistent JWT token attachment for all endpoints, ensuring users can only read their own data via securely authenticated requests.
