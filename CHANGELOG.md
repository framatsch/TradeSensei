# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- [backend] Fixed OIDC silent token refresh failure by setting the refresh token cookie path to `/` instead of `/api/v1/auth`, allowing the frontend proxy to correctly send the cookie.
- [frontend] Explicitly added `credentials: "same-origin"` to the fetch call in the API interceptor to ensure the refresh token cookie is always sent.

## [1.16.2] - 2026-09-09

### Fixed
- [frontend] Fixed trade detail "Correct Trade" menu being cut off by its parent container by applying `overflow-visible`.
- [frontend] Enhanced `InlineNumberField` discoverability for Stop Loss and Take Profit with a dashed underline and persistent pencil icon so it's clearly identifiable as editable.

## [1.16.1] - 2026-09-08

### Fixed
- [frontend] Disabled automatic background fetching (`refetchOnWindowFocus`) on tab switch and implemented a silent token refresh in the API interceptor to prevent unexpected 401 logouts and data loss in inactive tabs.

## [1.16.0] - 2026-09-07

### Added
- [frontend] Import dialog now automatically pre-selects the account if the user's portfolio only contains a single active account.

### Changed
- [frontend] Unified import dialog (Schwab/IBKR) date selector redesigned: replaced toggle buttons and progress bar with a compact, stateful dropdown for date presets ("Last 30 days", "YTD", etc.) alongside an always-visible date picker.
- [backend] Expanded `FlexFromDatePreset` in `AccountSettings` to natively support dynamic date presets (`"7d"`, `"30d"`, `"90d"`, `"180d"`, `"360d"`, `"mtd"`) alongside `"ytd"` and `"custom"`. These presets are now saved dynamically when a user updates their account settings.

## [1.15.0] - 2026-09-07

### Fixed
- [backend] Broker re-import now closes previously stuck metadata-protected open positions in place, preserving notes/tags/journal while recomputing aggregate trade fields; this correction can change historical performance metrics and equity-curve history on the next qualifying import.
- [backend] Added a Schwab zero-insert self-heal trigger: if an open metadata-protected trade has an absorbable unlinked execution on the same contract, import now forces a projection rebuild instead of returning a no-op, so pre-fix stuck positions close on the next sync. Unresolved manual-standin contracts are excluded to keep no-op imports fast.

## [1.14.0] - 2026-08-24

### Changed
- [backend] Unified IBKR ingestion paths: `/imports/flex` and IBKR file upload now both delegate to `ImportService.import_trades()`, and `FlexImportService` now acts as a pure Flex API fetch client.
- [backend] Renamed `ImportService.import_file()` to `ImportService.import_trades()` across backend services, routes, and tests while preserving the public `ImportResult.filename` field.

### Added
- [docs] Added broker ingestion architecture rule in `AGENTS.md` requiring every broker ingestion path (upload/sync/API pull) to terminate in `ImportService.import_trades()`, with `_sync_schwab` as reference implementation.
- [docs] Documented that IBKR Flex API import and IBKR file upload are behaviorally identical and both create raw transactions and linked executions.
- [tests] Added comprehensive integration coverage for split-file COMBO lifecycle and execution linking.
- [tests] Added integration coverage proving the IBKR sync path creates linked executions, is idempotent, matches file-upload results, preserves protected trades, and skips the projection rebuild on a no-op second sync.

### Fixed
- [backend] Removed an in-process retry loop around IBKR Flex `SendRequest` calls. Retrying a "please try again shortly" response within seconds was found to itself trigger IBKR's stricter "Too many failed attempts" account-level lockout; transient Flex errors and rate limits now surface immediately as HTTP 503 (`/broker/sync/{account_id}` and `/imports/flex`) instead of being silently retried.
- [backend] `POST /imports/flex` now handles parse/account-mismatch/unexpected errors from the shared import pipeline the same way `POST /imports/upload` does (400/422 instead of an unhandled 500).

## [1.13.0] - 2026-08-15

### Added
- [backend] Added protected-trade rebuild isolation signal `has_unlinked_executions` to `TradeRead` and exposed optional `has_unlinked_executions=true` filtering on `GET /api/v1/portfolios/{portfolio_id}/trades`.
- [frontend] Added trade-detail notice and trade-list filter toggle for protected trades with unlinked executions, including URL/saved-view serialization support.

### Fixed
- [backend] Added regression coverage for protected-trade rebuild isolation behavior (unlinked execution reporting, protected execution backfill exclusion, orphan suppression on protected contracts, and merge-protection invariants).
- [docs] Documented `has_unlinked_executions` semantics and trade-list filter usage in `docs/api-usage.md`.

## [1.12.0] - 2026-08-14

### Changed
- [frontend] Unified visual style across Trading Log and Checkin components by enforcing `.solid-card` as the standard container format.
- [frontend] Aligned `CheckinSidebar` layout, widths, headers, and hover states to perfectly match `TradingLogSidebar`.
- [docs] Updated UI `styleguide.md` to deprecate `.radiant-card` and establish `.solid-card` as the mandatory card component format.

## [1.11.0] - 2026-08-14

### Added
- [frontend] Added clickable sorting functionality to `ExecutionLegsTable` column headers.

### Fixed
- [frontend] Fixed `ExecutionRow` context menu cutoff at the bottom of the viewport by using Radix UI DropdownMenu for robust collision detection and positioning.

## [1.10.0] - 2026-08-11

### Added
- [frontend] Replaced legacy corporate action warning banner with a clean, tooltip-enabled split icon in the Trade Detail header.

### Fixed
- [backend] Fixed trade aggregation to persist split-adjusted `quantity` and `entry_price` to the database after corporate actions, and ensured manual execution splits correctly apply corporate action ratios when re-aggregating the trade.

## [1.9.1] - 2026-08-09

### Added
- [tools] New `ibkr_cli.py` CLI tool for fetching trades via IBKR Flex Query API with `--since` support and robust retry logic.

## [1.9.0] - 2026-08-09

### Added
- [docs] Finalized and archived OpenSpec `execution-metadata-protection-hardening` with updated specifications for user-metadata overwrite protection during broker imports.

### Fixed
- [backend] Fixed execution symbol-change spec to match implemented behavior — the execution's own trade re-aggregates under its new symbol, and a same-account old-symbol sweep runs as a safety net, not a two-chain split.
- [backend] Added regression guard ensuring broker sync's `FlexImportService` does not surface successful creates as false warnings.
- [backend] Added audit middleware `skip_audit` unit test to guard against double-audit regressions on `DELETE /executions/{id}`.
- [backend] Removed tautological broker service test and fixed `AsyncMock` → `MagicMock` for synchronous audit method.
- [backend] Fixed PEP 257 docstring violations in execution and flex-import test suites.

## [1.8.3] - 2026-07-29

