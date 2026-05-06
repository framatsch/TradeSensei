## 1. Backend Updates

- [x] 1.1 Remove `currency` field from `AccountCreate` and `AccountUpdate` schemas in `backend/app/schemas/account.py`.
- [x] 1.2 Update `AccountService.create` in `backend/app/services/account_service.py` to fetch the parent `Portfolio` and assign its `base_currency` to the new account's `currency` field before saving.
- [x] 1.3 Fix backend tests (e.g. in `tests/api/` or `tests/services/`) that previously supplied `currency` in the account creation payload.
- [x] 1.4 Regenerate OpenAPI client using the `openapi-sync` skill to update frontend types.

## 2. Frontend Updates

- [x] 2.1 Remove the `currency` selection field from the Account Creation form (e.g., `frontend/src/components/account/...`).
- [x] 2.2 Remove or disable the `currency` selection field from the Account Edit form.
- [x] 2.3 Verify TypeScript compilation and fix any frontend tests broken by the type change in the API client.
