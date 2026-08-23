## Why

The IBKR Flex sync runs through `FlexImportService.import_flex` — a second, parallel import implementation that has never received any of the protection work applied to `ImportService`. It calls the legacy `IBKRXMLParser.parse()` instead of `parse_raw()`, so it creates **no** `BrokerRawTransaction` and **no** `LogicalExecution` rows at all: it only calls `TradeRepository.create()`. Every trade it produces is leg-less by construction.

A confirmed incident followed the `protected-trade-rebuild-isolation` deploy. A single IBKR account sync created three phantom trades carrying the sentinel `entry_price = 0.001` and zero executions — two shadowing contracts held by a metadata-protected option combo, one shadowing an unprotected combo. They were the only leg-less trades in the affected database. The protected combo itself was left completely intact (`updated_at` predating the sync, all four legs linked and `user_modified=true`), which proves the isolation work in `ImportService` is correct — it is simply bypassed.

Neither guard in the Flex path can catch this. `manually_edited_keys` matches on the brittle `(broker_conid, opened_at)` key that this project already replaced with anchor-execution identity, and orphan sentinel lots receive a synthetic timestamp (`closed_at = opened_at + 1s`, `aggregator.py:696-697`) that by definition never collides with a real trade, so `find_duplicate(symbol, opened_at)` never fires either. Sentinel orphans therefore slip through on every single sync.

The correct pattern already exists in this codebase: `BrokerService._sync_schwab` (`broker_service.py:605-614`) fetches transactions from the Schwab API, wraps them in the same payload the file upload uses, and delegates to `ImportService.import_trades()`. Schwab consequently inherits every protection automatically and is **not** affected by this defect. IBKR is the sole outlier. This change removes that asymmetry.

## What Changes

- **Rename**: `ImportService.import_file()` becomes `ImportService.import_trades()`. Once the method is the mandatory terminus for scheduled syncs and API pulls, "file" describes only one of three callers, and a name that contradicts the architecture rule invites the reasoning that caused this defect. The `filename` parameter and the `ImportResult.filename` response field are **kept** — the response field is part of the public API contract — with their descriptions updated to state the value is a source label that is synthetic for non-file paths.
- **BREAKING (internal architecture)**: `FlexImportService` is reduced to a pure IBKR Flex Web Service API client. It fetches the Flex Query XML and returns it; it no longer parses, aggregates, deduplicates, or persists anything.
- Both IBKR entry points — `POST /api/v1/portfolios/{id}/imports/flex` and `BrokerService._sync_ibkr` — delegate the fetched XML bytes to `ImportService.import_trades(broker=BrokerType.IBKR)`, mirroring `_sync_schwab` exactly. The Flex API returns the same Flex Query XML format that users upload manually, and `get_parser(BrokerType.IBKR)` already resolves to the same `IBKRXMLParser`, so no payload translation is required.
- As a direct consequence the IBKR sync gains, with no additional code: the raw-transaction layer, real `LogicalExecution` rows with trade links, protected-trade isolation, orphan-lot suppression for protected contracts, anchor-based trade identity, the zero-insert guard, split-aware execution linking, combo position building, and protection reporting in `ImportResult`.
- The removed Flex-local deduplication (`find_duplicate` on `(symbol, opened_at)`) and protection skip (`manually_edited_keys` on `(broker_conid, opened_at)`) are replaced by the raw pipeline's `source_id`-keyed idempotency, which is strictly stronger.
- `ImportResult` returned from the Flex endpoint gains the fields the file-upload path already reports; `BrokerSyncResult` for IBKR gains the protection counters `_sync_schwab` already returns.
- An architecture rule is recorded in `AGENTS.md`: every broker ingestion path — file upload, scheduled sync, and API pull — MUST terminate in `ImportService.import_trades()`. Remote fetching belongs in a broker-specific client; parsing and persistence never do.
- **Schwab verified as unaffected**: `_sync_schwab` already follows the target pattern. No Schwab code changes; a regression test is added to keep it that way.

Explicitly out of scope (deliberate): cleaning up the three phantom production rows (a separate repair, since it must be planned against production); changing `IBKRXMLParser.parse()` itself, which stays for the legacy fallback inside `ImportService`; and any change to the Flex API request/poll protocol.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `trade-import`: Require every broker ingestion path to terminate in the single raw-pipeline import service, so file upload and API sync produce identical persistence results. Require IBKR Flex imports to create raw transactions and logical executions rather than bare trades.
- `account-centric-broker-sync`: Require the IBKR account sync to delegate to the unified import service, gaining protected-trade isolation and protection reporting; make explicit that the Schwab sync already satisfies this and must continue to.
- `execution-overwrite-protection`: Require the protections to hold for **every** ingestion entry point, not only the file-upload path — closing the bypass that allowed protected trades to be shadowed by phantom sentinel trades.

## Impact

- **Backend services**: `flex_import_service.py` reduced to an API client (parsing, aggregation, dedup, and persistence removed); `broker_service.py` `_sync_ibkr` rewritten to mirror `_sync_schwab`; `import_service.py` unchanged.
- **Backend API**: `POST /portfolios/{id}/imports/flex` keeps its request contract; its `ImportResult` response gains the fields the file-upload path already populates (raw-transaction counts, protection counters). Additive for clients.
- **Behavioural change**: IBKR sync now creates `BrokerRawTransaction` and `LogicalExecution` rows. Historic trades created by the old Flex path remain leg-less until re-imported; the raw pipeline is idempotent per `source_id`, so a re-sync materialises the missing executions.
- **Database**: no schema change.
- **Documentation**: `AGENTS.md` gains the ingestion-path architecture rule; `docs/api-usage.md` notes that Flex import and file upload are behaviourally identical.
- **Tests**: Flex endpoint delegates to `ImportService`; IBKR sync creates executions and links them; a protected trade survives an IBKR sync unchanged; no sentinel orphan is created for a protected contract via the sync path; `FlexImportService` performs no persistence; Schwab sync regression test asserting continued `ImportService` delegation.
- **Risk**: the Flex path loses its independent dedup logic. Mitigated because raw-pipeline idempotency keys on `source_id` (the IBKR trade ID), which is strictly more precise than `(symbol, opened_at)`.