### Fixed
- [frontend] Fixed the Chart Component Refresh Icon to match the spec by using the exact title "Refresh" instead of "Force Refresh Data".
- [backend] Fixed critical data loss bug where broker sync (Schwab/IBKR) wiped out trade metadata. Implemented stable `UPSERT` matching logic in `ImportService` using `broker_conid` and `opened_at` to preserve user metadata during sync.
- [backend] Fixed Schwab OAuth refresh token persistence by ensuring the database session is committed after token rotation.
- [tests] Fixed E2E test `chart-cache-refresh.spec.ts` navigation issues.
- [backend] Fixed CI lint checks by disabling `respect-gitignore` for Ruff to align remote and local environments.

## [1.8.2] - 2026-07-29

### Changed
- [backend] `DELETE /api/v1/market-data/cache` now performs a global unconditional wipe of all cached prices across all users, rather than filtering by the current user's traded symbols.
- [frontend] Updated the "Clear Cache" button in General Settings with a "Danger" warning to clarify that it clears market data for all users platform-wide.

## [1.8.1] - 2026-07-28

### Added
- [frontend] Added interactive display options dropdown to `TradeChart`, allowing users to independently toggle Entry/Exit Price Lines, Execution Marker Arrows, and Volume histogram.
- [frontend] Added volume histogram rendering to `TradeChart`, utilizing volume data provided by the Market Data Hub.
- [frontend] Added native `lightweight-charts` crosshair implementation (CrosshairMode.Normal) mimicking TradingView style with dashed lines and axis labels.

### Fixed
- [frontend] Removed aggressive CSS cursor override that was breaking axis resizing functionality (`ew-resize` and `ns-resize`) in lightweight-charts.
- [frontend] Enhanced silent fallback detection in `TradeChart` to accurately detect missing intraday data (e.g. LSEG daily fallbacks) and trigger the "No Market Data Available" empty state appropriately.

## [1.8.0] - 2026-07-27

### Added
- [backend] Added `POST /api/v1/portfolios/{portfolio_id}/executions/{execution_id}/link-broker-transaction` endpoint to link manual execution legs (`origin='manual'`) to raw broker transactions (`BrokerRawTransaction`), setting `source_id` and suppressing re-imports.
- [backend] Added derived `has_conflict` boolean field to `TradeRead` schema, automatically computed during trade aggregation when an unlinked manual leg duplicates an imported leg.
- [frontend] Added manual execution linking UI with broker raw transaction picker dialog, trade detail conflict warning banner, and visual conflict leg highlighting in execution tables.

### Changed
- [backend] Extended execution overwrite protection so that patching split or merged executions sets `user_modified=true`, ensuring user edits are preserved during broker re-imports unless explicitly overwritten.
- [backend] Hard-deleting a linked manual execution automatically releases its underlying `BrokerRawTransaction` (`suppressed=false`) in the same database transaction.
- [frontend] Updated import overwrite setting label to "Overwrite user modifications" with updated help text covering edited trades and execution legs.

### Fixed
- [backend] Fixed unintended loss of trade metadata (journals, tags, playbooks, quick notes) during broker syncs. Modifying trade metadata now explicitly marks the parent trade as `is_manually_edited=True`, preserving user inputs from being wiped during re-imports while allowing metrics updates.

## [1.7.0] - 2026-07-24

### Added
- [frontend] Added "Quick Notes" workflow with inline table inputs and timeline view. Quick notes capture point-in-time observations (e.g. emotions, order updates) during the trade.
- [frontend] Added "Import Quick Notes" button to the Qualitative Metadata panel to append timeline notes directly to the final trade journal.
- [backend] Added `emotion` field to `TradeNote` model and schemas.
- [backend] Added MCP get-by-ID read tools: `get_trade` (with embedded quick notes), `get_checkin`, `get_taxonomy`, and `get_annotation_definition`.
- [backend] Added MCP quick-note write tools `add_trade_note`, `update_trade_note`, `delete_trade_note`, and a journal edit tool `update_trade_journal` (replace/append) for single-trade granularity.
- [backend] Added MCP binary attachment tools `get_trade_attachments` and `get_playbook_attachments`, returning image bytes as base64 MCP image content blocks (default) or presigned URLs, bounded by a per-call attachment limit and a per-image inline size cap.
- [backend] Added MCP tool `link_trade_playbook` to set or clear a trade's linked playbook.
- [backend] Added `StorageService.download_file_by_storage_ref()` and extended the MCP JSON-RPC dispatcher to support non-text (image) content blocks in `tools/call` results.
- [docs] Documented the new MCP tools and example prompts in `docs/mcp-client-integration.md`.

### Changed
- [frontend] Refactored `QualitativeMetadataPanel` to be always editable, removing the explicit "Edit" button for a more seamless journaling experience.
- [frontend] Updated text placeholders across the trade detail view to clearly distinguish between point-in-time Quick Notes and the final post-trade Journal.

## [1.6.1] - 2026-07-19

### Fixed
- [tools] Fixed `schwab_cli.py` to support running from any directory by checking the current working directory for `.env` and outputting files to `Path.cwd()` by default.

## [1.6.0] - 2026-07-19

### Added
- [backend] Added strongly-typed option fields (`strike`, `expiry`, `option_type`) to `LogicalExecution` and `BrokerRawTransaction`, derived from the OCC symbol at import and backfilled for existing legs.
- [frontend] Option Leg Contract Details — Strike/Type/Expiry columns in the execution legs table and human-readable contract labels in the summary card, for both single-option and COMBO trades.
- [backend] Added robust OAuth connect flows for Charles Schwab (paste mode and callback mode) with refresh token rotation and 7-day expiry handling.
- [frontend] Replaced static Schwab credentials input with an OAuth flow in settings, supporting both seamless redirect callbacks and fallback paste methods.
- [backend] Added `DELETE /api/v1/portfolios/{portfolio_id}/accounts/{account_id}/trades` clear-trades endpoint with destructive acknowledgement, ownership-safe 404 behavior, and deletion counts.
- [frontend] Added account Danger Zone clear-trades modal/action with typed confirmation and success toast.
- [frontend] Added broker-capability-driven import date-range control used across IBKR and Schwab.

### Changed
- [frontend] Unified import sync date-range UX while preserving broker-specific request shape (`from_date` for IBKR, `days` for Schwab).
- [docs] Added `docs/api-usage.md` and documented the new clear-trades endpoint and unified import date-range behavior.

