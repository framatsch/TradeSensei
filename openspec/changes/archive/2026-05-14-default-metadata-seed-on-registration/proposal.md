## Why

New users experience a "cold start" where the platform lacks baseline metadata (tags, playbooks, and annotation metrics), reducing immediate analytical value and slowing onboarding. Seeding a curated set of industry-standard taxonomies and annotation definitions at account creation ensures users can immediately record trades and check-ins with meaningful defaults.

## What Changes

- Add a post-registration seeding service triggered when a new account is created.
- Seed default Taxonomies (Tags) for Check-ins, Trades, and Playbooks with specified hex colors and Lucide-compatible icon identifiers.
- Seed default Annotation Definitions (Metrics) for Check-ins and Trades with typed schemas (int, bool, string_enum) and UI metadata (scale, icon).
- Ensure idempotent behavior: check-before-insert to avoid duplicates if the hook fires multiple times.
- Expose the seeded metadata through existing creation forms (New Trade, New Check-in) without requiring user configuration.

## Capabilities

### New Capabilities
- `metadata-seeding`: Automatic creation of default taxonomies and annotation definitions for new users. This includes seeding payload schemas and UI metadata.

### Modified Capabilities
-(none) — this change introduces new behavior and does not change existing spec-level requirements.

## Impact

- Backend: New service function and registration hook integration (backend/app/services/user_service.py or similar). Database repositories for tags and annotation definitions will be invoked during account creation.
- Database: New rows in taxonomy and annotation tables linked to `user_id`; migrations not required if schema already supports user-scoped metadata.
- API/Frontend: Creation forms must render newly-seeded metadata immediately (no API changes expected; ensures seeded records are returned by existing list endpoints).
- Testing: Add unit/integration tests for idempotency and visibility in creation forms.
