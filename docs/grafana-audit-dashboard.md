# Grafana Audit Dashboard

## Overview

The audit dashboard provides visibility into authentication activity, resource
changes, and error rates. It expects audit logs in Loki labeled with
`logger="audit"`.

Dashboard definition: `grafana/dashboards/audit.json`.

## Import

1. Open Grafana.
2. Navigate to **Dashboards → Import**.
3. Upload `grafana/dashboards/audit.json`.
4. Select the Loki datasource when prompted.

## Panels

- Logins by User: counts `auth.login` events grouped by `user_id`.
- Failed Login Attempts: counts `auth.failed` grouped by `ip_address`.
- Actions by Type: distribution of audit actions.
- Actions by IP Address: activity grouped by IP.
- Resource Operations Timeline: create/update/delete trends.
- Import Activity: events matching `import.*` actions.
- Raw Log Viewer: stream of audit events.
- Error Rate: counts of `error.*` actions.
- Top Errors: top error actions by count.

## Filters

Dashboard variables allow filtering by `user_id`, `action`, `ip_address`,
and `email_hash`.

## Troubleshooting

- Ensure Loki has `logger="audit"` labels for audit entries.
- Verify logs are structured JSON with `action` and `status_code` fields.