### Fixed
- [security] Fixed IDOR vulnerabilities by replacing implicit ownership propagation with explicit authorization guards across Checkin, Taxonomy, Playbook, Portfolio, and Account services.
- [frontend] Restored UI consistency with strict Tailwind design tokens, resolving dark mode regressions, alignment issues, and text-overflow edge cases.
- [test] Fixed Playwright E2E test flakiness caused by `global-teardown` state-leaks, strict mode selector violations, and stale locators.
- [test] Fixed Python unit test failures in `test_broker_service.py` related to `AsyncMock` and asynchronous context managers.
- [backend] Combo position matching now handles the case where the user scales into the same spread via two or more separate broker orders and closes them together in one order: each opening order is matched FIFO and produces its own closed trade (with the closing legs split proportionally), instead of being incorrectly merged into a single combined position.
- [backend] Fixed unbounded trade duplication on repeated (non-cleared) re-imports whenever the account had any open combo position: the "delete all trades and rebuild" safety net was being skipped for the whole account instead of just the open combo's trades, causing fragmented/split single-instrument trades to be re-inserted as duplicates on every import.

### Removed
- [frontend] Removed the file-coupled Fresh Start affordance from `ImportForm` in favor of account-level clear-trades.
- [frontend] Removed the chart-local option overlay (strike lines, option chips, per-leg entry/exit markers, expiry line, and the "Chart layers" toggle popover) that was added alongside Option Leg Contract Details. Contract details are shown on the trade detail page only (execution legs table / summary card), not on the chart.

## [1.5.0] - 2026-07-17

### Added
- [backend] Cross-import COMBO seed/update flow: later IBKR closing-only imports now close the existing open COMBO trade (`db_trade_id`-based update) instead of creating duplicates
- [backend] `open_close` field on `LogicalExecutionRead` and `BrokerRawTransactionRead` schemas — exposes the O/C indicator derived by the broker parser at the API level
- [test] Integration coverage for split-file COMBO lifecycle (open-only import A + close-only import B) and DB-vs-ground-truth P&L anchor on `combo_positions.xml`

### Changed
- [frontend] Regenerated OpenAPI client (`frontend/lib/api/`) to include `LogicalExecutionRead.open_close` in generated types
- [docs] Clarified import behavior glossary entry: IBKR multi-leg option orders are grouped as COMBO trades with leg-level Open/Close markers while preserving aggregate P&L
- [backend] **BREAKING** Consolidated playbook content to a single markdown `description` field, removed legacy `content_markdown` storage, and removed MCP `rules` input from strategy playbook create/update
- [backend] Added MCP `sync_playbook_metadata` and extended `update_strategy_playbook` with optional additive `taxonomy_ids`; `get/list_strategy_playbooks` now include assigned taxonomies
- [frontend] Playbook editor save/load now uses `description` only; removed `content_markdown` usage in playbook payload types

### Fixed
- [backend] Replaced deprecated FastAPI `HTTP_*` status constants with modern `*_CONTENT` / `*_TOO_LARGE` variants across validation and upload error responses

## [1.4.0] - 2026-07-15

### Added
- [tools] New `schwab_cli.py` CLI tool for downloading Schwab positions and transactions
- [backend] Account-number matching for Schwab imports — auto-selects single account, aborts on mismatch
- [backend] On-the-fly split-adjustment of execution prices and quantities via `CorporateAction` records
- [frontend] Archive/unarchive actions and "Show Archived" toggle in Tags and Metrics library pages
- [backend] Cascading hard-deletion (`?force=true`) for taxonomy and annotation definitions

### Changed
- [backend] Execution APIs now return split-adjusted `price`/`quantity` plus raw `raw_price`/`raw_quantity` fields for execution marker consumers
- [frontend] Trade chart execution marker labels now prefer adjusted values and fall back to raw values when adjusted data is unavailable
- [backend] Introduce `STORAGE_PROXY_URL` as the primary presign host setting while keeping `STORAGE_PUBLIC_URL` as a backward-compatible alias
- [infra] Update local/prod compose defaults to prefer `STORAGE_PROXY_URL`; frontend `NEXT_PUBLIC_STORAGE_ACCESS_MODE` now defaults to `proxy` everywhere
- [backend] Schwab JSON importer now accepts only the wrapped `{accounts: [...]}` format; legacy top-level array format removed
- [backend] Schwab online sync reimplemented via Transactions API + shared `SchwabJSONParser` pipeline; removed `SchwabOrderNormalizer`

### Fixed
- [frontend] Remove storage proxy/upload fallback workarounds and restore deterministic proxy behavior for uploads and image reads
- [docs] Update object storage docs with `STORAGE_PROXY_URL` semantics and `STORAGE_PUBLIC_URL` deprecation guidance
- [backend] Schwab JSON parser now derives trade direction from `positionEffect` + `amount` sign for real Schwab equity exports

## [1.3.6] - 2026-06-24

### Fixed
- [frontend] Use dynamic viewport height (`h-[100dvh]`) for mobile browsers to prevent bottom UI cutoff
- [api] Fix 422 Unprocessable Content error on `/api/v1/checkins/filters` by reordering FastAPI router inclusions
- [frontend] Fix accidental form submission in CheckinLightbox zoom controls and add touch-pan support for zoomed images on mobile Safari
- [frontend] Fix root page blank screen and Safari Private Mode `localStorage` hydration crashes
- [frontend] Fix root page hardcoded redirect to `/dashboard`, now correctly redirects to the user's configured `home_route`

## [1.3.5] - 2026-06-24

### Added
- [frontend] Render assigned tags (colored pill badges) instead of description in the playbook library overview table
- [backend] Embed `taxonomies` in `PlaybookRead` response — list endpoint now returns tags in a single query via `selectinload` (no N+1)

### Fixed
- [frontend] Fix image previews not loading on mobile devices — presigned S3/SeaweedFS URLs are now tunnelled through `/api/storage-proxy` when the storage host is not reachable by the browser directly (localhost, `*.cluster.local`, RFC-1918 IPs)
- [frontend] Fix file uploads failing after storage port was closed — `PUT` requests to presigned upload URLs now go through the same proxy
- [frontend] External storage URLs (real S3, CloudFront) bypass the proxy and go directly to the browser — no performance overhead for cloud deployments
- [infra] Remove `STORAGE_ENDPOINT_URL` / `STORAGE_PUBLIC_URL` from frontend container env — proxy routing is now self-contained with no configuration required
- [infra] Remove SeaweedFS port 8333 host binding — storage is internal-only; all access goes through Next.js proxy

## [1.3.4] - 2026-06-23

### Fixed
- [backend] Resolve all ruff lint errors across the codebase
- [backend] Apply ruff format to 22 files for consistent code style
- [frontend] Add missing `taxonomies` field to `Playbook` TypeScript interface
- [tests] Skip flaky performance smoke test in CI to improve pipeline reliability

## [1.3.3] - 2026-06-22

