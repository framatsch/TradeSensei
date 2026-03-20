## 1. Database & Models

- [ ] 1.1 Generate Alembic migration to drop the `broker_connections` table
- [ ] 1.2 Update the `Account` model in `account.py` to include a `type` Enum column (`MANUAL`, `SCHWAB`, `IBKR`) and drop `broker` column
- [ ] 1.3 Create `AccountProperty` model in `account_property.py` to store `account_id`, `key`, and encrypted `value`
- [ ] 1.4 Generate Alembic migration for `accounts` table changes and the new `account_properties` table

## 2. Backend Schemas & Encryption Utilities

- [ ] 2.1 Extract encryption logic into a reusable utility module (`utils/encryption.py` using Fernet)
- [ ] 2.2 Update Pydantic DTOs for `Account` in `schemas/account.py` (Add account type Enum)
- [ ] 2.3 Update `AccountCreate` and `AccountUpdate` schemas to accept `properties` (e.g., dictionary of credentials)
- [ ] 2.4 Update `AccountResponse` schema to include property flags (e.g., `has_api_keys: bool`) but omit plain text values

## 3. Backend Services & APIs

- [ ] 3.1 Refactor `AccountService` to handle creation and updating of `AccountProperty` records with encryption
- [ ] 3.2 Update `/api/v1/accounts` route to support new schemas and pass properties to the service
- [ ] 3.3 Refactor `BrokerService` to accept `account_id`, fetch decrypted account properties, and prepare sync
- [ ] 3.4 Update `/api/v1/broker/sync` route to use `account_id` instead of assuming a global user connection

## 4. Frontend API Client & Types

- [ ] 4.1 Run the `openapi-sync` skill to regenerate the TypeScript API client and Next.js types

## 5. Frontend Account Settings UI

- [ ] 5.1 Update the Account creation/edit forms in `/dashboard/settings` to include an "Account Type" dropdown
- [ ] 5.2 Dynamically reveal credential input fields (Schwab: App Key/Secret; IBKR: Flex Token/Query ID) based on Account Type
- [ ] 5.3 Implement form submission to securely pass properties to the updated `/api/v1/accounts` endpoints

## 6. Frontend Import UI Revamp

- [ ] 6.1 Completely rewrite `/dashboard/import/page.tsx` to require account selection first
- [ ] 6.2 Render dynamic upload or sync options based on the selected account's `type`
- [ ] 6.3 Wire up the new "Sync via API" button to call the refactored `/api/v1/broker/sync/{account_id}` endpoint