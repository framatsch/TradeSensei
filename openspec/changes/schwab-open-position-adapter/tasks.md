> Depends on `open-position-seeding` (contract) and the wrapped Schwab format from `schwab-positions-cli-import`. Do not add origin/constraint/flag/service/guard tasks here — consume them from the contract.

## 1. Parser — positions[] ingestion (Schwab adapter)

- [ ] 1.1 In `backend/app/utils/parsers/schwab_json.py`, add `positions[]` handling in `parse_raw()`: iterate each `accounts[].positions[]` entry and emit a `BrokerRawTransactionCreate` alongside the transaction-derived records.
- [ ] 1.2 Set `is_open_position = True`; build `id = "schwab:openpos:{accountNumber}:{symbol}:{longQuantity}"` (or `{shortQuantity}` for shorts).
- [ ] 1.3 Set `executed_at` from the file's top-level `dateRange.start` (UTC), so the snapshot opening leg sorts before any close in the same window. Do not set `origin`/`pnl`.
- [ ] 1.4 Map direction/price: `longQuantity>0` → LONG, price `averageLongPrice` (fallback `averagePrice`); `shortQuantity>0` → SHORT, price `averagePrice`. If both are positive, emit **two** records (one LONG, one SHORT), each with its own deterministic id.
- [ ] 1.5 Map asset type via the existing `_map_asset_class`: `EQUITY` → `multiplier=1`; `OPTION` → `multiplier=100`, `symbol=instrument.symbol` (OCC symbol unchanged). Skip any other `assetType` with a warning; empty `positions[]` is a silent no-op. Do not touch the transaction path's `multiplier=1` hardcode.
- [ ] 1.6 Seed `positions[]` only from the **account-matched** entry (the same entry `schwab-json-import`'s account-number matching selects). Do not seed positions from non-selected account entries.
- [ ] 1.7 Emit the id broker-prefixed (`schwab:openpos:...`, no user id); rely on `import_service.py` to prepend `{user_id}:` before persistence (same as transaction records).

## 2. Unit tests — parser

- [ ] 2.1 A `positions[]` entry with `longQuantity` → correct `BrokerRawTransactionCreate` (symbol, LONG, quantity, price, `executed_at=dateRange.start`, `is_open_position=True`, id format).
- [ ] 2.2 Deterministic id: parsing the same entry twice yields the same id.
- [ ] 2.3 Short holding (`shortQuantity`) → SHORT record.
- [ ] 2.4 EQUITY → `multiplier=1`; OPTION → `multiplier=100` with OCC symbol preserved and option id built from the OCC symbol.
- [ ] 2.5 Non-equity/non-option `assetType` → skipped with warning; empty `positions[]` → no records, no warning.
- [ ] 2.6 `executed_at` ordering: a fixture where the close transaction's time is after `dateRange.start` → the snapshot leg sorts before the close.

## 3. Integration tests — full Schwab cycle (via contract)

- [ ] 3.1 Wrapped file with `positions[]` + `transactions` → each position becomes an open-lot `Trade` (no `closed_at`), transactions aggregate as before.
- [ ] 3.2 Re-import the same file → no duplicate raw/logical/trade records (deterministic-id idempotency).
- [ ] 3.3 Approximate close: `positions[]` seeds a lot, a later import's `TRADE` transaction for the same instrument `(symbol, conid=None, asset_class)` in the opposite direction closes it → one round-trip `Trade` with `opened_at` (≈`dateRange.start`) and `closed_at`.
- [ ] 3.4 Snapshot-replace (quantity change): seed a lot from `positions[]`, re-import with a changed quantity (or omitting it) → the stale `open_position` leg is replaced; one lot reflecting the latest snapshot.
- [ ] 3.5 Supersede: snapshot open + later real `imported` opening execution for the same instrument → contract rule drops the snapshot leg → one open lot.
- [ ] 3.6 Account scope: multi-account file → only the account-matched entry's `positions[]` are seeded.

## 4. Documentation

- [ ] 4.1 Update `docs/schwab-positions-tool.md` (or the Schwab import doc) to note that `positions[]` is now seeded as open lots, with the approximate-`opened_at` caveat.

## 5. Verification

- [ ] 5.1 `lint-check` (ruff + `mypy --strict`) — zero new errors.
- [ ] 5.2 `unit-test` (pytest) for Schwab positions parser + integration cycle — green (contract change must be present).