### Fixed
- [infra] Route all file uploads and image downloads through Next.js `/api/storage-proxy` — SeaweedFS port 8333 no longer needs to be publicly exposed
- [infra] Fix `ECONNREFUSED 127.0.0.1:8333` in Docker: set `STORAGE_ENDPOINT_URL` and `STORAGE_PUBLIC_URL` to internal `seaweedfs:8333` hostname in both backend and frontend containers
- [backend] Sanitize S3 key filenames in storage service — replace spaces and special characters with underscores to prevent `SignatureDoesNotMatch` 403 errors on presigned PUT URLs
- [frontend] Add missing `storageUploadUrl` import in `PlaybookEditorClient` that caused playbook image uploads to fail silently
- [backend] Fix `MissingGreenlet` crash on `PATCH /playbooks/{id}` by eager-loading `taxonomy_assignments` after flush in `playbook_repository.update`
- [backend] Fix same `MissingGreenlet` risk in `playbook_repository.get_by_id` and `create` by adding `selectinload` for `taxonomy_assignments`

## [1.3.2] - 2026-06-21

### Added
- [backend] Add MCP taxonomy and annotation definition CRUD support
- [docs] Add OpenSpec proposal, design, specs, and tasks for MCP taxonomy and annotation CRUD

### Fixed
- [frontend] Fix mobile sidebar overlay layout for trades, check-ins, and playbooks
- [backend] Resolve strict mypy errors in metadata repositories and correlation scope validation

## [1.3.1] - 2026-06-07

### Fixed
- [frontend] Add `color-scheme: light/dark` and native `<option>` element dark mode theming to globals.css

## [1.3.0] - 2026-06-06

### Added
- [backend] Checkin metadata: annotation filtering, taxonomies, MCP tools, and archive support
- [frontend] Annotation filtering and checkin metadata UI with taxonomy browser
- [frontend] Checkin filters and saved views with persisted filter state
- [frontend] Metrics/tags library UX improvements with usage indicators

### Changed
- [backend] Migrate AnnotationDefinition scope to comma-separated tokens
- [backend] Replace 'both' scope with explicit comma-separated scope tokens
- [frontend] Align CheckinFilterBar with Trade/Workspace paradigm
- [frontend] Format checkin dates and remove media filter

### Fixed
- [backend] IDOR vulnerability on assignment count endpoints
- [backend] normalize_scope empty guard and scope filter validation
- [backend] Update test suite for comma-separated scope format
- [frontend] Blocker, a11y, design system, and quality fixes (Round 2)

### Removed
- [backend] Committed development artifacts

## [1.2.5] - 2026-06-03

### Added
- [frontend] Lightbox image viewer now supports drag-to-pan and mouse wheel zoom navigation
- [docs] OpenSpec plan created for saved check-in filters
- [backend] Add `screenshot_keys` field to `DailyCheckinRead` schema to expose raw storage references alongside presigned URLs

### Fixed
- [backend] Fixed image URL validation bug during check-in updates that caused screenshot keys to become corrupted
- [frontend] Prevented page reload/navigation when saving check-in updates, showing a toast instead
- [frontend] Timeline text is now properly truncated to prevent overly long notes from breaking the layout
- [frontend] Split screenshot state into storage keys and preview URLs to prevent PATCH failures
- [frontend] Fixed URL parsing in `useScreenshots` to strip query params from presigned URLs before extracting filename
- [frontend] Replaced `TradeImageGallery` grid with compact inline thumbnails in Timeline view
- [backend] Removed dead file-upload code (`StaticFiles` mount, `upload_dir` config, `_screenshot_dir` method)

## [1.2.4] - 2026-06-02

### Changed
- [backend] Upload endpoint responses now return `{presigned_url, key}` instead of full `public_url`.
- [frontend] Updated upload hooks to store the image `key` (`{bucket}/{key}`) instead of the full URL.
- [backend] List and get API endpoints for trades, check-ins, and playbooks now generate temporary, short-lived presigned GET URLs dynamically.

### Security
- [backend] Migrated storage references to remove public hostnames; domain models now store generic `{bucket}/{key}` keys.
- [backend] Read access to images now explicitly requires authentication.

## [1.2.3] - 2026-05-31

### Added
- [frontend] News links now render prominently in Check-in Timeline and Gallery views with domain badges
- [frontend] TradingView chart links styled as distinct blue chips with icon in Check-in overviews

### Fixed
- [frontend] External links inside clickable check-in cards no longer trigger card navigation (`stopPropagation`)

### Changed
- [frontend] Market index badges in Timeline view now use primary colors and bold text for better visibility
- [frontend] Renamed "TradingView" column/placeholder to "External Link" in Check-in settings to reflect generic use

## [1.2.2] - 2026-05-31

### Fixed
- [frontend] Sidebar toggle (Cmd+B / button) now works on Trading Log and Market Check-in views — extracted shared sidebar state into Zustand store so child layouts respond to toggle
- [frontend] Checkin news links auto-prepend `https://` when no protocol is present
- [frontend] Checkin tag button active state uses primary colors instead of muted
- [backend] Replace `passlib` with direct `bcrypt` calls for password hashing — removes outdated dependency

### Changed
- [backend] Remove unused `market_phase` regex validation in DailyCheckinService (field is already validated for empty/whitespace)

## [1.2.1] - 2026-05-31

### Added
- [frontend] Taxonomy and Annotation managers synced with backend repositories (full CRUD via API)
- [frontend] Color-coded taxonomy chips with `color_hex` rendering and icon display in TaxonomySelector
- [frontend] Configurable chart interval (weekly, monthly, quarterly, yearly) in user settings with GeneralSettings UI
- [frontend] 1-week (1w) interval option in TradeChart time range selector
- [db] Seed default market indexes (SPX, NDX, DAX) for existing users via Alembic data migration

### Fixed
- [frontend] Fix undefined `isPending` variable reference in TaxonomyManager (use correct mutation pending states)
- [frontend] Fix DynamicIcon interface type conflict with LucideProps `name` prop
- [test] Fix broken `scalar_one()` query syntax in two backend tests (missing `.where()` clause)

### Changed
- [frontend] Add AGPLv3 license headers to multiple frontend components

## [1.2.0] - 2026-05-30

### Added
- [backend] Return distribution histogram endpoint `POST /analytics/return-distribution` with equal-width binning
- [backend] Status-based dashboard filter (`open`/`closed`) replacing boolean `include_open_trades` in `DashboardFilterConfig`
- [frontend] GitHub repository link and license display in AboutModal
- [frontend] Metric help tooltip for open/closed trade status filter
- [frontend] Help content for analytics and reporting page
- [test] Test suite for `showOpenTrades` hook and `TradesPageClient` open-trades toggle
- [test] User API integration tests for MCP session ownership validation

