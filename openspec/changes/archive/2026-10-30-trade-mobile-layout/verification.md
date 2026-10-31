# Trade mobile layout verification

**Status: complete as of 2026-10-30.** All **44 tasks**, including **7.8**, are checked in [tasks.md](tasks.md). The frontend validation gates and the standard repository-root Playwright run pass. Earlier red runs are superseded diagnostic history, not outstanding work.

## Automated checks

| Check | Result |
|-------|--------|
| Root `openspec validate trade-mobile-layout --strict` | Passed |
| Frontend `npm run lint` | **0 errors, 64 nonblocking warnings**, no fatal configuration errors |
| Frontend `npx tsc --noEmit --incremental false` | Passed |
| Full frontend `npm test -- --runInBand` | **548 passed, 0 failed, 0 skipped; 63 of 63 suites passed** |
| Root `./frontend/node_modules/.bin/tsc --project tsconfig.playwright.json --noEmit --incremental false` | Passed |

The completed scope includes the previously failing frontend unit suites and handwritten-code lint findings, not just the mobile feature files. Production fixes use explicit types and corrected hook/state behavior rather than new `any` types or inline suppressions. `npm run lint` uses ESLint flat configuration under Next.js 16 instead of the removed `next lint` command. Generated `frontend/lib/api/**/*.gen.ts` files are excluded from ESLint instead of being edited manually; TypeScript still checks them.

Machine-readable completion reports and logs are in the ignored `tmp/trade-mobile-layout/` directory: `unit-complete.json`, `unit-complete.log`, `lint-complete.json`, and `lint-complete.log`. All artifact paths in this record are relative to the repository root, not to the change directory.

The backend, API endpoints, and database schema are unchanged. This record does not claim a backend test run or a database migration.

## Complete headless Playwright suite

The standard root command, `npm run test:e2e -- --retries=0`, runs against the local stack with Chromium in headless mode: **200 cases in 29 files**, including setup. The completion run takes **130.968 seconds** and reports:

| Result | Count |
|--------|-------|
| Passed | 196 |
| Failed | 0 |
| Intentionally skipped | 4 |
| Flaky | 0 |

All five `@trade-mobile-layout` cases pass in this parallel full-suite run. They cover mobile tabs and draft persistence, execution-card editing and reload persistence, mobile sorting/selection/filtering/card navigation, and cross-page navigation/back-query restoration/deep links at 375px and 1440px. Boundary tests verify the actual GET's filter, sort, page size and stored cursor, not merely the resulting URL. Previous across the boundary requires no additional list request; fixture creation waits for authenticated GET visibility before adding an execution, and no write request is retried.

`playwright.config.ts` now selects `tsconfig.playwright.json`, whose `@playwright/test` path resolves test imports to the single root runtime. The installed root Playwright **1.58.2** and frontend Playwright **1.62.0** coexist without dependency symlinks, version bumps, or a temporary test configuration. The frontend application retains its own TypeScript configuration and dependency resolution. The root configuration explicitly enables headless mode, disables automatic HTML-report opening, and writes JSON to `test-results/results.json`.

The two legacy failures from the earlier full run are also resolved:

- `frontend/tests/specs/reporting-hub.spec.ts`: `renders global filter bar` locates the **Filters button** by role and accessible name, allowing its optional count badge without matching the Annotation Filters label.
- `frontend/tests/specs/topbar-navigation.spec.ts`: the logout case waits for the login form, then uses a bounded, read-only `toPass` assertion to verify the login URL and cleared token despite competing logout/auth-guard navigation. The sign-out action is not retried.

Both repaired cases pass three consecutive repetitions in the focused run: **10 passed, 0 failed**, including setup and the existing execution-editor case selected by the same focus pattern. Its evidence is `tmp/trade-mobile-layout/playwright-two-fixes-green-results.json` and `playwright-two-fixes-green.log`.

Original test coverage is preserved. Existing trade selectors are scoped only where responsive dual rendering introduces hidden duplicate headers, panels, or menus; no new skips replace assertions.

The four skips are existing declared skips/fixmes: imported closed combo seed unavailable, two BentoMenu cases, and the Model Book star case. They are not dependency-blocked cases.

Reproduction from the repository root, with `rtk proxy` preserving reporter output:

```bash
rtk proxy npm run test:e2e -- --retries=0
```

Final structured report: `tmp/trade-mobile-layout/playwright-all-green-results.json`. Complete log: `tmp/trade-mobile-layout/playwright-all-green.log`.

## Historical diagnostic runs (superseded)

