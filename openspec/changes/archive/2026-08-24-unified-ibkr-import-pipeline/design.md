## Context

### The incident

A deployment already containing the `protected-trade-rebuild-isolation` change ran a single IBKR account sync. That sync created three trades carrying the FIFO aggregator's sentinel `entry_price = 0.001` and **zero** linked executions. Two of them shadowed contracts held by a metadata-protected option combo; the third shadowed an unprotected combo. They were the only leg-less trades in the affected database.

Critically, the protected combo itself was **untouched**: its `updated_at` still predated the sync, `closed_at` and `pnl` were intact, and all four legs remained linked with `user_modified=true`. The isolation logic is correct. It was simply never invoked.

### Why it was never invoked

`POST /api/v1/portfolios/{id}/imports/flex` (`api/v1/imports.py:592-647`) and `BrokerService._sync_ibkr` (`broker_service.py:689-699`) both call `FlexImportService.import_flex` (`flex_import_service.py:98`), which is a second import implementation independent of `ImportService`:

| | `ImportService.import_trades` | `FlexImportService.import_flex` |
|---|---|---|
| Parser entry | `parse_raw()` (raw pipeline) | `parse()` — legacy (line 141) |
| `BrokerRawTransaction` | created | **none** |
| `LogicalExecution` | created and linked | **none** |
| Persistence | trades + executions + backfill | `trade_repo.create()` only (line 183) |
| `ProtectedExecutionSnapshot` | resolved and threaded | **absent** |
| `protected_contracts` → aggregator | passed (`import_service.py:517`) | **not passed** |
| Protection key | anchor execution (UUID) | `(broker_conid, opened_at)` (line 161) |

Two consequences follow directly:

- **Leg-less trades** are not a bug in the sense of a faulty branch; the Flex path never creates executions at all. Every trade it produces is leg-less by construction.
- **Sentinel orphan lots** are created because `protected_contracts` is never passed, so the suppression guards at `aggregator.py:683` and `aggregator.py:815` cannot fire.

### Why both dedup guards miss

`manually_edited_keys` matches `(broker_conid, opened_at)`. A sentinel lot's key is derived from the *closing* execution's contract and timestamp, whereas the protected combo's key uses its *opening* timestamp, weeks earlier. Different keys, no skip. This is precisely the brittleness that `protected-trade-rebuild-isolation` D9 replaced with anchor identity — in the Flex path it survives unchanged.

`find_duplicate(symbol, opened_at)` misses for a structural reason: orphan sentinel lots receive a **synthetic** timestamp. When the reconstructed close is not strictly after the open, the aggregator sets `closed_at = opened_at + 1 second` (`aggregator.py:696-697`). Such timestamps never collide with a real trade, so sentinels pass the duplicate guard on **every** sync, indefinitely.

This also explains why the Flex path looked healthy for so long: real trades are almost always rejected as duplicates, so the only rows that reliably get through are exactly the pathological ones.

### The target pattern already exists

`BrokerService._sync_schwab` (`broker_service.py:605-614`) fetches transactions from the Schwab API, wraps them in the same JSON envelope the file upload uses, and calls `ImportService.import_trades()`. Schwab therefore inherits every protection automatically and is **not affected** by this defect — verified by inspection of the sync path.

IBKR is the sole outlier, and the conversion is mechanical: the Flex API returns the same Flex Query XML users upload manually, and `get_parser(BrokerType.IBKR)` (`utils/parsers/factory.py:49`) resolves to the same `IBKRXMLParser` that `FlexImportService` instantiates directly. No payload translation is required.

## Goals / Non-Goals

**Goals:**

- Eliminate the second ingestion implementation so a protection, invariant, or bug fix applied once applies everywhere.
- Make IBKR sync produce raw transactions and linked executions, identical to a file upload of the same report.
- Record the architectural rule so the class of defect cannot recur through a future third path.
- Confirm and lock in that Schwab already satisfies the rule.

**Non-Goals:**