### Fixed
- [backend] MCP SSE security — reject cross-user `POST /mcp/messages` with HTTP 403 by storing `(user_id, queue)` in `_ACTIVE_STREAMS`
- [backend] `show_open_trades` default type: corrected from string `'False'` to boolean `false`
- [frontend] Race condition in `TradesPageClient`: defer `enforceClosedStatus` until settings are fully loaded to prevent incorrectly stripping `?status=open` during placeholder phase
- [frontend] Empty scatter plot rendering when analytics return no data
- [frontend] Calendar day click now correctly applies date range filters
- [frontend] Workspace filter bar migrated from `includeOpenTrades` boolean to `status` enum (`open`/`closed`/`null`)

### Removed
- [backend] Model Book entity — removed API routes, service, repository, Pydantic schemas, and ORM model
- [frontend] Model Book UI components (`ModelBookCard`, `ModelBookView`, `ModelBookFilterBar`, `StarButton`) and hooks (`useCheckinModelBook`, `useModelBookEntries`, `useTradeModelBook`)
- [db] Dropped `is_modelbook` column from `trades` and `daily_checkins` tables via Alembic migration
- [frontend] Trade status setting (`show_open_trades`) removed from FeaturesSettings — replaced by global `useShowOpenTrades` hook

## [1.1.2] - 2026-05-27

### Fixed
- [frontend] Rename `tag_ids` to `taxonomy_ids` in all filter components, hooks, and API client types to match backend naming

## [1.1.1] - 2026-05-23

### Added
- [dev] Introduce Gemini CLI commands for OCR workflow and Antigravity integration

### Changed
- [frontend] PlaybookEditorClient: add view/edit mode separation with `?edit=true` query param, delete playbook button, read-only preview mode hides edit controls, empty state indicators for images/links
- [frontend] CheckinForm: major rework of taxonomy mapping and form layout
- [frontend] QualitativeMetadataPanel: enhanced metadata display panel for trades

### Fixed
- [frontend/backend] Resolve taxonomy filtering: map `tag_ids` to `taxonomy_ids` consistently across all filter bars, forms, and queries
- [backend] DashboardFilterConfig schema now accepts `include_open_trades` parameter
- [backend] AnalyticsRepository and AttributionRepository correctly include open trades in metrics
- [frontend] `useTrades` hook correctly populates `taxonomy_ids` in API queries
- [frontend] Correlation dashboard and workspace filter bars use correct taxonomy field names
- [backend] Add `source_id` and `is_mixed_execution` columns to migration chain, drop cash transactions table

## [1.1.0] - 2026-05-18

### Added
- [core] MCP API SSE streaming with sorting support
- [mcp] Add `list_portfolios` and `list_accounts` MCP tools
- [frontend] Form improvements for playbook updates
- [mcp] License headers and cleanup

### Fixed
- [backend] IBKR FIFO P&L pipeline — 4 bug fixes with synthetic test harness
- [backend] Audit middleware request-body deadlock in tests
- [backend] Catch `httpx.ConnectTimeout` in OIDC login and callback endpoints
- [test] Fix 7 stale test failures after refactoring
- [infra] Split storage-init from compose startup to prevent CI teardown failure
- [infra] Add `workflow_dispatch` trigger to Discord notification

### Removed
- [backend] Remove cash transactions and tax/Anlage-KAP feature entirely

### Docs
- [docs] Add more MCP prompt examples
- [docs] Transition project to Dual-Licensing model (AGPLv3 + CLA)

## [1.0.0] - 2026-05-14

Initial stable release. Complete trading analytics platform with portfolio management, daily check-ins, structured metadata system, playbook strategy hub, MCP integration, and comprehensive reporting.

### Added
- [core] Portfolio core data model with full CRUD, colour chip picker, default portfolio selector
- [core] Three-pillar architecture: Portfolio Workspace, Trading Log, Market Check-in
- [core] App state management with BentoMenu context switcher and Zustand slices
- [core] Centralized taxonomy and annotation metadata system (2x2 matrix for trades/check-ins)
- [core] Playbook Strategy Hub with taxonomies, file attachments, and external links
- [core] Structured daily check-in system with market index association and mini calendar
- [core] Reporting Hub & Analytics UI with performance metrics and attribution visualization
- [core] Metadata Correlation Dashboard with scatter plots, heatmaps, and box charts
- [core] Model Book cross-entity gallery (trades + check-ins side-by-side)
- [core] MCP integration with PAT authentication and domain tools
- [core] Self-hosted object storage (SeaweedFS) for local deployments
- [core] Default metadata seed on user registration
- [core] Frontend API client migration from Axios to OpenAPI-generated hey-api SDK
- [core] Centralized help system with consistent tooltips

### Changed
- [ui] Trade Detail page redesigned with qualitative metadata panel
- [ui] New Trade Form redesigned for 2x2 metadata architecture
- [ui] Portfolio Workspace overhauled with isolated routes and performant widgets
- [ui] Settings Hub consolidated into centralized settings module
- [backend] Legacy tags/market_phase/checkin_field tables and endpoints removed
- [backend] Reporting layer decoupled from trade ledger
- [backend] Object storage and MCP server infrastructure

### Fixed
- [ui] Multiple OCR review findings across rounds 2, 3, 4/5
- [ui] TradeChart 'Up to Entry' mode cutoff
- [ui] Execution Leg Editor — full field editing and broken loading state
- [backend] Split-aware execution linking with FIFO aggregator
- [backend] Annotation input step values for int/float types
- [infra] Stabilized E2E tests with robust Playwright locators

## [0.27.1] - 2026-04-30

### Added
- [backend] Convert `if/else` assignments to ternary expressions across core services and parsers for conciseness (Ruff SIM108)

### Changed
- [backend] Increase Ruff `line-length` to 160 to reduce unnecessary multi-line wrapping in Python code

## [0.27.0] - 2026-04-30

### Added
- [frontend] Portfolios tab in Settings — full CRUD for portfolios with colour chip picker, default portfolio selector, and Danger Zone (data wipe)
- [frontend] Look & Feel settings tab — chart display defaults (`chart_candles_before`, `chart_candles_after`, `chart_show_post_exit`) stored in user settings
- [backend] Introduced the `Portfolio` entity with `id`, `name`, `base_currency`, and `color_hex`, plus user-scoped CRUD endpoints at `/api/v1/portfolios`.
- [frontend] Added `appContextStore` Zustand slice — Portfolio Workspace / Global Library / Market Check-in mode, persisted to localStorage
- [frontend] Added `portfolioStore` Zustand slice — persists `activePortfolioId` to localStorage
- [frontend] Added `TopBar` with `BentoMenu` (nine-dot context switcher), context-aware `PortfolioSwitcher` (colour chip + name), and `UserBadge`
- [frontend] Added `EmptyPortfolioGate` for first-time users with no portfolios
- [frontend] Added Global Library context at `/dashboard/library` (Playbooks, Tags)
- [frontend] Added Market Check-in placeholder at `/dashboard/checkin`

