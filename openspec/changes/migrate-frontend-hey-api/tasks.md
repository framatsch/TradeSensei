## 1. Client Initialization

- [ ] 1.1 Create `frontend/lib/api/init.ts` and implement `initializeApiClient` function.
- [ ] 1.2 Configure the `@hey-api` client base URL to `/api/proxy`.
- [ ] 1.3 Add a request interceptor to the `@hey-api` client to inject the `Authorization` header using `localStorage.getItem("access_token")`.
- [ ] 1.4 Add a response interceptor to the `@hey-api` client to catch `401 Unauthorized` responses and redirect the user to `/login`.
- [ ] 1.5 Update `frontend/app/providers.tsx` to import and call `initializeApiClient()` when the application starts.

## 2. API Call Migration

- [ ] 2.1 Search the `frontend/` directory for all imports of `frontend/lib/api.ts` (e.g., `import apiClient from "@/lib/api"`).
- [ ] 2.2 Refactor authentication and user-related components/stores to use the generated SDK functions instead of Axios.
- [ ] 2.3 Refactor portfolio-related components/stores to use the generated SDK functions instead of Axios.
- [ ] 2.4 Refactor trade-related components/stores to use the generated SDK functions instead of Axios.
- [ ] 2.5 Refactor any remaining API calls (e.g., playbook, metrics, tagging) to use the generated SDK functions.

## 3. Cleanup and Verification

- [ ] 3.1 Verify that the frontend builds without type errors (`npm run build` or `tsc --noEmit`).
- [ ] 3.2 Ensure the legacy `frontend/lib/api.ts` file is completely deleted.
- [ ] 3.3 Remove the `axios` dependency from `frontend/package.json` and run `npm install`.
- [ ] 3.4 Test the portfolio creation flow in the UI to ensure the original bug is resolved and authentication works correctly.