- Do NOT clean up the three phantom production rows here. They carry no executions, so removal is a pure `DELETE`, but it touches production and belongs in its own change with its own verification.
- Do NOT remove or alter `IBKRXMLParser.parse()`. It remains the legacy fallback inside `ImportService` for parsers without `parse_raw()`.
- Do NOT change the Flex API request/poll protocol, credential resolution, or error mapping.
- Do NOT retroactively repair historic leg-less trades created by the old Flex path. A re-sync materialises their executions through raw-pipeline idempotency; a forced backfill is a separate decision.

## Decisions

### D1. Reduce `FlexImportService` to an API client rather than adding protections to it

**Choice**: Strip parsing, aggregation, deduplication, and persistence from `FlexImportService`. It keeps credential handling and the Flex request/poll workflow (`_fetch_flex_xml`, `_send_request`, `_poll_report`) and returns XML bytes. Callers hand those bytes to `ImportService.import_trades(broker=BrokerType.IBKR)`.

**Alternatives considered**:
- *Port the protection snapshot, orphan-lot suppression, and anchor identity into `FlexImportService`.* Rejected. It fixes the three observed symptoms and leaves the cause — two implementations of the same responsibility, only one of which is maintained — fully intact. The Flex path would still lack the raw-transaction layer, execution creation, split-aware linking, combo building, and the zero-insert guard, and would diverge again at the next change. This defect is itself the second occurrence of that pattern.
- *Delete `FlexImportService` and inline the HTTP calls into `BrokerService`.* Rejected. The Flex request/poll workflow, rate-limit handling, and error mapping are genuinely IBKR-specific and worth isolating. The problem is not that the class exists; it is what it does after fetching.

**Rationale**: `_sync_schwab` already demonstrates the correct division of labour — broker-specific fetching in a client, everything downstream in the shared service. This aligns IBKR with a proven in-repo pattern rather than inventing one.

### D2. No payload translation between the Flex API and the file-upload path

**Choice**: Pass the fetched XML through unchanged, with `filename=f"flex_query_{query_id}.xml"`.

**Rationale**: The Flex Web Service returns the same document users download and upload. `IBKRXMLParser.parse_raw()` already consumes it on the upload path. Introducing a translation layer would create a third representation to keep in sync — the exact failure mode being removed.

### D3. Raw-pipeline `source_id` idempotency replaces the Flex-local dedup

**Choice**: Remove `find_duplicate(symbol, opened_at)` and `manually_edited_keys` from the Flex path and rely on the raw pipeline's `source_id` uniqueness (`uix_le_source_id`) plus the zero-insert guard.

**Alternatives considered**:
- *Keep the Flex dedup as an extra safety net.* Rejected. It is strictly weaker — keyed on a tuple that collides across scale-ins and misses synthetic timestamps entirely — and a redundant guard with different semantics is how the two paths drifted apart in the first place.

**Rationale**: `source_id` is the IBKR trade ID, globally unique per user and stable across reports. It is the strongest available key, and it is the one the upload path already trusts.

### D4. Rename `import_file` to `import_trades`

**Choice**: Rename `ImportService.import_trades()` to `ImportService.import_trades()`. Keep the `filename` parameter and the `ImportResult.filename` response field, updating only their descriptions to state that they carry a source label which is synthetic for non-file paths (e.g. `flex_query_{query_id}.xml`, `schwab_transactions_sync.json`).

**Alternatives considered**:
- *Keep `import_file`.* Rejected. Once the method is the mandatory terminus for scheduled syncs and API pulls, "file" describes only one of three callers. A name that contradicts the architecture rule invites exactly the reasoning that produced this defect — "this isn't a file import, so this method doesn't apply to me".
- *Also rename `filename` to `source_name`, including the response field.* Rejected. `ImportResult.filename` is part of the public API contract; renaming it breaks existing clients for a cosmetic gain. The parameter is genuinely a provenance label and remains meaningful; only its documentation needs to acknowledge synthetic values.
- *Introduce `import_trades` as a new method and keep `import_file` as a deprecated alias.* Rejected. There are ten call sites in `app/`, all internal. A clean rename is cheaper than maintaining two names, and an alias would let new code keep using the misleading one.

**Rationale**: The rule and the API surface must agree. Naming is the cheapest available enforcement mechanism.

