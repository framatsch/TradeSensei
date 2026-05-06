## 1. Help Content Centralization

- [x] 1.1 Create `frontend/lib/help-content.ts` with the new help dictionary structure.
- [x] 1.2 Extract existing help content from `frontend/app/help/page.tsx` into the dictionary.
- [x] 1.3 Add new help content for Playbooks (Types, Rules, Execution).
- [x] 1.4 Add new help content for Portfolios (Equity Curves, Risk, Multi-account).
- [x] 1.5 Add new help content for Market Check-ins (Bias, Focus, Review).
- [x] 1.6 Update `frontend/app/help/page.tsx` to consume content from `frontend/lib/help-content.ts`.

## 2. Hover-Card Tooltip System

> **Descoped** — user decided to keep the existing popup navigation to `/help#anchor` via `MetricHelpLink`.
> No `HelpTooltip` component will be implemented.

- [x] 2.1 ~~Implement `HelpTooltip` component~~ — descoped, `MetricHelpLink` retained.
- [x] 2.2 ~~Tooltip displays summary + "Read more" link~~ — descoped.
- [x] 2.3 ~~Style tooltip~~ — descoped.

## 3. UI Integration

> **Scope adjusted** — instead of replacing `MetricHelpLink` with `HelpTooltip`, we wired
> `helpAnchor` props into all previously unlinked charts and widgets.

- [x] 3.1 Wire `helpAnchor` into Dashboard charts (EquityCurveChart, DrawdownChart, DailyPnlBarChart, ReturnDistributionChart).
- [x] 3.2 Wire `helpAnchor` into Reporting/Overview widgets (EquityCurveWidget, DrawdownWidget, RMultipleDistributionWidget, PayoffRatio, PsychologicalAttributionWidget, PlaybookPhaseHeatmapWidget).
- [x] 3.3 Wire `helpAnchor` into Strategy widgets (MaeMfeScatterWidget, DurationVsPnlScatterWidget).
- [x] 3.4 Add new help entries for Overview Charts, Strategy Analysis, Time Analysis sections.

## 4. Markdown Export Tool

- [x] 4.1 Create `tools/export_help.ts` script to generate a Markdown glossary.
- [x] 4.2 Add `export-help` npm script in `frontend/package.json`.
- [x] 4.3 Verified: export produces `docs/HELP_GLOSSARY.md` with 10 sections / 49 entries.

## 5. Verification

- [x] 5.1 `npx tsc --noEmit` passes with zero errors.
- [x] 5.2 All `helpAnchor` props point to existing IDs in `frontend/lib/help-content.ts`.
- [x] 5.3 `/help` page consumes content from the dictionary — `HelpClient` import updated.
