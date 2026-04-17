# Audit Logging Validation Guide — Staging Checklist

This guide provides step-by-step validation instructions for the audit logging
system after deployment to staging. Each section includes precise commands and
expected outcomes.

---

## Prerequisites

- Backend deployed to staging with `AuditMiddleware` registered in `app/main.py`
- Access to Grafana (Explore view and Dashboards)
- Test user credentials for staging environment
- API client (curl, Postman, or frontend)

---

## Task 6.14: Test Dashboard with Sample Logs

**Goal**: Verify Grafana dashboard displays audit events correctly.

### Step 1: Generate test traffic

Run these API calls against staging to generate audit events:

```bash
# 1. Login (generates auth.login)
curl -X POST https://staging.tradesensei.com/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=testpass123"

# 2. Create account (generates account.created)
curl -X POST https://staging.tradesensei.com/api/v1/accounts \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Account", "broker": "IBKR", "account_number": "U12345"}'

# 3. Update account (generates account.updated)
curl -X PUT https://staging.tradesensei.com/api/v1/accounts/ACCOUNT_ID \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Account"}'

# 4. Delete account (generates account.deleted)
curl -X DELETE https://staging.tradesensei.com/api/v1/accounts/ACCOUNT_ID \
  -H "Authorization: Bearer YOUR_TOKEN"

# 5. Trigger validation error (generates error.validation)
curl -X POST https://staging.tradesensei.com/api/v1/accounts \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": ""}'  # Empty name should fail validation

# 6. Trigger not found (generates error.not_found)
curl -X GET https://staging.tradesensei.com/api/v1/accounts/99999999 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Step 2: Import Grafana dashboard

1. Open Grafana → Dashboards → New → Import
2. Upload `grafana/dashboards/audit.json` from repo
3. Select Loki datasource when prompted
4. Click "Import"

### Step 3: Verify panels display data

Check each panel in the dashboard:

- **Logins by User**: Should show auth.login events over time
- **Failed Login Attempts**: Test with wrong password first
- **Actions by Type**: Should show account.created, account.updated, account.deleted
- **Actions by IP Address**: Should show your IP with action count
- **Resource Operations Timeline**: Should show create/update/delete events
- **Error Rate**: Should show error.validation and error.not_found spikes
- **Top Errors**: Should list ValidationError, HTTPException
- **Raw Log Viewer**: Click an event → verify JSON structure

### Step 4: Test dashboard filters

- Select your `user_id` from dropdown → all panels filter to your actions
- Select `action=auth.login` → only login events shown
- Select your `ip_address` → only your requests shown
- Clear filters → all data visible again

**Expected outcome**: All 9 panels populate with data, filters work correctly.

**Mark complete**: Task 6.14 ✅

---

## Task 7.1: Deploy to Staging

**Goal**: Ensure backend with audit middleware is deployed and running.

### Commands

```bash
# Verify deployment status (adjust for your K8s/Docker setup)
kubectl get pods -n staging | grep backend

# Check backend logs for middleware registration
kubectl logs -n staging deployment/backend --tail=50 | grep -i audit