### D5. Record the rule in `AGENTS.md`, not only in the spec

**Choice**: Add an explicit architecture rule to `AGENTS.md`: every broker ingestion path — file upload, scheduled sync, API pull — MUST terminate in `ImportService.import_trades()`; a broker client may fetch a remote payload but MUST NOT parse, aggregate, deduplicate, or persist; no ingestion path may create a `Trade` directly.

**Rationale**: `AGENTS.md` is the file every agent is instructed to read before writing code; a capability spec is consulted only when someone already knows it is relevant. The failure mode here was not disagreeing with the rule — it was not knowing the second path existed. The rule has to live where it will be read unprompted.

### D6. Schwab is verified, not modified

**Choice**: No Schwab code changes. Add a regression test asserting `_sync_schwab` delegates to `ImportService.import_trades`.

**Rationale**: Schwab already satisfies the target architecture. The risk is not that it is wrong today but that a future change quietly reintroduces a bespoke path. A cheap assertion converts an implicit property into an enforced one.

## Risks / Trade-offs

- **[Risk] Historic trades created by the old Flex path remain leg-less until re-synced.** → Mitigation: raw-pipeline idempotency keys on `source_id`, so a re-sync inserts the missing raw rows and materialises executions without duplicating trades. Out of scope here; flagged for the repair change.
- **[Risk] The first sync after this change inserts many raw rows at once and triggers a full projection rebuild.** → Mitigation: identical to a first-time file upload of the same report, a supported and tested path. Protected trades are isolated from that rebuild by the existing change.
- **[Risk] Removing the Flex dedup could admit duplicates if `source_id` derivation differs between the Flex report and an uploaded file.** → Mitigation: both paths use the same parser on the same document, so derivation is identical by construction. Covered by the test asserting file upload and sync of the same report produce identical results.
- **[Risk] `ImportResult` from the Flex endpoint changes shape (previously-empty fields become populated).** → Mitigation: purely additive population of existing optional fields; no field is removed or retyped.
- **[Risk] Sentinel orphan lots can still be created for genuinely unprotected contracts** (the third phantom trade in the incident shadowed a combo that was not `is_manually_edited`). → Accepted and unchanged: orphan lots are a deliberate feature for transferred-in positions. What this change fixes is that they are now created *with* linked executions through the raw pipeline, instead of as leg-less phantoms. Whether unprotected combos should also resist re-slicing is the deferred combo-builder question from `protected-trade-rebuild-isolation`.
- **[Trade-off] `FlexImportService` shrinks to a thin client and its current tests largely become obsolete.** → Accepted; the behaviour they covered moves to `ImportService`, which already has far stronger coverage.

## Migration Plan

1. **Backend deploy** — `FlexImportService` reduced to a client; `/imports/flex` and `_sync_ibkr` delegate to `ImportService.import_trades()`.
2. **First IBKR sync after deploy** — inserts the raw transactions for the covered period and materialises the corresponding executions. Expect a non-trivial `raw_transactions_created` count and a full projection rebuild on that first run; protected trades are isolated from it.
3. **Verification** — confirm no new `entry_price = 0.001` trade lacks executions, and that protected trades' `updated_at` and leg links are unchanged by the sync.
4. **Phantom-row cleanup** — separate change against production.
5. **Rollback** — revert the backend. The old Flex path returns, along with the defect; no data written by the new path needs undoing, since raw transactions and executions are additive and idempotent.

## Open Questions

- Should the three phantom production rows be deleted, or kept until a re-sync confirms the new path reproduces the corresponding positions correctly? Leaning toward deleting them in the follow-up change, since they carry no executions and no user metadata.
- Should historic leg-less trades from the old Flex path be backfilled proactively, or left to be corrected by the next natural sync? Depends on how far back the Flex sync was actually used in production — worth measuring before deciding.
- Should an automated guard (test or lint rule) assert that no service outside `ImportService` calls `TradeRepository.create`? It would enforce D4 mechanically rather than by convention. Attractive, but it needs an allowlist for legitimate manual-creation paths (`TradeService.create_trade`, `partial_close_trade`), so it is proposed rather than assumed.
