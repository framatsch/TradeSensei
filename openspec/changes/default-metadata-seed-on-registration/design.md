## Context

Current state: New accounts are created with an empty set of user-scoped metadata (tags, playbooks, annotation definitions). UX and analytics value are reduced until users manually create metadata.

Constraints: Must be backend-service-only change with no schema migrations. All timestamps and IDs follow existing project conventions (UTC, UUID-style ids). Use Decimal for monetary fields if any (none here). Follow audit logging policy for manual audit events if operation is complex.

Stakeholders: Backend engineers, frontend engineers (forms), QA, product.

## Goals / Non-Goals

**Goals:**
- Implement an idempotent post-registration seeding service that inserts default taxonomies (tags) and annotation definitions for the 2x2 matrix.
- Ensure seeded records are user-scoped and immediately visible via existing list endpoints used by forms.

**Non-Goals:**
- Global/shared organization-wide seeds (out of scope).
- Large data migrations or changes to table schemas.

## Decisions

1) Service Placement
- Implement seeding in backend/app/services/seed_service.py as a single function `seed_default_metadata_for_user(user_id: UUID, *, session: AsyncSession)` and call it from the registration flow in `backend/app/services/user_service.py` immediately after the user row is created and committed.

Rationale: Keeps seeding logic isolated and testable. Service layer aligns with project architecture.

2) Idempotency Strategy
- Before inserting each record type, query the repository for any existing record with the same `user_id` and a stable `seed_key` (e.g., `seed:market-phases`). If present, skip creation for that seed_key.
- Use a small `seed_key` string stored in metadata column (or in `external_id` if schema already has it). If no schema field exists, enforce uniqueness using a compound unique index on (user_id, name, scope) where appropriate and handle unique-constraint exceptions gracefully.

Rationale: Explicit `seed_key` makes future seed updates/deltas easier. Query-before-insert avoids race-born duplicate attempts; fallback to catching unique-violation handles concurrent hooks.

3) Data Shape and Mapping
- Taxonomy (Tag) insert payload fields: name, scope, color_hex, icon_identifier, seed_key, user_id, created_by (system), created_at.
- Annotation Definition payload: name, type, scope, scale (when applicable), options (for enums), icon_identifier, seed_key, user_id, created_by, created_at.

4) Audit & Logging
- Emit a manual audit event `metadata.seeding` with safe metadata: user_id and seed_keys applied. DO NOT include seeded values that contain sensitive info.

5) Error Handling
- Failures in seeding should not block user registration. If seeding fails, log error and emit audit event `metadata.seeding.failed` with safe metadata. Provide a background retry via simple queued job (TODO in tasks).

## Risks / Trade-offs

[Race on concurrent hooks] → Mitigation: Query-before-insert + handle unique-violation exceptions
[Silent failures hide UX issues] → Mitigation: Emit audit event and log; add a lightweight health-check for seeder in later iteration

## Migration Plan

1. Implement service and unit tests.
2. Wire into registration flow behind a feature flag (optional) or run instantly in staging for QA.
3. Deploy backend; run integration tests validating seeded metadata visibility in forms.
4. If rollback required, remove hook call; seeded records remain (idempotent re-run safe).

## Open Questions

- Do we want seeds configurable per environment or customizable per tenant? (Recommend not for MVP.)

## Mockup

Below is a concise mockup showing how seeded tags appear in New Trade and New Check-in forms.

New Check-in Form (top fields):

- Mood Level [1-10 slider]   (seeded metric: Mood Level)
- Focus [1-10 slider]        (seeded metric: Focus)
- Market Phase [select chips]  (seeded tags: Bullish, Bearish, Sideways, Volatile)

New Trade Form (top fields):

- Setup Quality [A+ | B | C]  (seeded enum metric)
- Rule Followed [checkbox]    (seeded bool metric)
- Execution Tags [chips]      (seeded tags: FOMO, Discipline, High Conviction)

The UI should present seeded tags and metrics as first-class options identical to user-created ones.
