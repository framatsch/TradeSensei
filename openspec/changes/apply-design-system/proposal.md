## Why

Trade Sensei's frontend originally mixed an older Indigo/Violet "Radiant" palette (`#6366f1`, `#5153ba`, `#6063dd`, `#8b5cf6`), scattered generic SaaS blues (`blue-*`, `indigo-*`, `sky-*`, `violet-*`, `cyan-*`), 162 prohibited `dark:` utility overrides, 146 hardcoded `zinc-*`/`gray-*`/`slate-*` classes, and broken Tailwind `/N` opacity modifiers on hex CSS variables. An intermediate v1.0 glassmorphic spec introduced translucent panels (`rgba(255,255,255,0.60)` in Light, `rgba(20,22,26,0.72)` in Dark), near-black `#090a0c` canvas, `backdrop-filter: blur(...)`, and ambient orbs. Adopting **`docs/DESIGN.md` v2.0** (*Performance-First UI System — opaque solid colors · 60 FPS*), unified with `VisioTrade`, establishes a 100 % opaque three-level tonal hierarchy in **Layered Anthracite** (Dark, default) and **Pure White** (Light) without altering layout grids, component hierarchy, routing, or business logic.

## What Changes

- **Design-System Governance**: Anchor `docs/DESIGN.md` v2.0 as the mandatory single source of truth for look & feel across `AGENTS.md` (`GEMINI.md`), `CLAUDE.md`, `.github/copilot-instructions.md`, `.opencode/agents/frontend-engineer.md`, `.opencode/agents/ui-reviewer.md`, `.opencode/skills/ui-visual-check/SKILL.md`, and `docs/styleguide.md`.
- **Tokens, Theme Default & Typography (`globals.css`, `tailwind.config.ts`, `app/layout.tsx`, `app/providers.tsx`, `app/manifest.ts`)**:
  - Implement the exact 1:1 `:root` (Pure White Light: `--bg-canvas: #F8F9FB`, `--bg-panel: #FFFFFF`, `--bg-sub: #F3F5F9`) and `html.dark` (Layered Anthracite Dark, default: `--bg-canvas: #11141B`, `--bg-panel: #191E28`, `--bg-sub: #222936` — no pure black) custom properties from `docs/DESIGN.md` §6, bridged as hex literals to Tailwind semantic tokens with `color-mix` alpha support.
  - Configure `Inter` (400–700) + `IBM Plex Mono` (400–700) with `font-variant-numeric: tabular-nums` (`.tnum` and global `.font-mono`).
  - Provide 100 % opaque surface and control contracts (`.surface-chrome`, `.solid-card`, `.panel-sub`, `.panel-float`, `.btn-primary`, `.btn-secondary`, `.btn-ghost`, `.btn-selected`, `.price-pill`, `.wl-row`, `.badge-caution`, `.badge-neutral`) with zero `backdrop-filter`, zero ambient orbs, and zero `transition-all`.
- **Global Chrome, Logo & Auth Controls**:
  - Restyle `TopBar` and sidebars (`.surface-chrome`, `.sidebar-item`, `.nav-active` with Soft-Orange `--sel-*` and `2px` `--amber` left edge), sub-tab bars / segmented tracks (`.metric-toggle-*`), dropdowns/popovers (`.panel-float`), and action buttons (`.btn-primary` Solid Amber `--cta-bg` with `1.5px` `--cta-border` and dark `--cta-text`; `.btn-secondary` opaque secondary surface `--btn-sec-*`).
  - Sync `frontend/public/logo.svg`, `frontend/app/icon.svg`, and PWA PNG icons with the canonical repository-root `logo.svg` (amber `#d97706` hexagon) and align the auth/login header (`<Logo size={72} className="rounded-2xl" />` inside `.solid-card`).
- **Tables, Rows & List Interaction Contracts**: Apply the opaque `.wl-row` hover (`--bg-sub`), selection (`--sel-bg` + `inset 2px 0 0 var(--amber)` + `--sel-text` ticker + `6px` `--amber` focus dot), and `.dimmed` (`opacity: 0.7`, snapping to `1` on hover, no CSS `filter`) contracts across tables and selectable rows.
- **Strict UI Selection vs. Market Signal Separation, Charts, Modals & Guard Tests**:
  - Eliminate all generic SaaS blue/indigo/violet/sky/cyan UI chrome, badges, progress bars, `#6063dd` modal CTAs, and chart defaults (preserving user-configurable tag palette data in `lib/constants/colors.ts`).
  - Enforce `1px dashed` borders + warning iconography on caution/conflict banners and badges so `--caution-*` never visually collides with solid UI selection.
  - Upgrade modals/dialogs to opaque `.panel-float` with single-layer `--float-shadow` and enforce parity and zero-blur rules via `globals-theme-parity.test.ts` and `zero-blur-guard.test.ts`.

## Capabilities

### New Capabilities
- `design-system-foundation`: Dual-theme opaque token system (`docs/DESIGN.md` v2.0), typography & tabular numerals, three-level opaque tonal surfaces, Solid-Amber CTAs, Soft-Orange selection, `.wl-row` table/list interaction contracts, UI-selection-vs-market-signal separation, canonical logo sync, and blur-free 60-FPS guard tests.

### Modified Capabilities
<!-- None: existing functional, responsive-layout, routing, and data-fetching requirements remain unchanged. -->

## Impact

- **Frontend (`frontend/`)**: CSS custom properties and opaque component utilities in `app/globals.css`, color/shadow/font config in `tailwind.config.ts`, root theme/font setup in `app/layout.tsx`, `app/providers.tsx`, `app/manifest.ts`, synced `public/logo.svg` & `app/icon.svg`, and class-only styling updates across `components/` and `app/`.
- **Tests (`frontend/__tests__/`)**: Added `globals-theme-parity.test.ts` and `zero-blur-guard.test.ts`; updated class/manifest assertions in `NoteForm.test.tsx` and `PwaRegistrar.test.tsx`.
- **Backend / API / Database / Docker**: Untouched. No schema, OpenAPI, routing, or state logic changes.