### Changed
- [frontend] Accounts & Integrations tab scoped to active portfolio (Spec 2 prerequisite)
- [backend] `UserSettingsRead` / `UserSettingsUpdate` schemas gain four new fields (3 chart display + `default_portfolio_id`)
- [backend] Scoped trades, metrics, timeseries, imports, accounts, executions, and cash-transactions under `/api/v1/portfolios/{portfolio_id}/...`; legacy unscoped endpoints now return HTTP 410.
- [frontend] All dashboard pages read `activePortfolioId` from global context; per-page `AccountFilter` state removed
- [frontend] Sidebar nav-items are context-specific; Playbooks/Tags moved to Library context
- [frontend] Sidebar cleaned of sign-out and standalone account-management links
- Note: Playbooks & Tags management moved to Global Library context (Spec 2) — no Settings tab

### Migration
- [db] Added portfolio migration that creates a default portfolio per existing user and links all existing accounts automatically.

## [0.24.0] - 2026-04-20

### Added
- [backend] Split-aware execution linking with FIFO aggregator to correctly track position costs across partial closes and splits.
- [backend] Automatic underlying symbol extraction from OCC strings for IBKR XML imports (options trades).
- [frontend] TradeChart improvements: cyan (buy) and orange (sell) markers for executions; synthetic candles to bridge data gaps in low-volume assets.
- [backend] New test modules for execution linking, FIFO aggregation, and OCC string parsing.
- [db] Migrations for `position_id` on executions, `user_rating` on trades, and optimized indexes for split-tracking.

### Fixed
- [backend] Proportional commission validation logic to allow zero commissions on free trades while maintaining strict upper bounds.
- [frontend] `ExecutionRow` column alignment and trade detail layout fixes for improved readability on mobile devices.

### Changed
- [infra] Stabilized 36 Playwright E2E tests by adding robust locators and retry logic for flaky network requests.

## [0.22.0] - 2026-04-19

### Added
- [backend] Structured audit logging middleware and audit event service with JSON output and sensitive-field filtering.
- [infra] Grafana audit dashboard definition and documentation for audit log fields and dashboard usage.

## [0.21.0] - 2026-04-18

### Added
- [backend] Email-based self-service password reset: `POST /auth/forgot-password` sends a reset link to the registered address; `POST /auth/reset-password` validates the single-use JWT and updates the password.
- [backend] SMTP configuration fields (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM`, `SMTP_TLS`) and `password_reset_enabled` computed property on `Settings`; feature is off unless all SMTP fields are present.
- [backend] `create_password_reset_token` / `consume_password_reset_token` in `security.py`: 1-hour JWT with `pwreset` claim and replay protection via the existing `used_otts` table.
- [backend] `GET /auth/config` response now includes `password_reset_enabled` flag.
- [backend] Unit tests for password-reset token functions; integration tests for `POST /auth/forgot-password`, `POST /auth/reset-password`, and `GET /auth/config`.
- [frontend] `/forgot-password` page: email form that always shows a static success message after submission to prevent user enumeration.
- [frontend] `/reset-password` page: reads `?token=` from the URL, validates new + confirm password, and redirects to `/login?reset=success` on success.
- [frontend] Login page shows "Forgot password?" link below the password field only when `password_reset_enabled` is `true`.
- [frontend] Login page shows a green success banner when arriving from `/reset-password` via `?reset=success`.

## [0.20.0] - 2026-04-18

### Added
- [backend] Email-based self-service password reset: `POST /auth/forgot-password` sends a reset link to the registered address; `POST /auth/reset-password` validates the single-use JWT and updates the password.
- [backend] SMTP configuration fields (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM`, `SMTP_TLS`) and `password_reset_enabled` computed property on `Settings`; feature is off unless all SMTP fields are present.
- [backend] `create_password_reset_token` / `consume_password_reset_token` in `security.py`: 1-hour JWT with `pwreset` claim and replay protection via the existing `used_otts` table.
- [backend] `GET /auth/config` response now includes `password_reset_enabled` flag.
- [frontend] `/forgot-password` page: email form that always shows a static success message after submission to prevent user enumeration.
- [frontend] `/reset-password` page: reads `?token=` from the URL, validates new + confirm password, and redirects to `/login?reset=success` on success.
- [frontend] Login page shows "Forgot password?" link below the password field only when `password_reset_enabled` is `true`.
- [frontend] Login page shows a green success banner when arriving from `/reset-password` via `?reset=success`.

## [0.19.0] - 2026-04-18

### Added
- [backend] `LOCAL_AUTH_DISABLED` config flag: set to `true` to hide the username/password login form in the UI. Requires at least one external provider (Google or OIDC) to be configured; ignored otherwise to prevent lockout.
- [backend] `GET /api/v1/auth/config` endpoint returns `local_auth_enabled` field so the frontend can conditionally render the login form.
- [frontend] Login page reads `local_auth_enabled` from the auth config API and hides the credentials form when local auth is disabled.

### Changed
- [infra] Replaced TimescaleDB with plain **PostgreSQL 18** across all environments (`docker-compose.yml`, `docker-compose.test.yml`, `k8s/database/statefulset.yaml`). The PG 18 image requires the data volume to be mounted at `/var/lib/postgresql` (not `/var/lib/postgresql/data`).
- [backend] Removed `CREATE EXTENSION timescaledb` and `create_hypertable` calls from Alembic migrations `0001` and `f91cc12066ce`. The schema is now fully compatible with plain PostgreSQL.

## [0.17.0] - 2026-04-18

### Fixed
- [backend] Reformatted 7 backend files with ruff and restored `type: ignore[import-untyped]` for `authlib` import in `auth.py` (CI uses `mypy --strict`, which requires the annotation).

## [0.16.0] - 2026-04-18

### Fixed
- [frontend] Resolved TypeScript build error in `TradeForm`: removed `.transform()` from the optional `currency` Zod field (caused output/input type mismatch with `zodResolver`) and moved `.toUpperCase()` into `onSubmit`.

## [0.15.0] - 2026-04-18

### Fixed
- [infra] Renamed workspace member in `uv.lock` from `tradejournal-backend` to `tradesensei-backend`, fixing Docker image builds that failed with `--frozen` after the app rename.

## [0.14.0] - 2026-04-18

