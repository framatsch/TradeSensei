# Trade Sensei — Frontend Style Guide

> **Design System Single Source of Truth:** [`docs/DESIGN.md`](./DESIGN.md) (*Performance-First UI System v2.0 — Zero-Blur · 60 FPS*) defines the authoritative color palette, CSS custom properties (`:root` and `html.dark`), 100 % opaque three-level tonal surfaces, `IBM Plex Mono` tabular typography, Solid-Amber CTAs, Soft-Orange selection, dashed caution badges and chart colors. Whenever visual tokens or surface rules in this document differ from `docs/DESIGN.md`, **`docs/DESIGN.md` takes precedence**.

**Source files:**
- Design System Spec: `docs/DESIGN.md` (Version 2.0)
- Tokens & component classes: `frontend/app/globals.css`
- Tailwind color mapping: `frontend/tailwind.config.ts`
- Chart token constants: `frontend/lib/constants.ts`

---

## 1. Themes & 3-Level Opaque Tonal Hierarchy

Two independently calibrated 100 % opaque themes are supported:
- **Dark (Layered Anthracite, Default)** — `.dark` / `html.dark` on `<html>`:
  - Level 0 Canvas (`--bg-canvas` / `background`): `#11141B` (Deep Slate-Navy — **no pure black**)
  - Level 1 Panels & Chrome (`--bg-panel` / `card`, `sidebar`): `#191E28` (`1px solid #2A3242`, `--top-edge: inset 0 1px 0 rgba(255, 255, 255, 0.04)`)
  - Level 2 Sub-Cards, Sticky Headers & Row Hover (`--bg-sub` / `secondary`): `#222936` (`1px solid #2D3647`)
- **Light (Pure White)** — `:root`:
  - Level 0 Canvas (`--bg-canvas` / `background`): `#F8F9FB` (Cool Alabaster)
  - Level 1 Panels & Chrome (`--bg-panel` / `card`, `sidebar`): `#FFFFFF` (100 % opaque Pure White, `1px solid #DCE2EC`)
  - Level 2 Sub-Cards, Sticky Headers & Row Hover (`--bg-sub` / `secondary`): `#F3F5F9` (`1px solid #E4E9F2`)

**Rule:** Never use `dark:` Tailwind modifiers or raw palette utilities (`zinc-*`, `gray-*`, `slate-*`, `blue-*`, `indigo-*`). The theme switches solely through CSS custom properties in `frontend/app/globals.css`.

---

## 2. Semantic Color Tokens

Always use these Tailwind class names. They map to CSS variables defined in `globals.css` and support `/N` alpha modifiers via `color-mix(in srgb, ...)` in `tailwind.config.ts`.

| Purpose | Semantic token / Tailwind class | Light (`:root`) | Dark (`html.dark`) |
| --- | --- | --- | --- |
| Page canvas (Level 0) | `background` (`--bg-canvas`) | `#F8F9FB` | `#11141B` |
| Chrome, sidebar and panels (Level 1) | `sidebar`, `card`, `card-foreground` (`--bg-panel`) | `#FFFFFF` / `#0F172A` | `#191E28` / `#F1F5F9` |
| Sub-cards, sticky headers, hover (Level 2) | `secondary`, `muted` (`--bg-sub`) | `#F3F5F9` | `#222936` |
| Tooltips and dropdowns | `popover`, `popover-foreground` | `#FFFFFF` / `#0F172A` | `#191E28` / `#F1F5F9` |
| Main and secondary text | `foreground` (`--text-primary`), `muted-foreground` (`--text-secondary`) | `#0F172A` / `#475569` | `#F1F5F9` / `#94A3B8` |
| Borders and fields | `border` (`--border-panel`), `hairline` (`--border-sub`), `input` | `#DCE2EC` / `#E4E9F2` / `#C8D1DF` | `#2A3242` / `#2D3647` / `#334155` |
| Primary action and focus | `primary`, `accent`, `ring` (`--amber` / `--cta-bg`) | `#D97706` (`#0F172A` fg) | `#F59E0B` (`#11141B` fg) |
| Positive and negative data | `success` (`--emerald`), `danger` (`--rose`) | `#059669` / `#BE123C` | `#1CE88C` / `#FB7185` |
| Warning / destructive action | `warning` (`--caution-text`), `destructive` | `#9A3412` / `#BE123C` | `#FBBF24` / `#FB7185` |
| Modal backdrop | `overlay` | `rgba(15, 23, 42, 0.56)` | `rgba(0, 0, 0, 0.64)` |
| Floating layers | `shadow-float` (`--float-shadow`) | `0 8px 24px rgba(15, 23, 42, 0.12)` | `0 8px 24px rgba(0, 0, 0, 0.40)` |

The source logo is `logo.svg` at the repository root. `frontend/public/logo.svg` and `frontend/app/icon.svg` must be byte-identical copies (`cmp logo.svg frontend/public/logo.svg` and `cmp logo.svg frontend/app/icon.svg`).

---

## 3. Forbidden Patterns (Enforced by `zero-blur-guard.test.ts`)

These patterns are **never** acceptable anywhere in `frontend/app`, `frontend/components` or `frontend/lib`:

```tsx
// ❌ Generic SaaS blue / violet / cyan accents or butter-yellow selection
<div className="bg-blue-600 text-indigo-400 bg-amber-100" />

// ❌ Hardcoded neutral palette classes or dark: modifiers
<div className="bg-zinc-900 text-gray-500 dark:bg-slate-800" />

// ❌ Backdrop blur, ambient orbs, glass classes or transition-all (Zero-Blur · 60 FPS)
<div className="backdrop-blur-md glass-card transition-all" />
```

