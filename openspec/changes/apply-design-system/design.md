## Context

`docs/DESIGN.md` (Version 2.0 — **Performance-First UI System · opaque solid colors · 60 FPS**, shared with `VisioTrade`) defines the authoritative look & feel for Trade Sensei:
- **100 % Opaque Three-Level Tonal Layering** in **Layered Anthracite Dark** (`.dark` default: `--bg-canvas: #11141B`, `--bg-panel: #191E28`, `--bg-sub: #222936` — never pure black) and **Pure White Light** (`:root`: `--bg-canvas: #F8F9FB`, `--bg-panel: #FFFFFF`, `--bg-sub: #F3F5F9` — never transparent).
- **Solid colors · 60 FPS**: Zero `backdrop-filter`, zero `backdrop-blur-*`, zero `filter: blur()` / `saturate()`, zero ambient background orbs, zero multi-layer shadows, and zero `transition-all`.
- **Strict Separation Between UI Selection and Market Signals**:
  - **Primary CTAs**: Solid Amber (`--cta-bg`: `#D97706` Light / `#F59E0B` Dark, hover `#F59E0B` / `#FBBF24`, `1.5px` `--cta-border`, high-contrast dark text `--cta-text`: `#0F172A` / `#11141B`).
  - **Selection & Active Pills**: Soft-Orange (`--sel-bg`: `#FFF4ED` Light / `rgba(245, 158, 11, 0.14)` Dark, `--sel-border`: `#EA580C` / `#F59E0B`, `--sel-text`: `#9A3412` / `#FDE68A`, `--amber`: `#D97706` / `#F59E0B` — never butter-yellow `#FEF3C7`).
  - **Quantitative Market Signals**: Vivid Emerald (`--emerald`: `#059669` / `#1CE88C`, `--emerald-chart`: `#10B981` / `#1CE88C`), Stress Rose (`--rose`: `#BE123C` / `#FB7185`), and Caution (`--caution-*`, always rendered with a `1px dashed` border).
- **Zero generic SaaS blue** (`blue-*`, `indigo-*`, `sky-*`, `violet-*`, `purple-*`, `cyan-*` as UI accents).

## Goals / Non-Goals

**Goals:**
- Implement 100 % of the `:root` and `html.dark` custom properties from `docs/DESIGN.md` §6 1:1 in `frontend/app/globals.css`, verified by `globals-theme-parity.test.ts`.
- Guarantee **blur-free 60-FPS rendering with opaque solid colors** across all components and stylesheet rules, verified by `zero-blur-guard.test.ts`.
- Maintain **Zero Structural / Logic Break**: preserve all layout heights (`--topbar-height`), grids, flex/responsive breakpoints, component props, hooks, stores, and API calls.
- Sync `frontend/public/logo.svg`, `frontend/app/icon.svg`, and PWA PNG icons with repository-root `logo.svg` and align auth/login headers with `VisioTrade`.

**Non-Goals:**
- Restructuring navigation funnels, changing `TopBar` or sidebar dimensions/collapse logic, or renaming product views.
- Altering user-selectable tag/taxonomy color swatches in `frontend/lib/constants/colors.ts` (user data, explicitly exempted in `AGENTS.md`).
- Any backend, database, OpenAPI, or Docker build architecture changes.

## Decisions

### 1. Verbatim `docs/DESIGN.md` §6 Tokens + Hex-Literal Semantic Bridge in `globals.css` & `tailwind.config.ts`
- **Decision**: Declare the complete `:root` and `html.dark` custom property blocks from `docs/DESIGN.md` §6 verbatim (including uppercase hex literals), plus `--float-shadow` and semantic Tailwind bridge variables (`--background`, `--sidebar`, `--foreground`, `--card`, `--popover`, `--primary`, `--primary-foreground`, `--secondary`, `--surface-muted`, `--muted`, `--muted-foreground`, `--accent`, `--destructive`, `--warning`, `--success`, `--danger`, `--border`, `--input`, `--ring`) as hex literals, wrapped with `withAlpha(cssVar)` in `tailwind.config.ts`.
- **Rationale**: Direct 1:1 parity with `docs/DESIGN.md` §6 enforced by `globals-theme-parity.test.ts`, WCAG AA contrast on `--muted-foreground` (`--text-secondary`: `#475569` Light / `#94A3B8` Dark) and `--primary-foreground` (`#0F172A` Light / `#11141B` Dark), and working `/N` opacity modifiers across all Tailwind semantic tokens.

### 2. Three-Level Opaque Surface Hierarchy (Solid Colors)
- **Decision**:
  - `.surface-chrome`: `background-color: var(--bg-panel); border-color: var(--border-panel); box-shadow: var(--top-edge);` — used on `TopBar` and sidebars.
  - `.solid-card` (and `.radiant-card` / `.card-glossy` aliases): `border-radius: 8px; background-color: var(--bg-panel); border: 1px solid var(--border-panel); box-shadow: var(--top-edge);` — used on standalone Level-1 panels.
  - `.panel-sub`: `border-radius: 6px; background-color: var(--bg-sub); border: 1px solid var(--border-sub);` — used on Level-2 nested tiles and repeated mobile list cards (`TradeCard.tsx`, `ExecutionLegCard.tsx`, `NoteList.tsx` items).
  - `.panel-float`: `border-radius: 8px; background-color: var(--bg-panel); border: 1px solid var(--border-panel); box-shadow: var(--float-shadow);` — used on modal dialogs, popovers, dropdown menus, and `<Toaster />`.
  - `.btn-primary` & `.btn-secondary`: Directly consume `--cta-*` (Solid Amber, `1.5px` border, `font-semibold`, `6px` radius) and `--btn-sec-*` (opaque secondary control, `1px` border, `6px` radius).

### 3. Opaque Table `.wl-row` Hover, Soft-Orange Selection & Opacity-Only Dimming
- **Decision**: `.wl-row:hover` applies `background-color: var(--bg-sub)`; `.wl-row.selected` applies `background-color: var(--sel-bg); box-shadow: inset 2px 0 0 var(--amber)` (plus `tr.wl-row.selected > td:first-child { box-shadow: inset 2px 0 0 var(--amber); }` for table rows) and `.wl-row.selected .wl-ticker { color: var(--sel-text); }`; `.wl-row.dimmed` applies `opacity: 0.7` (no `filter: saturate(...)`), restoring `opacity: 1` on hover.

### 4. Canonical Logo Sync & Auth Card Alignment
- **Decision**: Keep `frontend/public/logo.svg` and `frontend/app/icon.svg` byte-identical to repository-root `logo.svg` (amber `#d97706` hexagon), regenerate `apple-touch-icon.png` and `public/icons/*.png` from `logo.svg`, and render `<Logo size={72} className="rounded-2xl" />` inside `.solid-card` on `/login`, `/register`, `/forgot-password`, and `/reset-password`.
