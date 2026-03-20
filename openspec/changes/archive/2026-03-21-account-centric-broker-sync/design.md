## Context

Currently, the `BrokerConnection` model assumes one global API connection per user. However, many brokers (like Schwab and IBKR) allow or require isolated API keys, tokens, or query IDs per trading account. The platform needs to support linking multiple trading accounts with their own secure API keys, and adapt the frontend UI to accommodate this account-centric paradigm. API credentials must be stored securely at rest.

## Goals / Non-Goals

**Goals:**
- Move API credential storage from the user level (`broker_connections` table) to the account level (`account_properties` table).
- Enforce strict typing on `Account` (MANUAL, SCHWAB, IBKR).
- Securely encrypt API credentials (Data at Rest) using `cryptography.fernet` symmetric encryption.
- Adapt backend synchronization logic to lookup and decrypt properties per `account_id`.
- Update the Next.js frontend to securely pass credentials and handle the account-first import/sync workflow.

**Non-Goals:**
- Implementing actual live synchronization with Schwab in this specific change (we only build the foundational schema and UI flow first, Schwab live sync implementation comes in a separate PR).
- OAuth 2.0 redirect flows for user-facing applications (we assume static API Keys/Secrets that the user enters manually).

## Decisions

**1. Explicit Account Types via Enum**
- *Decision:* Add a `type` column to the `Account` model using a SQLAlchemy Enum (`MANUAL`, `SCHWAB`, `IBKR`).
- *Rationale:* Instead of string parsing, an explicit enum makes frontend routing, validation, and backend syncing deterministic.

**2. Flexible `AccountProperty` Key-Value Store**
- *Decision:* Create a 1:N relationship between `Account` and a new `AccountProperty` model storing generic `key` and `value` fields.
- *Rationale:* Different brokers require different fields (Schwab: App Key, App Secret. IBKR: Token, Query ID). A flexible KV-store avoids polluting the main `accounts` table with nullable, broker-specific fields.

**3. Application-Layer Encryption for Properties**
- *Decision:* Use `cryptography.fernet` to encrypt the `value` column in `AccountProperty` before writing it to the DB.
- *Rationale:* This ensures Data at Rest encryption. The master key (`ENCRYPTION_KEY`) is stored securely in environment variables. Keys are never sent back to the frontend in plain text; the API only returns flags (e.g., `has_api_key=True`).

**4. Account-First Import Flow**
- *Decision:* The `/dashboard/import` page will force users to select an `Account` first from a `<select>` or `<ComboBox>`. Depending on the account's type, the UI will mount either a "Sync via API" module, a "CSV Upload" module, or both.
- *Rationale:* This reduces user error (importing Schwab trades into an IBKR account) and aligns the UI exactly with the underlying data model.

## Risks / Trade-offs

- **Risk: Data Migration for Existing Brokers.** Dropping `broker_connections` will lose existing IBKR tokens.
  - *Mitigation:* The platform is in early iterations. Since this is an alpha/beta stage, dropping the table entirely is acceptable, or we can instruct the user to re-enter their tokens on their respective accounts.
- **Risk: Security of `ENCRYPTION_KEY`.** If the `.env` encryption key is lost, all stored broker credentials are irrecoverable.
  - *Mitigation:* Document key management practices clearly in the production deployment guides.
- **Risk: Sync endpoint payload changes.** The `sync` endpoint changes significantly, breaking current frontend sync calls.
  - *Mitigation:* We will rely on `openapi-sync` to strictly regenerate the frontend API client and adapt the components simultaneously.