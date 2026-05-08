## ADDED Requirements

### Requirement: Centralized Generated API Client
The frontend application SHALL execute all backend API requests exclusively using the automatically generated `@hey-api/client-fetch` SDK. The legacy Axios client SHALL be completely removed.

#### Scenario: Submitting an API Request
- **WHEN** a user action triggers a backend API request (e.g., fetching a portfolio)
- **THEN** the request is constructed and sent using the generated `@hey-api` client function

### Requirement: Authentication Header Injection
The generated `@hey-api` SDK SHALL automatically inject the user's `access_token` from `localStorage` into the Authorization header of every outgoing API request.

#### Scenario: Attaching the JWT Token
- **WHEN** the `@hey-api` SDK dispatches a request and an `access_token` exists in `localStorage`
- **THEN** the SDK interceptor attaches the header `Authorization: Bearer <token>` to the request before sending it to the server

#### Scenario: Requesting Without Token
- **WHEN** the `@hey-api` SDK dispatches a request and no `access_token` is present
- **THEN** the request proceeds without an Authorization header, allowing the backend to handle the unauthenticated state

### Requirement: Relative Proxy Base URL Routing
The generated `@hey-api` SDK SHALL be configured globally to use the relative path `/api/proxy` as its base URL, ensuring requests route correctly through the Next.js reverse proxy.

#### Scenario: Base URL Construction
- **WHEN** the `@hey-api` client makes a request to an endpoint (e.g., `/api/v1/portfolios`)
- **THEN** the request URL is constructed as `/api/proxy/api/v1/portfolios`

### Requirement: Global Unauthorized Error Handling
The `@hey-api` SDK SHALL capture any `401 Unauthorized` response globally and forcefully redirect the user to the `/login` page while clearing the invalid `access_token`.

#### Scenario: Handling 401 Responses
- **WHEN** an API request returns an HTTP status of `401` and the user is not currently on the `/login` route
- **THEN** the `access_token` is removed from `localStorage` and the browser is redirected to `/login`

### Requirement: No Direct HTTP Calls in UI Code
Frontend components, stores, and hooks SHALL NOT call `fetch()`, `axios`, or any HTTP library directly. All backend communication MUST go through the generated `@hey-api` SDK functions exported from `frontend/lib/api/`.

#### Scenario: Component Fetching Data
- **WHEN** a React component or Zustand store needs to load data from the backend
- **THEN** it calls the corresponding generated function (e.g., `listPortfoliosApiV1PortfoliosGet()`) and receives a fully typed response

#### Scenario: Prohibited Direct Fetch
- **WHEN** a developer introduces a call to `fetch()` or `axios` directly in a component or store
- **THEN** the code review MUST reject the change as a spec violation

### Requirement: Data Isolation via Authentication
The frontend SHALL rely exclusively on the backend's JWT-based authorization to enforce data isolation. UI components SHALL NOT implement client-side ownership checks or attempt to filter data by user ID.

#### Scenario: Fetching User-Scoped Data
- **WHEN** any API function from the `@hey-api` SDK is called
- **THEN** the attached JWT token causes the backend to return only data belonging to the authenticated user, without any additional filtering in the frontend

#### Scenario: No Client-Side Ownership Filter
- **WHEN** a component renders a list of resources (e.g., portfolios, trades)
- **THEN** the component renders exactly what the backend returned, without filtering by user ID client-side

### Requirement: Integration Tests Pass After Migration
All existing backend integration tests and any new frontend integration tests related to authentication and API routing SHALL pass without modification after the migration is complete.

#### Scenario: Pre-Existing Tests Remain Green
- **WHEN** the full test suite is executed after the migration
- **THEN** all previously passing backend integration tests continue to pass

#### Scenario: Auth Flow is Testable
- **WHEN** an integration test exercises the login → API call → response flow
- **THEN** the test verifies that the Authorization header is present and the correct data is returned for that user only
