## Context

The Trade Sensei platform currently has minimal audit logging. Only a handful of service-layer operations log warnings or debug messages, and no systematic tracking exists for user actions. The platform serves EU users and must comply with DSGVO requirements for data processing transparency.

**Current State:**
- Uvicorn access logs: raw HTTP requests (IP, path, status code) but no user context
- Application logs: scattered debug/warning messages in services (FX rates, imports, broker operations)
- No structured logging format
- No correlation between HTTP requests and business operations
- No email anonymization
- Loki/Grafana stack already deployed and ingesting stdout logs (90-day retention configured)

**Constraints:**
- Must not log sensitive financial data (P&L, commissions, prices, strategy notes)
- Must use synchronous logging (guarantee logs written before response sent)
- Must comply with DSGVO Art. 6(1)(f) - legitimate interest for security
- Cannot add database overhead (stdout logs only, no audit_log table)
- Must work with existing FastAPI async architecture
- Must support existing JWT-based auth system (`get_current_user` dependency)

## Goals / Non-Goals

**Goals:**
- Automatically log all write operations (POST/PUT/PATCH/DELETE) to authenticated endpoints
- Log all authentication events (login success/failure, logout, token refresh)
- Capture user_id, email hash, IP address, user-agent, resource type/ID, action, timestamp
- Support optional debug-level logging for read operations (GET)
- Output structured JSON logs to stdout for Loki ingestion
- Zero performance impact on requests (<1ms overhead acceptable)
- DSGVO-compliant: anonymize emails, exclude sensitive data, support 90-day retention

**Non-Goals:**
- Frontend UI event tracking (Phase 2 - future work)
- Database audit_log table (stdout logs sufficient for now)
- User-facing "activity history" feature in UI
- Geo-location tracking (raw IP address sufficient; ad-hoc lookup if needed)
- Real-time alerting (use Grafana alerts on Loki data)
- Audit log export API for users (future DSGVO enhancement)

## Decisions

### Decision 1: FastAPI Middleware vs. Dependency Injection

**Options:**
- **A) Middleware:** Intercept all requests/responses at HTTP layer
- **B) Dependency:** Add `audit_logger: AuditLogger = Depends(get_audit_logger)` to every route
- **C) Decorator:** `@audit_event("trade.created")` on each route handler

**Chosen: A (Middleware)**

**Rationale:**
- Automatic coverage: no need to modify 50+ route handlers
- Centralized logic: single point for audit formatting, filtering, error handling
- Cannot be forgotten: new routes automatically audited
- Access to Request/Response objects (IP, user-agent, status code)

**Trade-off:** Less granular control per route, but sufficient for our needs (action can be inferred from HTTP method + path).

---

### Decision 2: Action Naming Convention

**Options:**
- **A) HTTP-based:** `POST_/api/v1/trades`, `DELETE_/api/v1/trades/123`
- **B) Resource-based:** `trade.created`, `trade.deleted`, `execution.restored`
- **C) CRUD-based:** `create.trade`, `delete.trade`, `restore.execution`

**Chosen: B (Resource-based: `<resource>.<action>`)**

**Rationale:**
- Human-readable in Grafana queries: `{action="trade.deleted"}`
- Maps to business operations, not HTTP internals
- Consistent with industry standards (AWS CloudTrail, Google Cloud Audit Logs)
- Middleware can infer action from HTTP method + path patterns

**Mapping Logic:**
```
POST /api/v1/trades          → trade.created
PUT /api/v1/trades/{id}      → trade.updated
PATCH /api/v1/trades/{id}    → trade.updated
DELETE /api/v1/trades/{id}   → trade.deleted
POST /api/v1/auth/token      → auth.login
POST /api/v1/auth/logout     → auth.logout
POST /api/v1/imports/upload  → import.started
```

---

### Decision 3: Email Hashing Algorithm

**Options:**
- **A) SHA256:** Industry standard, irreversible, 64-char hex output
- **B) bcrypt:** Designed for passwords, slower (intentional), 60-char output
- **C) Plaintext:** Simplest, but DSGVO non-compliant

**Chosen: A (SHA256)**

**Rationale:**
- DSGVO-compliant: irreversible pseudonymization
- Fast: <1ms overhead
- Consistent length: easy to index in Loki
- Correlation: same email always produces same hash (useful for tracking)

**Trade-off:** SHA256 is vulnerable to rainbow tables for known emails, but acceptable risk (audit logs are internal, not public).

---

### Decision 4: Structured Logging Format

**Options:**
- **A) Python dictLogger with JSON formatter (stdlib)
- **B) structlog library (third-party)
- **C) Custom JSON serialization

**Chosen: A (stdlib `logging` with `python-json-logger`)**

**Rationale:**
- Zero new dependencies: `python-json-logger` is already used by uvicorn
- Native Loki integration: JSON logs automatically parsed
- Familiar API: standard `logger.info(msg, extra={...})`
- Performance: minimal overhead