### Added
- [backend] Introduced `simplified-execution-model`: `LogicalExecution` now tracks `origin` (`imported|manual|merged|split`), `deleted` (soft-delete flag), `user_modified`, and `parent_id` fields instead of the former `status` enum.
- [backend] Soft-delete for imported/merged/split executions: `DELETE /executions/{id}` returns 200 with body; manual executions are hard-deleted (204 No Content).
- [backend] `POST /executions/{id}/restore` endpoint: un-deletes a soft-deleted execution and re-aggregates the parent trade.
- [backend] `POST /executions/{id}/split` endpoint: splits one execution into two child executions with `origin='split'` and the original soft-deleted.
- [backend] `POST /imports/{account_id}/fresh-start` endpoint: deletes all executions and trades for an account within a single transaction, then re-imports from the provided file.
- [backend] `GET /trades/{id}/executions` and `GET /executions` support `?include_deleted=true` to show soft-deleted rows.
- [backend] `PATCH /broker-raw-transactions/{id}/suppress` endpoint to toggle the `suppressed` flag on raw transactions, preventing re-import.
- [backend] Configurable `statement_timeout` guard (default 60 s) on the fresh-start endpoint via `FRESH_START_TIMEOUT` env var.
- [backend] Alembic migration to drop the deprecated `has_conflict` column from the `trades` table.
- [backend] Alembic migration to add `deleted`, `user_modified`, `parent_id`, `origin` columns and supporting indexes to `logical_executions`.
- [frontend] `ExecutionStatusBadge` component derives its color from `origin` + `deleted` + `user_modified` (Imported=blue, Edited=amber, Manual=violet, Merged=orange, Split=cyan, Deleted=gray).
- [frontend] `ExecutionLegsTable` "Show deleted" toggle; deleted rows rendered at 50% opacity with a Restore button.
- [frontend] `SplitExecutionModal` for splitting a single execution into two, with qty/price/timestamp fields and a live preview.
- [frontend] Fresh Start section in the Import dialog, gated behind an explicit acknowledgement checkbox.
- [frontend] `useRestoreExecution`, `useSplitExecution`, and updated `useTradeExecutions` React Query hooks.

### Changed
- [backend] `_re_aggregate_trade` now filters to `deleted=False` executions only (Decision 5 of the spec).
- [backend] Merge-trades service uses `passive_deletes=True` on the `logical_executions` relationship and refreshes the ORM collection before deleting non-survivor trades, preventing FK-cascade data loss.
- [backend] `LogicalExecution` SQLAlchemy model uses `Enum(AssetClass/Direction, create_type=False)` to match the pre-existing PostgreSQL enum types.
- [frontend] Removed `has_conflict` badge from `TradeRow` and conflict count badge from the sidebar.
- [frontend] Removed `ConflictBanner` component from the trade detail page.
- [frontend] `ExecutionRow` uses `origin`/`deleted`/`user_modified` fields instead of deprecated `status`.

### Removed
- [backend] `has_conflict` field removed from `Trade` model, `TradeUpdate`/`TradeFilters` schemas, and all repository/API filter logic.
- [backend] `?has_conflict` query parameter removed from `GET /api/v1/trades`.
- [frontend] `useConflictTradeCount` hook removed from `useTrades.ts`.

### Fixed
- [backend] `merge_trades` service now correctly re-aggregates the survivor after reassigning executions by expiring the session-cached collections via `session.refresh` before deleting non-survivor trades.
- [backend] `delete_execution` for manual executions now cascade-deletes the parent trade when it has no remaining active executions.

### Renamed
- Application renamed from **Trade Journal** to **Trade Sensei** across the full stack: package names (`tradesensei-backend`), Docker/K8s resources, database name, API title, session cookie, frontend UI strings, CI/CD image tags, and all documentation.

## [0.10.0] - 2026-04-03

### Added
- [backend] Added `net_pnl` and `net_pnl_eur` fields to the `Trade` model and Pydantic schemas.
- [backend] Created an Alembic migration to calculate `net_pnl` for existing closed trades.
- [backend] Updated the trade aggregator to automatically calculate net P&L and net P&L EUR for closed trades.
- [frontend] Added `net_pnl` and `net_pnl_eur` to the `Trade` interface and aggregation hooks.
- [frontend] Redesigned the `PerformanceAnalysisDashboard` table with themed groupings: Overview, Profit & Loss, Win/Loss, and Averages.
- [frontend] Updated dashboard Insights and Charting to use Net P&L metrics as the primary performance indicator.

### Changed
- [frontend] Improved table visual hierarchy with theme-responsive borders (`#dadbdf` in light, `#29292b` in dark).

## [0.7.0] - 2026-03-28

### Fixed
- [frontend] Fixed Account E2E tests by adding `page.reload()` and count-based assertions for reliable deletion verification.
- [frontend] Stabilized `playwright.config.ts` by fixing `baseURL` and ensuring correct `storageState` inheritance across test projects.
- [frontend] Improved account deletion hook to correctly invalidate `trades` and `stats` caches, ensuring UI consistency.
- [auth] Made frontend redirect URLs configurable for OIDC/OAuth to support diverse deployment environments.

### Changed
- [infra] Updated `ci-green-loop` skill to support local verification via `gh act` before pushing.

## [0.6.0] - 2026-03-28

### Added
- [backend] Added generic OIDC client support via Authlib with configuration through environment variables.
- [backend] Implemented OIDC login, callback, and token exchange endpoints.
- [backend] Added session middleware to FastAPI for OAuth state management.
- [frontend] Added OIDC sign-in button and dynamic auth configuration.
- [frontend] Switched all API calls to relative paths (`/api/proxy`) for better Docker and Kubernetes compatibility.

### Fixed
- [frontend] Updated `OAuthErrorBanner` to be provider-agnostic.
- [frontend] Fixed Next.js proxy to handle OAuth redirects manually by setting `redirect: "manual"`.
- [backend] Forced `email_verified = True` for OIDC to support internal providers like Authentik.

### Changed
- [infra] Renamed `INTERNAL_API_URL` to `API_URL` and removed obsolete `NEXT_PUBLIC_API_URL`, `NEXTAUTH_SECRET`, and `NEXTAUTH_URL` from frontend service.

### Added
- [frontend] Added a collapsible desktop sidebar with drawer mode, persistent state in localStorage, and a floating toggle button for a cleaner workspace. Keyboard shortcut `Cmd/Ctrl + B` toggles the sidebar.

### Fixed
- [frontend] Playbook creation now shows immediately in the list without requiring a second item to be created (optimistic update via `setQueryData`).
- [frontend] Tag creation now shows immediately in the list without requiring a second item to be created (optimistic update via `setQueryData`).
- [frontend] Playbook update and delete now reflect immediately in the UI without requiring a page refresh (optimistic cache update via `setQueryData`).
- [frontend] Tag delete now reflects immediately in the UI without requiring a page refresh (optimistic cache update via `setQueryData`).
- [frontend] Tag filtering in the trades overview now works correctly — uses OR logic so trades with any of the selected tags are returned.
- [frontend] Account filter in the trades overview is now visible for all users, not just those with multiple accounts.
- [backend] Fixed tag filter in `GET /api/v1/trades` — FastAPI's `Depends()` does not parse `list[UUID]` query parameters from Pydantic models; `tag_ids` is now declared as an explicit `Query()` parameter on the endpoint and merged into the filter object before the service call.
- [backend] Fixed 500 Internal Server Error on `/api/v1/metrics/summary` and `/api/v1/metrics/equity-curve` caused by `MissingGreenlet` error in async SQLAlchemy when Pydantic serialized unloaded relationships (`playbook`, `tags`, `trade_notes`). All required relationships are now eagerly loaded via `selectinload`.

