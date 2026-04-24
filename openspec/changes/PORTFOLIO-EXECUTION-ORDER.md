# Portfolio Feature — Execution Order

Three specs form a strict dependency chain. They **must** be implemented and
merged in the order listed below. Starting Spec 2 before Spec 1 is merged, or
Spec 3 before Spec 2, will result in broken builds and unresolvable type errors
in the generated OpenAPI client.

---

## Execution Order

```
Spec 1: portfolio-core-data-model          (backend only)
    ↓   requires: nothing
    ↓   produces: Portfolio DB model, CRUD API, portfolio-scoped endpoints,
    ↓             Alembic migration, regenerated OpenAPI TS client
    ↓
Spec 2: app-state-topbar-navigation        (frontend only)
    ↓   requires: Spec 1 merged + openapi-sync run
    ↓   produces: appContextStore, portfolioStore, BentoMenu, TopBar,
    ↓             PortfolioSwitcher, UserBadge, EmptyPortfolioGate,
    ↓             Global Library context (/dashboard/library),
    ↓             Market Check-in placeholder (/dashboard/checkin)
    ↓
Spec 3: settings-hub                       (backend + frontend)
        requires: Spec 1 + Spec 2 merged
        produces: Portfolios tab (CRUD, colour chip picker, default portfolio selector),
                  Look & Feel tab (chart display defaults),
                  AccountSettings scoped to activePortfolioId,
                  default_portfolio_id in user_settings
```

---

## Dependency Table

| Spec | Depends on | Blocks |
|---|---|---|
| Spec 1 `portfolio-core-data-model` | — | Spec 2, Spec 3 |
| Spec 2 `app-state-topbar-navigation` | Spec 1 | Spec 3 |
| Spec 3 `settings-hub` | Spec 1 + Spec 2 | — |

---

## What each spec needs from its predecessor

### Spec 2 needs from Spec 1

- `GET /api/v1/portfolios` endpoint live and returning `PortfolioRead[]`
- Generated TS client function `listPortfoliosApiV1PortfoliosGet` available
  (run `openapi-sync` skill after Spec 1 is merged)
- `PortfolioRead` TypeScript type available for `usePortfolios` hook typing

### Spec 3 needs from Spec 1

- Portfolio CRUD API (`POST/PATCH/DELETE /api/v1/portfolios`) for the Settings UI
- `has_trades` field on `PortfolioRead` (to disable `base_currency` input)

### Spec 3 needs from Spec 2

- `useActivePortfolio()` hook importable from `@/hooks/useActivePortfolio`
- `activePortfolioId` available in `AccountSettings` component
- UserBadge → Settings link renders correctly (TopBar must exist)
- `/dashboard/settings?tab=portfolios` reachable as target for EmptyPortfolioGate CTA

---

## Verification Gates (before starting each spec)

### Before starting Spec 2

```bash
# 1. Spec 1 merged and deployed
curl http://localhost:8000/api/v1/portfolios \
  -H "Authorization: Bearer <token>"
# Expected: HTTP 200 with JSON array

# 2. OpenAPI client regenerated
grep -r "listPortfoliosApiV1PortfoliosGet" frontend/lib/api/
# Expected: at least one match
```

### Before starting Spec 3

```bash
# 1. Spec 1 verification (same as above)

# 2. Spec 2 verification — useActivePortfolio hook exists
ls frontend/hooks/useActivePortfolio.ts
# Expected: file exists

# 3. Zustand store exists
ls frontend/stores/portfolioStore.ts frontend/stores/appContextStore.ts
# Expected: both files exist

# 4. TopBar is rendered on /dashboard
# Open browser → /dashboard → TopBar with BentoMenu visible
```

---

## Playwright Test Files by Spec

Tests are spec-first — they are written and committed with each spec, but will
fail until the implementation is complete. This is intentional.

| Spec | Test file(s) | Status |
|---|---|---|
| Spec 1 | backend pytest (in `backend/tests/`) | Written in tasks |
| Spec 2 | `frontend/tests/specs/topbar-navigation.spec.ts` (TC-060–TC-098) | Written ✓ |
| Spec 2 | `frontend/tests/specs/portfolio-context.spec.ts` (TC-100–TC-121) | Written ✓ |
| Spec 3 | `frontend/tests/specs/portfolio-settings.spec.ts` (TC-130–TC-170) | Written ✓ |

### Tests that will break when Spec 2 is implemented

`frontend/tests/specs/navigation.spec.ts` — migration comments added directly
in the file. The following tests must be updated or deleted after Spec 2 ships:

| Test | Reason | Replacement |
|---|---|---|
| TC-040 | Remove Playbooks/Tags/Sign Out assertions | Update in place |
| TC-042 | `/dashboard/playbooks` no longer resolves directly | Delete → TC-093 |
| TC-043 | `/dashboard/tags` no longer resolves directly | Delete → TC-094 |
| TC-047 | "Sign Out" removed from sidebar | Delete → TC-098 |
| TC-048 | Same | Delete → TC-098 |

---

## Rollback Strategy

Each spec is independently reversible:

- **Spec 1 rollback**: `alembic downgrade -1` drops portfolios table and nulls
  `accounts.portfolio_id`. Frontend remains unaffected (Spec 2 not yet merged).
- **Spec 2 rollback**: Pure frontend revert. No DB changes. No data loss.
- **Spec 3 rollback**: Frontend revert; backend schema additions to
  `UserSettingsRead/Update` are additive and harmless if left in place
  (unread fields are ignored by the frontend).
