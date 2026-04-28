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