## [0.5.1] - 2026-03-26

### Added
- [infra] Implemented the `bump-version` skill and automated versioning tool for cross-component version synchronization.

### Changed
- [infra] Updated `package.json` files and component versions to follow the `0.5.x` semantic versioning scheme.

## [0.5.0] - 2026-03-26

### Added

- [frontend] "View Report" buttons added to the `PerformanceAnalysisDashboard` table to improve E2E test stability and user navigation.
- [backend] Google OAuth 2.0 integration: `users` table fields, `AuthService` logic, and API endpoints for authorization, callback, and token exchange.
- [frontend] Google Sign-In support: brand-compliant button, OAuth error handling, and session callback processing.
- [backend] Playbook, Tagging, and Psychological Note models with full CRUD API support.
- [backend] Time-series aggregation endpoints for P&L (daily/monthly), asset classes, symbols, and return distribution.
- [frontend] Initial dashboard visualization: metrics cards, equity curve, and drawdown charts using Recharts.
- [frontend] Advanced trade management: paginated trade list and broker import (IBKR/Schwab) UI.
- [infra] Iterative CI recovery skill (`ci-green-loop`) for automated triage and fix of GitHub Actions failures.

### Fixed

- [frontend] Performance Reports E2E tests (`reports.spec.ts`) now correctly locate and interact with the "View Report" buttons.

## [0.4.0] - 2026-03-15

### Added

- [backend] IBKR Activity Statement CSV parser and Charles Schwab trade history parser.
- [backend] Multi-part file upload endpoint for broker imports with ownership validation.

## [0.3.0] - 2026-03-01

### Added

- [backend] Performance metrics engine: win rate, profit factor, expectancy, Sharpe ratio, and max drawdown.
- [backend] Equity curve and drawdown curve time-series generation.

## [0.2.0] - 2026-02-15

### Added

- [backend] Multi-user support with User and Account models.
- [backend] JWT-based authentication with refresh token rotation and revocation.
- [backend] Account CRUD with strict user-level data isolation.

## [0.1.0] - 2026-02-01

### Added

- [backend] Initial data model and REST API for Trade management.
- [backend] TimescaleDB integration with hypertable partitioning for trades.
- [infra] Dockerized development stack and GitHub Actions CI/CD pipelines.


[1.16.2]: https://github.com/scheffold/TradeSensei/compare/v1.16.1...v1.16.2
[1.16.1]: https://github.com/scheffold/TradeSensei/compare/v1.16.0...v1.16.1
[1.16.0]: https://github.com/scheffold/TradeSensei/compare/v1.15.0...v1.16.0
[1.15.0]: https://github.com/scheffold/TradeSensei/compare/v1.14.0...v1.15.0
[1.14.0]: https://github.com/scheffold/TradeSensei/compare/v1.13.0...v1.14.0
[unreleased]: https://github.com/scheffold/TradeSensei/compare/v1.16.2...HEAD
[1.13.0]: https://github.com/scheffold/TradeSensei/compare/v1.12.0...v1.13.0
[1.12.0]: https://github.com/scheffold/TradeSensei/compare/v1.11.0...v1.12.0
[1.11.0]: https://github.com/scheffold/TradeSensei/compare/v1.10.0...v1.11.0
[1.10.0]: https://github.com/scheffold/TradeSensei/compare/v1.9.1...v1.10.0
[1.9.1]: https://github.com/scheffold/TradeSensei/compare/v1.9.0...v1.9.1
[1.9.0]: https://github.com/scheffold/TradeSensei/compare/v1.8.3...v1.9.0
[1.8.3]: https://github.com/scheffold/TradeSensei/compare/v1.8.2...v1.8.3
[1.8.2]: https://github.com/scheffold/TradeSensei/compare/v1.8.1...v1.8.2
[1.8.1]: https://github.com/scheffold/TradeSensei/compare/v1.8.0...v1.8.1
[1.8.0]: https://github.com/scheffold/TradeSensei/compare/v1.7.0...v1.8.0
[1.7.0]: https://github.com/scheffold/TradeSensei/compare/v1.6.1...v1.7.0
[1.6.1]: https://github.com/scheffold/TradeSensei/compare/v1.6.0...v1.6.1
[1.6.0]: https://github.com/scheffold/TradeSensei/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/scheffold/TradeSensei/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/scheffold/TradeSensei/compare/v1.3.6...v1.4.0
[1.3.6]: https://github.com/scheffold/TradeSensei/compare/v1.3.5...v1.3.6
[1.3.5]: https://github.com/scheffold/TradeSensei/compare/v1.3.4...v1.3.5
[1.3.4]: https://github.com/scheffold/TradeSensei/compare/v1.3.3...v1.3.4
[1.3.3]: https://github.com/scheffold/TradeSensei/compare/v1.3.2...v1.3.3
[1.3.2]: https://github.com/scheffold/TradeSensei/compare/v1.3.1...v1.3.2
[1.3.1]: https://github.com/scheffold/TradeSensei/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/scheffold/TradeSensei/compare/v1.2.5...v1.3.0
[1.2.5]: https://github.com/scheffold/TradeSensei/compare/v1.2.4...v1.2.5
[1.2.4]: https://github.com/scheffold/TradeSensei/compare/v1.2.3...v1.2.4
[1.2.3]: https://github.com/scheffold/TradeSensei/compare/v1.2.2...v1.2.3
[1.2.2]: https://github.com/scheffold/TradeSensei/compare/v1.2.1...v1.2.2
[1.2.1]: https://github.com/scheffold/TradeSensei/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/scheffold/TradeSensei/compare/v1.1.2...v1.2.0
[1.1.2]: https://github.com/scheffold/TradeSensei/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/scheffold/TradeSensei/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/scheffold/TradeSensei/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/scheffold/TradeSensei/compare/v0.27.1...v1.0.0
[0.27.1]: https://github.com/scheffold/OpenTradeJournal/compare/v0.27.0...v0.27.1
[0.27.0]: https://github.com/scheffold/TradeSensei/compare/v0.26.2...v0.27.0
[0.24.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.22.0...v0.24.0
[0.22.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.21.0...v0.22.0
[0.17.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.16.0...v0.17.0
[0.16.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.15.0...v0.16.0
[0.15.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.14.0...v0.15.0
[0.14.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.13.0...v0.14.0
[0.7.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/scheffold/OpenTradeJournal/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/scheffold/OpenTradeJournal/releases/tag/v0.1.0
