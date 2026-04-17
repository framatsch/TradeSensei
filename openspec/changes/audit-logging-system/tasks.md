## 1. Core Audit Service Implementation

- [ ] 1.1 Create `backend/app/services/audit_service.py` with `AuditEventService` class
- [ ] 1.2 Implement `create_audit_event()` method with structured JSON log format
- [ ] 1.3 Implement email hashing function using SHA256 with lowercase normalization
- [ ] 1.4 Implement timestamp formatting as ISO 8601 with microseconds (UTC)
- [ ] 1.5 Implement UUID v4 request ID generation
- [ ] 1.6 Add sensitive data filtering (exclude P&L, commissions, passwords, tokens)
- [ ] 1.7 Add support for optional metadata fields (parent_resource_id, metadata JSON)
- [ ] 1.8 Configure Python JSON logger to output to stdout

## 2. Audit Middleware Implementation

- [ ] 2.1 Create `backend/app/core/audit_middleware.py` with `AuditMiddleware` class
- [ ] 2.2 Implement request interception for all authenticated endpoints
- [ ] 2.3 Add JWT token extraction to get `user_id` from `get_current_user` dependency
- [ ] 2.4 Implement IP address extraction from `request.client.host`
- [ ] 2.5 Add X-Forwarded-For header parsing for proxied requests
- [ ] 2.6 Extract user-agent from request headers
- [ ] 2.7 Implement HTTP method filtering (log POST/PUT/PATCH/DELETE, skip GET unless DEBUG)
- [ ] 2.8 Add health endpoint filter (skip `/health` requests)
- [ ] 2.9 Implement resource ID extraction from URL paths using regex patterns
- [ ] 2.10 Implement action inference from HTTP method + path (e.g., `POST /trades` → `trade.created`)
- [ ] 2.11 Add special handling for auth endpoints (`/api/v1/auth/token` → `auth.login`)
- [ ] 2.12 Implement synchronous logging with try/except error handling
- [ ] 2.13 Add logging for authentication failures (invalid/expired tokens)
- [ ] 2.14 Implement unhandled exception catching with action `error.unhandled`
- [ ] 2.15 Add structured exception logging (type, message, stack trace, correlation ID)
- [ ] 2.16 Implement HTTP error response logging (4xx, 5xx status codes)
- [ ] 2.17 Add specific error action patterns (`error.not_found`, `error.forbidden`, `error.validation`, `error.internal`)

## 3. Middleware Registration

- [ ] 3.1 Register `AuditMiddleware` in `backend/app/main.py` after CORS and Session middleware
- [ ] 3.2 Verify middleware execution order (audit runs before route handlers)
- [ ] 3.3 Test that middleware doesn't interfere with existing request/response flow

## 4. Action Mapping Configuration

- [ ] 4.1 Create action mapping dictionary for special routes (auth, imports, merges)
- [ ] 4.2 Add route-level metadata support for complex operations (bulk ops, merges)
- [ ] 4.3 Document action naming conventions in code comments

## 5. Testing