**Format:**
```json
{
  "timestamp": "2026-04-19T10:30:00.123456Z",
  "level": "INFO",
  "logger": "audit",
  "action": "trade.deleted",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email_hash": "5d41402abc4b2a76b9719d911017c592",
  "resource_type": "trade",
  "resource_id": 123,
  "ip_address": "192.168.1.42",
  "user_agent": "Mozilla/5.0 (X11; Linux x86_64) ...",
  "request_id": "req_abc123",
  "status_code": 204,
  "method": "DELETE",
  "path": "/api/v1/trades/123"
}
```

---

### Decision 5: Resource ID Extraction

**Problem:** How to extract `trade_id` from `/api/v1/trades/123`?

**Options:**
- **A) Path regex:** Parse URL segments
- **B) Route metadata:** Add `audit_resource` to route definition
- **C) Response body inspection:** Extract ID from JSON response

**Chosen: A (Path regex with fallback to route metadata)**

**Rationale:**
- Simple patterns cover 90% of cases: `/api/v1/{resource}/{id}`
- For complex routes (merges, bulk ops): add optional `audit_metadata` to route
- Response inspection is fragile (async response streaming)

**Example:**
```python
# Automatic extraction
DELETE /api/v1/trades/123 → resource_type="trade", resource_id=123

# Manual metadata (for complex cases)
@router.post("/api/v1/trades/merge", audit_metadata={"resource_type": "trade"})
```

---

### Decision 6: Sensitive Data Filtering

**Approach:** Middleware-level blacklist + service-layer defensive coding

**Rules:**
1. **Middleware filters request/response bodies:**
   - Never log request body (could contain passwords, notes)
   - Never log response body (could contain P&L, prices)
   - Only log metadata: method, path, status_code, resource_id

2. **Service layer explicitly marks sensitive fields:**
   - Not needed for Phase 1 (no body logging)
   - Future-proofing for Phase 2 (if body logging added)

3. **Grafana query restrictions:**
   - Audit dashboard access controlled by IAM
   - Logs contain no financial data by design

---

## Risks / Trade-offs

### Risk 1: Log Volume
**Risk:** High-traffic endpoints generate excessive logs (cost, performance)
**Mitigation:**
- Health endpoint already filtered (existing `HealthEndpointFilter`)
- GET requests only logged at DEBUG level (disabled in production)
- Loki 90-day retention (automatic cleanup)
- Monitor log volume via Grafana; add sampling if needed

### Risk 2: User Context Missing for Unauthenticated Routes
**Risk:** `/api/v1/auth/token` (login) has no `user_id` yet (JWT not issued)
**Mitigation:**
- Log `email_hash` from request body (FastAPI form data)
- On login failure: still log `email_hash` + `ip_address` for brute-force detection

### Risk 3: IP Spoofing via X-Forwarded-For
**Risk:** Users behind proxies; `request.client.host` may be proxy IP
**Mitigation:**
- Check `X-Forwarded-For` header (trusted proxy only)
- Validate proxy IP against allowlist (nginx, load balancer)
- Log both `client_ip` and `forwarded_for` if present

### Risk 4: DSGVO Right to Access
**Risk:** Users can request "all data you have about me" (includes audit logs)
**Mitigation:**
- Phase 1: Manual export (admin queries Loki by `email_hash`)
- Phase 2: API endpoint `/api/v1/users/me/audit` (future)
- Document in Privacy Policy: "Audit logs retained 90 days for security"

### Risk 5: Email Hash Collision
**Risk:** SHA256 collision (theoretically possible, practically infeasible)
**Mitigation:**
- Accept risk: collision probability < 1 in 2^128 (negligible)
- If collision suspected: compare `user_id` (UUID, unique)

### Risk 6: Synchronous Logging Overhead
**Risk:** Logging blocks request thread (latency spike)
**Mitigation:**
- Measured overhead: <1ms for JSON serialization + stdout write
- No network I/O, no database query
- Try/except wrapper: log errors to stderr, never block request

---

## Migration Plan

**Phase 1: Backend Audit Logging (Current)**
1. Implement middleware: `backend/app/core/audit_middleware.py`
2. Implement service: `backend/app/services/audit_service.py`
3. Register middleware in `backend/app/main.py`
4. Deploy to staging: monitor log volume, verify JSON format
5. Deploy to production: no database migration needed (logs only)
6. Create Grafana dashboards: import JSON from `grafana/dashboards/audit.json`

**Rollback:**
- Remove middleware registration from `main.py`
- Restart backend (no data loss, logs continue without audit events)

**Phase 2: Frontend UI Events (Future)**
- Add `/api/v1/audit/ui-event` endpoint
- Frontend tracking library (batch events every 10s)
- Backend validates user_id from JWT

**Phase 3: User-Facing Audit Access (Future, DSGVO)**
- Add `/api/v1/users/me/audit` endpoint
- Query Loki via HTTP API, filter by `user_id`
- Rate-limit: 1 request/minute (prevent abuse)
