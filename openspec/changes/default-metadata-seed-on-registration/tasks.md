## 1. Extend Taxonomy Seed Defaults

- [ ] 1.1 Open `backend/app/repositories/taxonomy_repository.py` and locate `seed_defaults(user_id)`. Replace the existing 3-tag seed with the full 11-tag set (Market Phases × 4, Execution Quality × 3, Strategy Categories × 4) with correct `scope`, `color_hex`, and `icon_identifier` values per spec.
- [ ] 1.2 Verify `icon_identifier` strings are Lucide-compatible (e.g. `"trending-up"`, `"shield"`, `"rocket"`) — no library prefix needed unless the frontend strips/adds it.
- [ ] 1.3 Confirm the existing `UniqueViolation` / `IntegrityError` handling in `seed_defaults` catches duplicate inserts gracefully (log + skip); add it if missing.

## 2. Extend Annotation Definition Seed Defaults

- [ ] 2.1 Open `backend/app/repositories/annotation_definition_repository.py` and locate `seed_defaults(user_id)`. Replace or extend the existing 2-metric seed with the full 4-metric set: Mood Level (int, checkins, 1-10), Focus (int, checkins, 1-10), Rule Followed (bool, trades), Setup Quality (string_enum, trades, options: ["A+","B","C"]).
- [ ] 2.2 Ensure `scale_labels` JSONB is set correctly: `{"min":1,"max":10}` for int types, `{}` for bool, `{"options":["A+","B","C"]}` for string_enum.
- [ ] 2.3 Assign `icon_identifier` values per spec: `"smile"`, `"target"`, `"check-square"`, `"award"`.
- [ ] 2.4 Confirm idempotency handling mirrors step 1.3.

## 3. Wire Non-Blocking Error Handling

- [ ] 3.1 In `backend/app/services/auth_service.py`, wrap the `seed_defaults` calls for taxonomies and annotation definitions in a `try/except Exception` block. On failure: call `logger.error()` with `user_id` and emit audit event `metadata.seeding.failed` (safe metadata: `user_id` only). Do NOT re-raise — account creation must succeed.
- [ ] 3.2 Confirm `external_oauth_login` also calls the updated seed functions (it already calls the old ones — verify the same path is covered).

## 4. Unit Tests

- [ ] 4.1 Add a test in `backend/tests/` (or extend existing taxonomy tests) asserting that after `seed_defaults(user_id)` the session contains all 11 expected taxonomy records with correct `name`, `scope`, `color_hex`, `icon_identifier`.
- [ ] 4.2 Add a test asserting that after `seed_defaults(user_id)` for annotation definitions the session contains all 4 records with correct `type`, `scope`, `scale_labels`, `icon_identifier`.
- [ ] 4.3 Add an idempotency test: call `seed_defaults` twice for the same `user_id` and assert no duplicates are created and no exception is raised.
- [ ] 4.4 Add a test for the non-blocking failure path in `AuthService.register`: mock the taxonomy repository to raise an unexpected exception, assert user is still returned and the error is logged.

## 5. Integration / Acceptance Verification

- [ ] 5.1 Register a fresh test user via `POST /auth/register` in a test environment and call `GET /taxonomies` — assert all 11 seeded tags are returned.
- [ ] 5.2 Call `GET /annotation-definitions` for the new user — assert all 4 seeded metrics are returned.
- [ ] 5.3 Register the same user credentials a second time (or force-call the seeder twice) — assert the second call returns no duplicate records.