The completion scope includes all old frontend validation issues, including failures excluded by the initial narrow scope. The following reports remain diagnostic history only:

- `unit-results.json` and `lint-results.json` record **510 passed / 38 failed** unit tests and **130 lint errors / 130 warnings** before those repairs.
- `playwright-full-final-results.json` records **194 passed / 2 failed / 4 skipped** using the earlier temporary configuration. Both failures are repaired and pass in the completion run above.
- The earlier `Requiring @playwright/test second time` error and temporary frontend-runtime configuration are superseded by the permanent root TypeScript mapping. Temporary configurations are not required for the supported root command.

These historical reports live under `tmp/trade-mobile-layout/`. The completion reports above are authoritative.

## Desktop baseline comparison

An isolated, unmodified HEAD worktree served as the baseline. Both versions used the same temporary test data, viewport, locale, time zone, and theme. The temporary test user was deleted after each comparison.

- At **1440 × 900**, the trade list, expanded desktop filters, and desktop selection state are pixel-identical to baseline.
- Detail grid widths and card dimensions match baseline. The new navigation row moves the detail content down by 15px.
- Card-level detail captures show only small rendering differences after restoring the original desktop metric typography (121 pixels in Performance, 17 in Execution Summary, and 22 in the journal card).
- Baseline/current captures, geometry, and pixel-difference results are in `tmp/trade-mobile-layout/desktop-comparison/`.

The authorized UI reviewer confirmed desktop preservation. The sole desktop visual finding, insufficient contrast on the new position indicator, was fixed using `text-foreground`; the recaptured indicator measures **17.15:1** contrast. The desktop recheck has no remaining CRITICAL, WARNING, or SUGGESTION findings. Its 10 navigation-control unit tests pass after the correction.

The temporary baseline server was stopped and both baseline worktree registrations were removed. Screenshot artifacts remain in the ignored directory above.

## Mobile and responsive captures

Fresh live-API captures are in `tmp/trade-mobile-layout/recapture/`, with measurements in `measurements.json`. The capture harness creates an isolated temporary user and removes that user after closing the browser; it does not mock backend responses.

- **375 × 812, light and dark:** list, selection/bulk bar, filter sheet, expanded Account dropdown, overview with compact navigation, open-trade header, chart-options panel, performance/summary, journal/notes, dirty journal bar, execution cards, leg actions/Delete confirmation, and combo-option execution cards.
- **768 × 1024:** the same mobile layout and overflow checks.
- **1440 × 900:** current desktop list, detail/navigation, and chart options.
- Document and main-content widths equal the viewport in every measured state. No uncaught page errors were recorded.
- At 375px, the chart-options control is at x63–101 and its panel at x29–221: neither is clipped. Trade navigation remains inactive while the chart-options dialog is open.

The first mobile visual pass found low-contrast colored text and a clipped chart control. Both were corrected locally: opt-in text contrast below `lg` uses existing semantic tokens without changing global theme values, and the chart toolbar wraps below `lg` while its options panel stays inside the card. The Delete confirmation uses a readable outlined danger treatment. A code-review recheck found no issues and measured sampled contrast of at least **4.84:1 in light mode / 6.83:1 in dark mode** (Delete: **6.87:1 / 9.67:1**).

Final rendered visual review: **PASS**, with no remaining introduced CRITICAL/WARNING findings. The selected-card symbol retains readable foreground on hover (17.75:1 in dark mode), and an opaque sticky wrapper covers the nested scroll container's top-padding gap. The corrected captures use the actual trade-view scroller and show the below-fold performance/summary, clean journal preview/notes, and distinct dirty-top/bottom states.

## Code review

The read-only code review identified three navigation defects, all fixed and confirmed resolved in a focused recheck:

1. Journal changes made while a next-page request is pending are checked immediately before navigation. Cancelling leaves the draft and stored context intact.
2. Requests finishing after unmount, a trade change, or a portfolio change cannot write context or navigate.
3. Add, Split, Link, Move, and Detach execution dialogs expose modal semantics, so global trade shortcuts remain inactive while they are open.

Deferred-response hook tests and nine integrated tests using the real execution dialogs cover these cases.

## Known nonblocking operational limitations

- **Physical-device safe areas:** desktop-browser viewport emulation does not reproduce actual nonzero device safe-area insets. The bars include the specified `env(safe-area-inset-bottom)` padding, but these captures and headless checks are not physical-device validation.
- **Graph maintenance:** the recorded Graphify code-refresh attempt has a **180-second timeout**. No generated graph files are part of the change; this maintenance limitation does not invalidate the passing frontend and browser checks above.
