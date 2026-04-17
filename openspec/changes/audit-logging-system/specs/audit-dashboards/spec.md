## ADDED Requirements

### Requirement: Dashboard visualizes logins by user

The Grafana dashboard SHALL display a time-series chart of login events (`auth.login`) grouped by `user_id`. The chart SHALL show successful logins over time with configurable time ranges (last 1h, 24h, 7d, 30d).

#### Scenario: Admin views login activity over 24 hours
- **WHEN** admin opens "Audit Dashboard" and selects "Last 24 hours"
- **THEN** dashboard displays line chart with login count per hour, grouped by user

#### Scenario: Filter logins by specific user
- **WHEN** admin applies filter `user_id=<specific-uuid>`
- **THEN** dashboard shows only login events for that user

---

### Requirement: Dashboard visualizes failed login attempts

The Grafana dashboard SHALL display a time-series chart of failed authentication events (`auth.failed`) grouped by `ip_address`. The chart SHALL highlight IPs with multiple failures to detect brute-force attempts.

#### Scenario: Security team detects brute-force attack
- **WHEN** security team views "Failed Logins" panel
- **THEN** dashboard shows IPs with >5 failed attempts in red (alert threshold)

#### Scenario: Filter failed logins by time range
- **WHEN** admin selects "Last 1 hour" time range
- **THEN** dashboard shows only failed login attempts from the last hour

---

### Requirement: Dashboard visualizes actions by action type

The Grafana dashboard SHALL display a bar chart of audit events grouped by `action` (e.g., `trade.created`, `trade.deleted`, `account.updated`). The chart SHALL show action counts over the selected time range.

#### Scenario: Admin views most common actions
- **WHEN** admin opens "Actions by Type" panel
- **THEN** dashboard displays bar chart with actions sorted by count (descending)

#### Scenario: Identify unusual delete activity
- **WHEN** admin filters to `action=*.deleted` pattern
- **THEN** dashboard shows all delete actions across resources (trades, accounts, executions)

---

### Requirement: Dashboard visualizes actions by IP address

The Grafana dashboard SHALL display a table of audit events grouped by `ip_address` with columns: IP address, action count, unique users, last seen timestamp. The table SHALL support sorting and filtering.

#### Scenario: Admin identifies suspicious IP
- **WHEN** admin opens "Actions by IP" panel
- **THEN** dashboard shows table with all IPs, sorted by action count (descending)

#### Scenario: Filter actions from specific IP
- **WHEN** admin clicks on IP `203.0.113.42` in table
- **THEN** dashboard updates all panels to show only events from that IP

---

### Requirement: Dashboard visualizes resource operations timeline

The Grafana dashboard SHALL display a timeline view of resource operations (create/update/delete) for a specific resource type (e.g., trades, accounts). The timeline SHALL show events chronologically with action type, user, and timestamp.

#### Scenario: Admin investigates trade deletion
- **WHEN** admin filters to `resource_type=trade` and `action=trade.deleted`
- **THEN** dashboard shows timeline of all trade deletions with user_id and timestamp

#### Scenario: Audit trail for specific resource
- **WHEN** admin filters to `resource_id=123`
- **THEN** dashboard shows all audit events for that resource (created, updated, deleted)

---

### Requirement: Dashboard supports search by email hash

The Grafana dashboard SHALL support filtering audit events by `email_hash` to trace all actions for a specific user (identified by email). The dashboard SHALL provide a text input field for entering the hash.

#### Scenario: Admin searches by email hash
- **WHEN** admin enters `email_hash=973dfe463ec85785f5f95af5ba3906ee` in search field
- **THEN** dashboard shows all audit events for user with that email hash

---

### Requirement: Dashboard includes import activity panel

The Grafana dashboard SHALL display a panel for import operations (`import.started`, `import.completed`, `import.failed`) with metadata showing record counts and file names. The panel SHALL highlight failed imports.

#### Scenario: Admin views recent imports
- **WHEN** admin opens "Import Activity" panel
- **THEN** dashboard shows table with import events, record counts, and success/failure status

#### Scenario: Investigate failed import
- **WHEN** admin filters to `action=import.failed`
- **THEN** dashboard shows failed imports with error metadata (if available)

---

### Requirement: Dashboard provides raw log viewer

The Grafana dashboard SHALL include a logs panel that displays raw JSON audit log entries for detailed inspection. The panel SHALL support full-text search across all log fields.

#### Scenario: Admin inspects raw audit event
- **WHEN** admin clicks on a specific audit event in a chart
- **THEN** dashboard shows raw JSON log entry in logs panel

#### Scenario: Search for specific action
- **WHEN** admin searches for `trade.merged` in logs panel
- **THEN** dashboard displays all raw log entries matching that action

---

### Requirement: Dashboard supports time range selection

The Grafana dashboard SHALL support time range selection with presets: Last 15m, Last 1h, Last 6h, Last 24h, Last 7d, Last 30d. The dashboard SHALL also support custom time range input.

#### Scenario: Admin views last 7 days of activity
- **WHEN** admin selects "Last 7 days" from time range picker
- **THEN** all dashboard panels update to show data from the last 7 days

#### Scenario: Admin sets custom time range
- **WHEN** admin selects custom range `2026-04-01 to 2026-04-15`
- **THEN** dashboard shows audit events only from that date range

---

### Requirement: Dashboard auto-refreshes data

The Grafana dashboard SHALL support auto-refresh with configurable intervals (5s, 10s, 30s, 1m, 5m). The default refresh interval SHALL be 30 seconds.

#### Scenario: Dashboard shows live audit events
- **WHEN** admin enables auto-refresh with 30-second interval
- **THEN** dashboard panels update every 30 seconds with new audit events

---

### Requirement: Dashboard requires authentication

The Grafana dashboard SHALL require authentication (Grafana user login) to view audit logs. Only users with `Admin` or `Viewer` roles SHALL have access to the audit dashboard.

#### Scenario: Unauthenticated user cannot access dashboard
- **WHEN** unauthenticated user navigates to audit dashboard URL
- **THEN** Grafana redirects to login page

#### Scenario: Admin user views audit dashboard
- **WHEN** authenticated admin user navigates to audit dashboard
- **THEN** dashboard loads with all panels visible
