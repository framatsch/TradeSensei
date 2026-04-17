## ADDED Requirements

### Requirement: Middleware intercepts all authenticated requests

The middleware SHALL intercept all HTTP requests to authenticated API endpoints before they reach route handlers. The middleware SHALL extract user context from JWT tokens, request metadata (IP address, user-agent), and route information (HTTP method, path, resource IDs).

#### Scenario: Authenticated POST request is intercepted
- **WHEN** a user sends `POST /api/v1/trades` with valid JWT token
- **THEN** middleware extracts `user_id` from token, `ip_address` from request, and creates audit event with action `trade.created`

#### Scenario: Authenticated DELETE request is intercepted
- **WHEN** a user sends `DELETE /api/v1/trades/123` with valid JWT token
- **THEN** middleware extracts `user_id`, `resource_id=123`, and creates audit event with action `trade.deleted`

#### Scenario: Unauthenticated request bypasses audit logging
- **WHEN** a user sends `POST /api/v1/auth/token` (login, no JWT yet)
- **THEN** middleware skips JWT extraction but still logs `auth.login` event with `email_hash` from form data

---

### Requirement: Middleware logs write operations automatically

The middleware SHALL automatically log all write operations (POST, PUT, PATCH, DELETE) to authenticated endpoints. The middleware SHALL NOT log read operations (GET) unless `LOG_LEVEL=DEBUG`.

#### Scenario: POST request is logged
- **WHEN** a user sends `POST /api/v1/accounts` with valid JWT
- **THEN** middleware creates audit log entry with action `account.created`

#### Scenario: PUT request is logged
- **WHEN** a user sends `PUT /api/v1/trades/123`
- **THEN** middleware creates audit log entry with action `trade.updated`

#### Scenario: GET request is NOT logged in production
- **WHEN** a user sends `GET /api/v1/trades` and `LOG_LEVEL=INFO`
- **THEN** middleware does NOT create audit log entry

#### Scenario: GET request IS logged in debug mode
- **WHEN** a user sends `GET /api/v1/trades` and `LOG_LEVEL=DEBUG`
- **THEN** middleware creates audit log entry with action `trade.list`

---

### Requirement: Middleware extracts resource IDs from URL paths

The middleware SHALL extract resource IDs from URL path patterns like `/api/v1/{resource}/{id}`. For complex routes (merges, bulk operations), the middleware SHALL support optional route-level metadata to specify resource type and ID.

#### Scenario: Resource ID extracted from simple path
- **WHEN** a user sends `DELETE /api/v1/executions/456`
- **THEN** middleware extracts `resource_type=execution` and `resource_id=456`

#### Scenario: Resource ID extracted from nested path
- **WHEN** a user sends `POST /api/v1/accounts/5/trades`
- **THEN** middleware extracts `resource_type=trade` and `parent_resource_id=5` (account)

#### Scenario: Resource type inferred from complex route with metadata
- **WHEN** a user sends `POST /api/v1/trades/merge` (route has `audit_metadata={"resource_type": "trade"}`)
- **THEN** middleware uses metadata to set `resource_type=trade`, `resource_id=null`

---

### Requirement: Middleware infers action from HTTP method and path

The middleware SHALL infer business action names from HTTP method and URL path patterns. Actions SHALL follow the format `<resource>.<verb>` (e.g., `trade.created`, `account.deleted`).

#### Scenario: POST to collection infers created action
- **WHEN** HTTP method is `POST` and path is `/api/v1/trades`
- **THEN** action is `trade.created`

#### Scenario: DELETE to resource infers deleted action
- **WHEN** HTTP method is `DELETE` and path is `/api/v1/playbooks/10`
- **THEN** action is `playbook.deleted`

#### Scenario: PUT to resource infers updated action
- **WHEN** HTTP method is `PUT` and path is `/api/v1/notes/7`
- **THEN** action is `note.updated`

#### Scenario: POST to auth endpoint infers login action
- **WHEN** HTTP method is `POST` and path is `/api/v1/auth/token`
- **THEN** action is `auth.login`

#### Scenario: POST to logout endpoint infers logout action
- **WHEN** HTTP method is `POST` and path is `/api/v1/auth/logout`
- **THEN** action is `auth.logout`

---

### Requirement: Middleware handles X-Forwarded-For for proxied requests

The middleware SHALL check for the `X-Forwarded-For` HTTP header to determine the original client IP address when the request is proxied through nginx or a load balancer. The middleware SHALL log both `client_ip` (direct connection) and `forwarded_for` (original client) when the header is present.

#### Scenario: Direct connection logs client IP
- **WHEN** request comes directly from `192.168.1.42` with no `X-Forwarded-For` header
- **THEN** middleware logs `ip_address=192.168.1.42`, `forwarded_for=null`

#### Scenario: Proxied connection logs both IPs
- **WHEN** request comes from proxy `10.0.0.5` with `X-Forwarded-For: 203.0.113.42`
- **THEN** middleware logs `ip_address=10.0.0.5`, `forwarded_for=203.0.113.42`

---

### Requirement: Middleware uses synchronous logging with error handling

The middleware SHALL log audit events synchronously (blocking) to guarantee log entries are written to stdout before the HTTP response is sent to the client. The middleware SHALL wrap logging in try/except to prevent logging failures from breaking API requests.

#### Scenario: Audit log written before response
- **WHEN** middleware successfully logs `trade.created` event
- **THEN** log entry appears in stdout BEFORE HTTP 201 response is sent to client

#### Scenario: Logging error does not break request
- **WHEN** stdout logging fails (disk full, pipe broken)
- **THEN** middleware logs error to stderr and continues with HTTP response (status code 201)

---

### Requirement: Middleware filters health endpoint

The middleware SHALL NOT log requests to `/health` endpoint to reduce log volume from frequent healthcheck polling.

#### Scenario: Health check request not logged
- **WHEN** a user sends `GET /health`
- **THEN** middleware does NOT create audit log entry

---

### Requirement: Middleware logs authentication failures

The middleware SHALL log failed authentication attempts (invalid JWT token, expired token, inactive user) with action `auth.failed`. The log SHALL include IP address, user-agent, and attempted email hash (if extractable from token).

#### Scenario: Invalid JWT token logged as auth failure
- **WHEN** a user sends `GET /api/v1/trades` with invalid JWT token
- **THEN** middleware creates audit log with action `auth.failed`, `user_id=null`, `ip_address=<client_ip>`

#### Scenario: Expired token logged as auth failure
- **WHEN** a user sends `DELETE /api/v1/trades/123` with expired JWT token
- **THEN** middleware creates audit log with action `auth.failed`, `reason=expired_token`
