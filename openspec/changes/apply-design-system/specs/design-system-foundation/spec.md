## ADDED Requirements

### Requirement: Dual-Theme Performance-First Opaque CSS Token System (`docs/DESIGN.md` v2.0)
The frontend SHALL implement the dual-theme **Performance-First UI System v2.0** token block from `docs/DESIGN.md` §6 1:1 in `:root` (Light · Pure White) and `html.dark` (Dark · Layered Anthracite, default theme), plus `--float-shadow` and hex-literal semantic Tailwind bridge tokens (`--background`, `--sidebar`, `--foreground`, `--card`, `--card-foreground`, `--popover`, `--popover-foreground`, `--primary`, `--primary-foreground`, `--secondary`, `--secondary-foreground`, `--surface-muted`, `--muted`, `--muted-foreground`, `--accent`, `--accent-foreground`, `--destructive`, `--warning`, `--success`, `--danger`, `--border`, `--input`, `--ring`), and expose semantic Tailwind color utilities with working `/N` alpha modifiers via `color-mix(in srgb, ...)`.

#### Scenario: Layered Anthracite Dark is active by default with 100 % opaque tokens
- **WHEN** the application loads in a fresh browser session without a stored theme preference
- **THEN** `<html>` has the `dark` class
- **AND** `--bg-canvas` / `--background` resolves to `#11141B` (never pure black), `--bg-panel` / `--card` resolves to `#191E28`, `--bg-sub` / `--secondary` resolves to `#222936`, `--text-primary` / `--foreground` resolves to `#F1F5F9`, `--cta-bg` / `--primary` resolves to `#F59E0B`, `--emerald` / `--success` resolves to `#1CE88C`, and `--rose` / `--danger` resolves to `#FB7185`

#### Scenario: Pure White Light theme resolves crisp opaque white panels
- **WHEN** the user switches the theme to Light mode (`:root` without `.dark`)
- **THEN** `--bg-canvas` / `--background` resolves to `#F8F9FB`, `--bg-panel` / `--card` resolves to `#FFFFFF` (100 % opaque white), `--bg-sub` / `--secondary` resolves to `#F3F5F9`, `--border-panel` / `--border` resolves to `#DCE2EC`, `--text-primary` / `--foreground` resolves to `#0F172A`, `--cta-bg` / `--primary` resolves to `#D97706` with `--cta-text` / `--primary-foreground` `#0F172A`, `--sel-bg` resolves to `#FFF4ED` with `--sel-border` `#EA580C`, `--emerald` resolves to `#059669`, and `--rose` resolves to `#BE123C`

#### Scenario: Every DESIGN.md §6 token exists 1:1 in both themes
- **WHEN** `frontend/__tests__/app/globals-theme-parity.test.ts` compares `frontend/app/globals.css` with `docs/DESIGN.md` §6
- **THEN** every custom property in `docs/DESIGN.md` §6 is defined in both `:root` and `html.dark` with the exact documented value

### Requirement: Performance-First Solid-Color Rendering (60 FPS)
The frontend SHALL render every surface 100 % opaque and SHALL NOT use `backdrop-filter`, `-webkit-backdrop-filter`, Tailwind `backdrop-blur-*` / `backdrop-saturate-*` utilities, CSS `filter: blur(...)` or `filter: saturate(...)` on UI surfaces, ambient background orbs (`.ambient-orbs`), the glass utility names `.glass-chrome`, `.glass-card`, `.glass-inset`, `.glass-float`, `.btn-glass`, or `transition-all`. Depth SHALL come only from the three tonal levels `--bg-canvas` → `--bg-panel` → `--bg-sub`, `1px` hairline borders, `--top-edge` in Dark mode, and the single-layer `--float-shadow` on floating layers.

#### Scenario: Guard test finds no blur, orb or glass remnants
- **WHEN** `frontend/__tests__/app/zero-blur-guard.test.ts` scans every `.css`, `.ts` and `.tsx` file under `frontend/app`, `frontend/components` and `frontend/lib`
- **THEN** it finds zero occurrences of `backdrop-filter`, `backdrop-blur`, `backdrop-saturate`, `filter: blur`, `filter: saturate`, `ambient-orbs`, `orb-drift`, `--orb-`, `--glass-`, `glass-chrome`, `glass-card`, `glass-inset`, `glass-float`, `btn-glass` and `transition-all`