# Or if using Docker Compose:
docker-compose -f docker-compose.staging.yml ps
docker-compose -f docker-compose.staging.yml logs backend | grep -i audit
```

**Expected outcome**: Backend pod/container is running, logs show no errors.

**Mark complete**: Task 7.1 ✅

---

## Task 7.2: Verify Structured JSON Logs in Loki

**Goal**: Confirm audit events reach Loki with correct JSON structure.

### Step 1: Query Loki via Grafana Explore

1. Open Grafana → Explore
2. Select Loki datasource
3. Run query:

```logql
{logger="audit"}
```

4. Switch to "Table" view
5. Expand a log entry and verify JSON structure

### Step 2: Check required fields

Every audit event must have:

```json
{
  "timestamp": "2026-04-19T14:23:45.123456Z",
  "action": "account.created",
  "user_id": 123,
  "email_hash": "973dfe463ec85785f5f95af5ba3906eedb2d931c24e69824a89ea65dba4e813b",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "resource_type": "account",
  "resource_id": "456",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "method": "POST",
  "path": "/api/v1/accounts",
  "status_code": 201
}
```

### Step 3: Verify action naming

Run these queries and check action format:

```logql
{logger="audit"} | json | action =~ ".*\\..*"
```

All actions should match `<resource>.<verb>` pattern:
- `auth.login`
- `account.created`, `account.updated`, `account.deleted`
- `trade.created`, `trade.updated`, `trade.deleted`
- `error.validation`, `error.not_found`, `error.internal`

**Expected outcome**: All logs are valid JSON with required fields, action naming follows conventions.

**Mark complete**: Task 7.2 ✅

---

## Task 7.3: Verify Log Format Matches Spec

**Goal**: Confirm all field types and formats match `docs/audit-logging.md` spec.

### Validation checklist

Run this query to inspect field types:

```logql
{logger="audit"} | json
```

For each field, verify:

| Field | Type | Format | Example |
|-------|------|--------|---------|
| `timestamp` | string | ISO 8601 with μs | `2026-04-19T14:23:45.123456Z` |
| `action` | string | `<resource>.<verb>` | `account.created` |
| `user_id` | integer | — | `123` |
| `email_hash` | string | SHA256 hex (64 chars) | `973dfe...` |
| `request_id` | string | UUID v4 | `550e8400-e29b-41d4-a716-446655440000` |
| `resource_type` | string | singular noun | `account`, `trade` |
| `resource_id` | string | ID from URL | `456` |
| `ip_address` | string | IPv4 or IPv6 | `192.168.1.100` |
| `user_agent` | string | HTTP header | `Mozilla/5.0...` |
| `method` | string | HTTP verb | `POST`, `PUT`, `DELETE` |
| `path` | string | URL path | `/api/v1/accounts` |
| `status_code` | integer | HTTP status | `200`, `201`, `404`, `500` |

**Expected outcome**: All fields match spec types and formats.

**Mark complete**: Task 7.3 ✅

---

## Task 7.4: Verify Email Hashing Works Correctly

**Goal**: Confirm identical emails produce identical hashes.

### Test procedure

1. Login with `test@example.com`:

```bash
curl -X POST https://staging.tradesensei.com/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=testpass123"
```

2. Query Loki for the first hash:

```logql
{logger="audit"} | json | action="auth.login" | line_format "{{.email_hash}}"
```

Copy the hash (e.g., `973dfe463ec85785f5f95af5ba3906eedb2d931c24e69824a89ea65dba4e813b`).

3. Login again with same email (wait 1 minute to avoid rate limiting).

4. Query again and verify hash is identical.

5. Login with `TEST@EXAMPLE.COM` (uppercase) and verify hash is still identical (email normalization test).

**Expected outcome**: Same email (case-insensitive) produces identical SHA256 hash.

**Mark complete**: Task 7.4 ✅

---

## Task 7.5: Verify Sensitive Data is NOT Logged

**Goal**: Confirm no P&L, prices, passwords, tokens, or strategy details appear in logs.

### Prohibited fields (must never appear)

Run these queries — **all should return 0 results**:

```logql
{logger="audit"} |= "pnl"
{logger="audit"} |= "commission"
{logger="audit"} |= "price"
{logger="audit"} |= "quantity"
{logger="audit"} |= "password"
{logger="audit"} |= "token"
{logger="audit"} |= "playbook"
{logger="audit"} |= "tag_name"
{logger="audit"} |= "notes"
{logger="audit"} |= "strategy"
```

### Additional spot checks

1. Create a trade with P&L data via API
2. Query Loki for the `trade.created` event
3. Expand the JSON and manually verify:
   - No `pnl`, `commission`, `price`, `quantity` fields
   - Only safe fields like `user_id`, `resource_id`, `action`

**Expected outcome**: Zero matches for all sensitive field queries.

**Mark complete**: Task 7.5 ✅

---

## Task 7.6: Verify 90-Day Retention Policy in Loki

**Goal**: Confirm Loki is configured to retain audit logs for 90 days.

### Verification steps

1. Check Loki configuration (adjust path for your setup):

```bash
# Kubernetes ConfigMap
kubectl get configmap loki-config -n monitoring -o yaml | grep -A5 retention