- [ ] 5.1 Write unit tests for `AuditEventService` email hashing
- [ ] 5.2 Write unit tests for timestamp formatting
- [ ] 5.3 Write unit tests for sensitive data filtering
- [ ] 5.4 Write integration tests for middleware request interception
- [ ] 5.5 Write integration tests for resource ID extraction from various URL patterns
- [ ] 5.6 Write integration tests for action inference from HTTP method + path
- [ ] 5.7 Test middleware handles missing user context (unauthenticated requests)
- [ ] 5.8 Test middleware handles X-Forwarded-For header correctly
- [ ] 5.9 Test middleware filters health endpoint
- [ ] 5.10 Test middleware logs write operations but not read operations (unless DEBUG)
- [ ] 5.11 Test middleware error handling (logging failure doesn't break request)
- [ ] 5.12 Test authentication failure logging
- [ ] 5.13 Test unhandled exception logging with stack traces
- [ ] 5.14 Test HTTP error response logging (404, 403, 422, 500)
- [ ] 5.15 Test validation error logging with field details
- [ ] 5.16 Test database error logging with correlation IDs

## 6. Grafana Dashboard Creation

- [ ] 6.1 Create `grafana/dashboards/audit.json` dashboard definition
- [ ] 6.2 Add "Logins by User" time-series panel with Loki query for `auth.login` events
- [ ] 6.3 Add "Failed Login Attempts" panel grouped by IP address
- [ ] 6.4 Add "Actions by Type" bar chart panel grouped by `action` field
- [ ] 6.5 Add "Actions by IP Address" table panel with columns: IP, count, unique users, last seen
- [ ] 6.6 Add "Resource Operations Timeline" panel for create/update/delete events
- [ ] 6.7 Add "Import Activity" panel for import events with metadata (record counts)
- [ ] 6.8 Add "Raw Log Viewer" panel for JSON log inspection
- [ ] 6.9 Configure time range picker with presets (15m, 1h, 6h, 24h, 7d, 30d)
- [ ] 6.10 Configure auto-refresh with 30-second default interval
- [ ] 6.11 Add dashboard variables for filtering by user_id, action, ip_address, email_hash
- [ ] 6.12 Add "Error Rate" panel for tracking `error.*` actions over time
- [ ] 6.13 Add "Top Errors" panel grouped by exception type
- [ ] 6.14 Test dashboard with sample audit logs from staging environment

## 7. Deployment and Validation

- [ ] 7.1 Deploy audit middleware to staging environment
- [ ] 7.2 Verify structured JSON logs appear in Loki (query via Grafana Explore)
- [ ] 7.3 Verify log format matches spec (all required fields present)
- [ ] 7.4 Verify email hashing works correctly (consistent hashes for same email)
- [ ] 7.5 Verify sensitive data is NOT logged (check logs for P&L, prices, passwords)
- [ ] 7.6 Verify 90-day retention policy in Loki (existing configuration)
- [ ] 7.7 Monitor log volume and performance impact (<1ms latency confirmed)
- [ ] 7.8 Import Grafana dashboard and validate all panels display data
- [ ] 7.9 Test dashboard filters and time range selection
- [ ] 7.10 Deploy to production after staging validation

## 8. AGENTS.md Policy Documentation

- [ ] 8.1 Add "Audit Logging Policy" section to AGENTS.md
- [ ] 8.2 Document automatic audit coverage for POST/PUT/PATCH/DELETE endpoints
- [ ] 8.3 Document sensitive data exclusion list (P&L, commissions, prices, passwords, tokens)
- [ ] 8.4 Document action naming conventions (`<resource>.<verb>` format)
- [ ] 8.5 Document error logging requirements (try/except with logger.error)
- [ ] 8.6 Add code review checklist for audit logging compliance
- [ ] 8.7 Link to implementation examples (middleware auto-logging, manual events, error logging)
- [ ] 8.8 Instruct backend-engineer agent to verify audit logging for new features
- [ ] 8.9 Instruct frontend-engineer agent to verify backend audit logging exists
- [ ] 8.10 Instruct code-reviewer agent to check audit policy compliance

## 9. Documentation and Compliance

- [ ] 9.1 Update Privacy Policy to mention IP logging for security purposes (DSGVO Art. 6(1)(f))
- [ ] 9.2 Document audit log fields in `docs/audit-logging.md`
- [ ] 9.3 Document error logging patterns in `docs/audit-logging.md`
- [ ] 9.4 Document Grafana dashboard usage in `docs/grafana-audit-dashboard.md`
- [ ] 9.5 Add code comments explaining action inference logic
- [ ] 9.6 Add code comments explaining exception handling and error categorization
- [ ] 9.7 Update CHANGELOG.md with new audit logging feature
