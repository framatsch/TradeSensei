## Why

The Trade Sensei platform currently has minimal logging of user actions and API operations. For security, compliance (DSGVO), debugging, and forensic analysis, we need a comprehensive audit trail that tracks who did what, when, and from where. This enables security incident response, regulatory compliance for EU users, and visibility into system usage via Grafana/Loki dashboards.

## What Changes

- Add FastAPI middleware to automatically log all REST API write operations (POST/PUT/PATCH/DELETE)
- Add structured JSON logging for authentication events (login, logout, failed attempts, token refresh)
- Add comprehensive exception and error logging (unhandled exceptions, validation errors, HTTP 4xx/5xx responses)
- Implement audit event service with standardized format including user_id, IP address, user-agent, resource IDs, and actions
- Configure logging to output structured JSON to stdout for Loki ingestion
- Create Grafana dashboards for audit visualization (logins, actions by user, failed attempts, actions by IP, errors)
- Add DSGVO-compliant handling: email hashing (SHA256), 90-day retention policy in Loki
- Exclude sensitive data from logs: no P&L, commissions, prices, strategy notes, or passwords/tokens
- Support debug-level logging for read operations (GET) when `LOG_LEVEL=DEBUG`
- Update AGENTS.md with audit logging policy and error handling requirements for backend-engineer and frontend-engineer agents

## Capabilities

### New Capabilities

- `audit-middleware`: FastAPI middleware that intercepts all authenticated requests and logs actions with user context, IP address, resource details, timestamps, exceptions, and HTTP errors
- `audit-event-service`: Service layer for creating structured audit events with standardized format, email hashing, and sensitive data filtering
- `audit-dashboards`: Grafana dashboard configurations for visualizing audit events by user, action type, IP address, and time range
- `agent-instructions`: AGENTS.md documentation section that instructs backend-engineer and frontend-engineer agents to automatically add audit logging for new features and follow error logging standards

### Modified Capabilities

<!-- No existing capabilities are being modified - this is a new feature -->

## Impact

**Backend:**
- New middleware in `backend/app/core/audit.py`
- New service in `backend/app/services/audit_service.py`
- Updated `backend/app/main.py` to register audit middleware
- All API routes in `backend/app/api/v1/*` automatically covered by middleware

**Infrastructure:**
- Loki retention policy set to 90 days (already configured, no changes needed)
- New Grafana dashboards added to monitoring stack

**Dependencies:**
- No new Python packages required (uses stdlib `logging`, `hashlib`)
- Grafana/Loki stack already in place

**DSGVO Compliance:**
- Privacy Policy update required (mention IP logging for security purposes)
- User data access API endpoint needed for DSGVO "right to access" (future enhancement)