### Requirement: Zero Generic SaaS Blue in UI Chrome, Badges, Modals, and Charts
Application UI components, CSS utilities, modals, badges, progress indicators, and charts SHALL NOT use generic SaaS blue, indigo, sky, violet, purple, or cyan accent classes or hex values (`blue-*`, `indigo-*`, `sky-*`, `violet-*`, `purple-*`, `cyan-*`, `#6366f1`, `#6063dd`, `#5153ba`, `#4f52b7`, `#3b82f6`, `#8b5cf6`) or butter-yellow selection (`amber-100`, `#FEF3C7`). User-configurable taxonomy/tag palette definitions (`lib/constants/colors.ts`) are exempt as user data.

#### Scenario: Source audit finds zero forbidden SaaS blue utilities or dark: modifiers in UI components
- **WHEN** `frontend/app` and `frontend/components` are scanned for `(bg|text|border|ring|from|to|via|fill|stroke)-(blue|indigo|sky|violet|purple|cyan)-[0-9]+`, `dark:`, and `#6063dd` / `#6366f1` / `#3b82f6` / `#8b5cf6`
- **THEN** zero matches are found

### Requirement: Typography & Tabular Numeric Formatting
The application SHALL use `Inter` (weights 400, 500, 600, 700) for display and body copy and `IBM Plex Mono` (weights 400, 500, 600, 700) for monospace text, and every price, P&L value, percentage, count, metric, and timestamp rendered with `.font-mono` or `.tnum` SHALL enforce `font-variant-numeric: tabular-nums`.

#### Scenario: Numeric figures render with IBM Plex Mono and tabular numerals
- **WHEN** a price, P&L figure, win-rate percentage, quantity, or execution timestamp is rendered in a table, KPI card, or price pill
- **THEN** its computed style includes `"IBM Plex Mono"` in `font-family` and `tabular-nums` in `font-variant-numeric`

### Requirement: Solid-Amber Action Buttons, Opaque Surfaces & Canonical Logo Sync
Primary CTAs (`.btn-primary`, `.btn-solid`) SHALL render as Solid Amber buttons (`--cta-bg`: `#D97706` Light / `#F59E0B` Dark, hover `--cta-hover`: `#F59E0B` / `#FBBF24`, `1.5px solid var(--cta-border)`, dark text `--cta-text`: `#0F172A` / `#11141B`, `6px` radius, `font-semibold`). Secondary buttons (`.btn-secondary`, `.btn-ghost`) SHALL render as opaque `--btn-sec-bg` controls (`6px` radius). Global `TopBar` and sidebars SHALL use `.surface-chrome`, standalone panels `.solid-card` (`8px` radius), nested tiles/mobile list cards `.panel-sub` (`6px` radius), and modals/popovers/toasts `.panel-float` (`8px` radius, `--float-shadow`). `frontend/public/logo.svg` and `frontend/app/icon.svg` SHALL be byte-identical to repository-root `logo.svg`.

#### Scenario: Canonical logo copies are byte-identical
- **WHEN** `logo.svg`, `frontend/public/logo.svg` and `frontend/app/icon.svg` are compared with `cmp`
- **THEN** all three files are byte-identical

### Requirement: Soft-Orange Row & Navigation Selection and Strict Market Signal Separation
Data table rows and selectable list rows using `.wl-row` SHALL display `background-color: var(--bg-sub)` on `:hover`, `background-color: var(--sel-bg)` with a `2px` `--amber` inset left edge and `--sel-text` ticker highlight when `.selected`, and `opacity: 0.7` (no CSS `filter`) snapping back to `1` on `:hover` when `.dimmed`. Active sidebar items (`.nav-active` / `.sidebar-item[aria-current="page"]`) and active segmented toggles (`.metric-toggle-active`) SHALL also use `--sel-bg` and `--sel-text`. Quantitative P&L and market state SHALL use `--emerald` (`success`), `--rose` (`danger`), and `--caution-*` (`warning`). Every caution/warning badge, banner, or conflict highlight (`.badge-caution`, `.surface-caution`, `.surface-warning`) SHALL render with a `1px dashed var(--caution-border)` border so it never visually collides with solid UI selection.

#### Scenario: Caution banners and conflict badges render with a 1px dashed border
- **WHEN** `ConflictBanner`, `InsufficientDataBanner`, `CorrectTradeModal` warning notice, `MergePreviewModal` warning notice, or an edited/conflict badge is rendered
- **THEN** its container uses `--caution-bg` / `--caution-text` and a `1px dashed` `--caution-border`