**Exception:** User-chosen tag/taxonomy color swatches in `frontend/lib/constants/colors.ts` are user data.

---

## 4. Shared Opaque Component Utility Classes

Defined in `frontend/app/globals.css` under `@layer components`.

| Class | Usage |
| --- | --- |
| `.surface-chrome` | Top bar and sidebar chrome (Level 1, 100 % opaque `--bg-panel`, `--border-panel`, `--top-edge`) |
| `.solid-card` | Dashboard panels and tables (Level 1, 100 % opaque `--bg-panel`, `8px` radius) |
| `.panel-sub` | KPI tiles, chart boxes, nested tiles and mobile list cards (Level 2, 100 % opaque `--bg-sub`, `6px` radius) |
| `.panel-float` | Dialogs, popovers, dropdown menus and toasts (`8px` radius, opaque `--bg-panel`, single-layer `--float-shadow`) |
| `.btn-primary`, `.btn-solid` | Solid-Amber primary action (`--cta-bg`, `1.5px solid var(--cta-border)`, dark `--cta-text`, `6px` radius) |
| `.btn-secondary`, `.btn-ghost` | Opaque secondary action (`--btn-sec-bg`, `1px solid var(--btn-sec-border)`, `6px` radius) |
| `.btn-selected`, `.pill-active` | Active filter / toggle pill (Soft-Orange `--sel-bg`, `1.5px solid var(--sel-border)`, `--sel-text`) |
| `.price-pill` | Tabular-numeral price pill (`--bg-sub`, `1px solid var(--border-sub)`, `6px` radius) |
| `.metric-toggle-bar` | Segmented-control container (`--bg-sub`, `1px solid var(--border-sub)`, `9999px` radius) |
| `.metric-toggle-active`, `.metric-toggle-inactive` | Segment states (Soft-Orange active) |
| `.sidebar-item`, `.nav-active` | Sidebar items (hover `--bg-sub`; active Soft-Orange `--sel-bg` + `--sel-text` + `2px` `--amber` left edge) |
| `.wl-row`, `.radiant-table` | Row hover (`--bg-sub`), selection (`--sel-bg` + `2px` `--amber` left edge + `--sel-text` ticker), dimming (`opacity: 0.7`) |
| `.badge-positive`, `.surface-success` | Vivid green signal badge/surface (`--emerald-bg`, `--emerald-border`, `--emerald`) |
| `.badge-negative`, `.surface-danger` | Stress rose signal badge/surface (`--rose-bg`, `--rose-border`, `--rose`) |
| `.badge-caution`, `.surface-caution`, `.surface-warning` | Caution badge/surface (`--caution-bg`, `--caution-text`, always **`1px dashed var(--caution-border)`**) |
| `.badge-neutral` | Neutral opaque badge (`--bg-sub`, `--border-sub`, `--text-secondary`) |

---

## 5. Typography & Numerics

- **Display & UI Body (`--font-sans`):** `Inter` (400, 500, 600, 700)
- **Quantitative / Mono (`--font-mono`):** `IBM Plex Mono` (400, 500, 600, 700)
- **Tabular Numerals (`.tnum` / `.font-mono`):** Every price, P&L figure, percentage, ratio, count, and timestamp MUST use `font-mono` or `.tnum` (`font-variant-numeric: tabular-nums`).
- **Secondary Units (`.unit-dim` / `.unit-muted`):** Render secondary units (`$`, `%`, `pts`, `M`) muted (`--text-muted`).

---

## 6. Chart Tokens (`frontend/lib/constants.ts`)

Use `CHART_COLORS` for Recharts series and tooltips:

| Key | Value | Purpose |
| --- | --- | --- |
| `CHART_COLORS.primary` | `var(--amber)` | Primary series (Amber `#D97706` / `#F59E0B`) |
| `CHART_COLORS.success` | `var(--emerald-chart)` | Profit / positive series (`#10B981` Light / `#1CE88C` Dark) |
| `CHART_COLORS.danger` | `var(--rose)` | Loss / negative series (`#BE123C` Light / `#FB7185` Dark) |
| `CHART_COLORS.warning` | `var(--caution-border)` | Caution / threshold series |
| `CHART_COLORS.grid` | `var(--chart-grid)` | Dashed (`3 3`) gridlines (`#E2E8F0` Light / `#252D3C` Dark) |
| `CHART_COLORS.tooltip` | `--bg-panel` / `--border-panel` | Opaque Level-1 tooltip container |

---

## 7. Verification & Review Checklist (for `ui-reviewer`)

- Automated gates:
  - `npx tsc --noEmit`, `npm run lint`, `npm test -- --watchAll=false` (including `globals-theme-parity.test.ts` and `zero-blur-guard.test.ts`), and `npm run build`.
  - `cmp logo.svg frontend/public/logo.svg` and `cmp logo.svg frontend/app/icon.svg`.
- Visual check in **both Layered Anthracite (Dark) and Pure White (Light)** at `1440×900` and `375×812`:
  - [ ] All panels are 100 % opaque (`#FFFFFF` on `#F8F9FB` in Light; `#191E28` on `#11141B` in Dark) — zero transparency, zero blur, zero ambient orbs
  - [ ] Primary CTAs (`.btn-primary`) are Solid Amber (`#D97706` Light / `#F59E0B` Dark) with high-contrast dark text (`#0F172A` / `#11141B`)
  - [ ] Active pills and selected rows/nav items use Soft-Orange (`--sel-bg`, never butter-yellow) with a `2px` `--amber` left edge on rows/sidebar items
  - [ ] Caution banners and badges use `.surface-caution` / `.badge-caution` (`1px dashed` border)
  - [ ] All numeric values, P&L figures, percentages, and dates use `font-mono` / `.tnum` (`tabular-nums`)