# Docker Compose
cat loki/loki-config.yaml | grep -A5 retention
```

2. Look for `retention_period: 2160h` (90 days) or similar.

3. Query oldest audit log:

```logql
{logger="audit"} | json | __timestamp__ > 0
```

4. Check timestamp of oldest entry (should not exceed 90 days from now).

**Expected outcome**: Loki config shows 90-day retention, oldest logs are <90 days old.

**Mark complete**: Task 7.6 ✅

---

## Task 7.7: Monitor Log Volume and Performance Impact

**Goal**: Verify audit logging adds <1ms latency and doesn't overwhelm log storage.

### Step 1: Measure request latency

Run a baseline request without auth (no audit logging):

```bash
time curl https://staging.tradesensei.com/health
```

Run an authenticated request (triggers audit):

```bash
time curl -X POST https://staging.tradesensei.com/api/v1/accounts \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "broker": "IBKR", "account_number": "U12345"}'
```

Compare response times — audit overhead should be negligible (<1ms).

### Step 2: Check log volume in Loki

Query log rate:

```logql
rate({logger="audit"}[5m])
```

Expected: <10 logs/sec for normal usage (adjust for your traffic).

### Step 3: Monitor Loki disk usage

```bash
# Kubernetes
kubectl exec -n monitoring loki-0 -- df -h /loki

# Docker
docker exec loki df -h /loki
```

**Expected outcome**: Latency <1ms overhead, log rate within acceptable range, disk usage stable.

**Mark complete**: Task 7.7 ✅

---

## Task 7.8: Import Grafana Dashboard

**Goal**: Make audit dashboard available in Grafana.

### Step 1: Import dashboard

1. Open Grafana → Dashboards → New → Import
2. Click "Upload JSON file"
3. Select `grafana/dashboards/audit.json` from repo
4. Click "Load"
5. Select Loki datasource from dropdown
6. Click "Import"

### Step 2: Verify dashboard UID

Dashboard UID should be `audit-logging` (check URL after import).

### Step 3: Set as favorite (optional)

Click ★ in top bar to bookmark.

**Expected outcome**: Dashboard imported successfully, accessible at `/dashboards/audit-logging`.

**Mark complete**: Task 7.8 ✅

---

## Task 7.9: Test Dashboard Filters and Time Range

**Goal**: Verify all filters and time pickers work correctly.

### Test filters (top of dashboard)

1. **User ID filter**:
   - Select your user ID → all panels show only your actions
   - Clear → all users visible

2. **Action filter**:
   - Select `auth.login` → only login events
   - Select `account.created` → only account creations
   - Clear → all actions visible

3. **IP Address filter**:
   - Select your IP → only your requests
   - Clear → all IPs visible

4. **Email Hash filter**:
   - Select your email hash → only your logins
   - Clear → all users visible

### Test time range picker (top right)

Select each preset and verify data updates:
- Last 15 minutes
- Last 1 hour
- Last 6 hours
- Last 24 hours
- Last 7 days
- Last 30 days

### Test auto-refresh

- Enable auto-refresh (30s default)
- Generate a new action (e.g., login)
- Wait 30 seconds → verify new event appears

**Expected outcome**: All filters work, time range updates panels, auto-refresh adds new events.

**Mark complete**: Task 7.9 ✅

---

## Task 7.10: Deploy to Production

**Goal**: Promote audit logging to production after successful staging validation.

### Prerequisites

Confirm all tasks 7.1–7.9 are complete with no issues.

### Deployment steps

1. Merge audit logging feature branch to `main`
2. Tag release (e.g., `v1.7.0-audit-logging`)
3. Deploy to production via CI/CD or manual deployment
4. Repeat spot checks from staging:
   - Query `{logger="audit"}` in production Loki
   - Verify JSON structure
   - Check sensitive data exclusion
   - Import dashboard (if not already present)
   - Test filters

### Post-deployment monitoring

- Monitor error rate in Grafana for 24 hours
- Check Loki disk usage trend
- Review audit logs for unexpected patterns

**Expected outcome**: Production deployment successful, audit logs flowing correctly, no performance degradation.

**Mark complete**: Task 7.10 ✅

---

## Summary

| Task | Description | Status |
|------|-------------|--------|
| 6.14 | Test dashboard with sample logs | ⬜ Pending |
| 7.1 | Deploy to staging | ⬜ Pending |
| 7.2 | Verify structured logs in Loki | ⬜ Pending |
| 7.3 | Verify log format matches spec | ⬜ Pending |
| 7.4 | Verify email hashing | ⬜ Pending |
| 7.5 | Verify sensitive data exclusion | ⬜ Pending |
| 7.6 | Verify 90-day retention | ⬜ Pending |
| 7.7 | Monitor log volume and latency | ⬜ Pending |
| 7.8 | Import Grafana dashboard | ⬜ Pending |
| 7.9 | Test dashboard filters | ⬜ Pending |
| 7.10 | Deploy to production | ⬜ Pending |

Check off each task as completed. If any task fails, document the issue and
resolve before proceeding to production deployment.
