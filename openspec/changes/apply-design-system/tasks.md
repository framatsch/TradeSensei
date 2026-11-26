> **Execution Guardrails for Coding Agents (READ FIRST):**
> 1. **Zero Structural / Logic Break:** Do NOT change JSX element hierarchy, flex/grid layout classes, responsive visibility (`hidden`, `lg:flex`, `md:block`), props, hooks, event handlers, or API calls. Touch **only** CSS rules, `className` color/surface/border/shadow/typography tokens, and chart color constants.
> 2. **60-FPS Blur Discipline:** NEVER add `backdrop-filter` or `backdrop-blur-*` to `<tr>`, `<td>`, `TradeCard`, `ExecutionLegCard`, `NoteList` items, calendar cells, or heatmap cells.
> 3. **Preserve Existing Test Hooks:** Keep `data-testid`, `role`, `aria-*`, and semantic test-asserted classes (`text-success`, `text-danger`, `text-muted-foreground`, `border-l-warning`, `opacity-50`).

## 1. Phase 1 — Design Tokens, Theme Default, Fonts & Base Utilities (`globals.css` / `tailwind.config.ts` / `layout.tsx`)

- [x] 1.1 **File:** `frontend/app/globals.css` (lines 5–104) — Replace `:root`, `.dark`, and `body` token/base definitions with the exact `docs/DESIGN.md` tokens + semantic bridge and GPU-contained ambient orb layer
  - **Exact CSS Replacement:**
    - Replace `:root { ... }` and `.dark { ... }` with the complete verbatim `docs/DESIGN.md` custom properties + semantic Tailwind bridge:
      ```css
      :root {
        color-scheme: light;
        /* Exact docs/DESIGN.md tokens — Frosted Pearl Alabaster Glass + Hiberbee Amber-Orange */
        --canvas: #e5e8ef;
        --ink: #0f1115;
        --ink-secondary: #2d3340;
        --muted: #525966;
        --muted-dim: rgba(82, 89, 102, 0.62);

        --accent: #d97706;
        --accent-deep: #b45309;
        --accent-bright: #f59e0b;
        --accent-rgb: 217, 119, 6;
        --accent-soft: rgba(217, 119, 6, 0.12);
        --accent-border: rgba(217, 119, 6, 0.44);
        --accent-halo: 0 0 14px rgba(217, 119, 6, 0.20);

        --row-hover-bg: linear-gradient(90deg, rgba(var(--accent-rgb), 0.14) 0%, rgba(var(--accent-rgb), 0.07) 70%, rgba(var(--accent-rgb), 0.03) 100%);
        --row-hover-shadow: inset 3px 0 0 rgba(var(--accent-rgb), 0.85), inset 0 1px 0 rgba(var(--accent-rgb), 0.22), inset 0 -1px 0 rgba(var(--accent-rgb), 0.14);
        --row-hover-hairline: inset 0 1px 0 rgba(var(--accent-rgb), 0.22), inset 0 -1px 0 rgba(var(--accent-rgb), 0.14);
        --row-sel-bg: linear-gradient(90deg, rgba(var(--accent-rgb), 0.22) 0%, rgba(var(--accent-rgb), 0.12) 70%, rgba(var(--accent-rgb), 0.06) 100%);
        --row-sel-hover-bg: linear-gradient(90deg, rgba(var(--accent-rgb), 0.26) 0%, rgba(var(--accent-rgb), 0.16) 70%, rgba(var(--accent-rgb), 0.09) 100%);
        --row-sel-shadow: inset 3.5px 0 0 var(--accent), inset 0 1px 0 rgba(var(--accent-rgb), 0.36), inset 0 -1px 0 rgba(var(--accent-rgb), 0.24);
        --row-sel-hairline: inset 0 1px 0 rgba(var(--accent-rgb), 0.36), inset 0 -1px 0 rgba(var(--accent-rgb), 0.24);
        --row-ticker-sel: var(--accent-deep);
        --sidebar-hover-bg: rgba(var(--accent-rgb), 0.13);
        --sidebar-sel-bg: rgba(var(--accent-rgb), 0.17);
        --sidebar-sel-hover-bg: rgba(var(--accent-rgb), 0.21);
        --sidebar-sel-text: var(--accent-deep);

        --positive: #047857;
        --positive-rgb: 4, 120, 87;
        --positive-soft: rgba(4, 120, 87, 0.11);
        --positive-border: rgba(4, 120, 87, 0.28);
        --positive-glow: 0 2px 12px rgba(4, 120, 87, 0.14);

        --negative: #be123c;
        --negative-rgb: 190, 18, 60;
        --negative-soft: rgba(190, 18, 60, 0.11);
        --negative-border: rgba(190, 18, 60, 0.28);
        --negative-glow: 0 2px 12px rgba(190, 18, 60, 0.14);

        --caution: #a16207;
        --caution-soft: rgba(161, 98, 7, 0.09);
        --caution-border: rgba(161, 98, 7, 0.44);
        --caution-glow: 0 2px 10px rgba(161, 98, 7, 0.12);

        --glass-bg: rgba(255, 255, 255, 0.60);
        --glass-bg-strong: rgba(255, 255, 255, 0.88);
        --glass-inset: rgba(255, 255, 255, 0.44);
        --glass-border: rgba(15, 17, 21, 0.08);
        --hairline: rgba(15, 17, 21, 0.08);
        --specular: inset 0 1px 0 rgba(255, 255, 255, 0.92);
        --card-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.92), 0 10px 30px rgba(15, 23, 42, 0.065), 0 1px 3px rgba(15, 23, 42, 0.04);
        --chrome-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.90), 0 4px 18px rgba(15, 23, 42, 0.045);
        --glass-blur: blur(24px) saturate(190%);

        --cta-bg: linear-gradient(180deg, rgba(58, 64, 76, 0.86) 0%, rgba(40, 45, 55, 0.90) 100%);
        --cta-bg-hover: linear-gradient(180deg, rgba(68, 75, 90, 0.90) 0%, rgba(46, 52, 64, 0.94) 100%);
        --cta-text: #f8fafc;
        --cta-border: rgba(var(--accent-rgb), 0.48);
        --cta-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.24), 0 6px 16px rgba(30, 36, 48, 0.14), 0 0 12px rgba(var(--accent-rgb), 0.14);

        --active-pill-bg: rgba(255, 255, 255, 0.88);
        --active-pill-text: #181c24;
        --active-pill-border: rgba(var(--accent-rgb), 0.50);
        --active-pill-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.98), 0 4px 14px rgba(var(--accent-rgb), 0.16), 0 1px 3px rgba(15, 23, 42, 0.05);

        --pill-neutral-bg: rgba(255, 255, 255, 0.56);
        --pill-neutral-border: rgba(15, 17, 21, 0.09);
        --pill-neutral-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.88), 0 2px 8px rgba(15, 23, 42, 0.045);
        --track-bg: rgba(15, 17, 21, 0.055);
        --chart-grid: rgba(15, 17, 21, 0.065);

        --orb-1: rgba(245, 158, 11, 0.22);
        --orb-2: rgba(16, 185, 129, 0.18);
        --orb-3: rgba(244, 63, 94, 0.13);

        /* Semantic Tailwind bridge (WCAG AA verified) */
        --background: var(--canvas);
        --sidebar: #eef0f5;
        --foreground: var(--ink);
        --card: #f7f8fb;
        --card-foreground: var(--ink);
        --popover: #fbfcfe;
        --popover-foreground: var(--ink);
        --primary: var(--accent-deep);
        --primary-foreground: #ffffff;
        --secondary: #dde1ea;
        --secondary-foreground: var(--ink-secondary);
        --surface-muted: #dce0e8;
        --muted-foreground: var(--muted);
        --accent-foreground: #ffffff;
        --destructive: var(--negative);
        --destructive-foreground: #ffffff;
        --warning: var(--caution);
        --warning-foreground: #ffffff;
        --success: var(--positive);
        --danger: var(--negative);
        --code-fg: var(--accent-deep);
        --border: #d4d8e0;
        --input: #cfd4de;
        --ring: var(--accent);
        --radius: 0.625rem;
        --font-geist-sans: var(--font-sans);
        --font-geist-mono: var(--font-mono);
      }

      html.dark,
      .dark {
        color-scheme: dark;
        /* Exact docs/DESIGN.md tokens — Glossy Obsidian Anthracite Glass (Default) */
        --canvas: #090a0c;
        --ink: #f4f4f5;
        --ink-secondary: #d4d6dc;
        --muted: #9499a4;
        --muted-dim: rgba(148, 153, 164, 0.58);

        --accent: #f59e0b;
        --accent-bright: #fbbf24;
        --accent-deep: #d97706;
        --accent-rgb: 245, 158, 11;
        --accent-soft: rgba(245, 158, 11, 0.13);
        --accent-border: rgba(245, 158, 11, 0.48);
        --accent-halo: 0 0 14px rgba(245, 158, 11, 0.24);

        --row-hover-bg: linear-gradient(90deg, rgba(var(--accent-rgb), 0.15) 0%, rgba(var(--accent-rgb), 0.07) 60%, rgba(255, 255, 255, 0.03) 100%);
        --row-hover-shadow: inset 3px 0 0 rgba(var(--accent-rgb), 0.85), inset 0 1px 0 rgba(var(--accent-rgb), 0.22), inset 0 -1px 0 rgba(var(--accent-rgb), 0.14);
        --row-hover-hairline: inset 0 1px 0 rgba(var(--accent-rgb), 0.22), inset 0 -1px 0 rgba(var(--accent-rgb), 0.14);
        --row-sel-bg: linear-gradient(90deg, rgba(var(--accent-rgb), 0.24) 0%, rgba(var(--accent-rgb), 0.13) 65%, rgba(var(--accent-rgb), 0.06) 100%);
        --row-sel-hover-bg: linear-gradient(90deg, rgba(var(--accent-rgb), 0.28) 0%, rgba(var(--accent-rgb), 0.17) 65%, rgba(var(--accent-rgb), 0.09) 100%);
        --row-sel-shadow: inset 3.5px 0 0 var(--accent-bright), inset 0 1px 0 rgba(var(--accent-rgb), 0.42), inset 0 -1px 0 rgba(var(--accent-rgb), 0.28);
        --row-sel-hairline: inset 0 1px 0 rgba(var(--accent-rgb), 0.42), inset 0 -1px 0 rgba(var(--accent-rgb), 0.28);
        --row-ticker-sel: var(--accent-bright);
        --sidebar-hover-bg: rgba(var(--accent-rgb), 0.13);
        --sidebar-sel-bg: rgba(var(--accent-rgb), 0.20);
        --sidebar-sel-hover-bg: rgba(var(--accent-rgb), 0.24);
        --sidebar-sel-text: var(--accent-bright);

        --positive: #34d399;
        --positive-rgb: 52, 211, 153;
        --positive-soft: rgba(52, 211, 153, 0.13);
        --positive-border: rgba(52, 211, 153, 0.28);
        --positive-glow: none;

        --negative: #fb7185;
        --negative-rgb: 251, 113, 133;
        --negative-soft: rgba(251, 113, 133, 0.13);
        --negative-border: rgba(251, 113, 133, 0.28);
        --negative-glow: none;

        --caution: #eab308;
        --caution-soft: rgba(234, 179, 8, 0.10);
        --caution-border: rgba(234, 179, 8, 0.38);
        --caution-glow: none;

        --glass-bg: rgba(20, 22, 26, 0.72);
        --glass-bg-strong: rgba(20, 22, 26, 0.92);
        --glass-inset: rgba(255, 255, 255, 0.03);
        --glass-border: rgba(255, 255, 255, 0.085);
        --hairline: rgba(255, 255, 255, 0.075);
        --specular: inset 0 1px 0 rgba(255, 255, 255, 0.11);
        --card-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.11), 0 10px 30px rgba(0, 0, 0, 0.30);
        --chrome-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.09);
        --glass-blur: blur(20px) saturate(165%);

        --cta-bg: linear-gradient(180deg, rgba(48, 52, 62, 0.92) 0%, rgba(32, 35, 43, 0.94) 100%);
        --cta-bg-hover: linear-gradient(180deg, rgba(58, 63, 76, 0.95) 0%, rgba(38, 42, 52, 0.97) 100%);
        --cta-text: #f4f4f5;
        --cta-border: rgba(var(--accent-rgb), 0.50);
        --cta-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.16), 0 4px 16px rgba(var(--accent-rgb), 0.16), 0 2px 6px rgba(0, 0, 0, 0.35);

        --active-pill-bg: rgba(255, 255, 255, 0.09);
        --active-pill-text: #f4f4f5;
        --active-pill-border: rgba(var(--accent-rgb), 0.52);
        --active-pill-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.14), 0 2px 12px rgba(var(--accent-rgb), 0.16);

        --pill-neutral-bg: rgba(255, 255, 255, 0.055);
        --pill-neutral-border: rgba(255, 255, 255, 0.095);
        --pill-neutral-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
        --track-bg: rgba(255, 255, 255, 0.048);
        --chart-grid: rgba(255, 255, 255, 0.06);

        --orb-1: rgba(245, 158, 11, 0.14);
        --orb-2: rgba(52, 211, 153, 0.10);
        --orb-3: rgba(244, 63, 94, 0.10);

        /* Semantic Tailwind bridge */
        --background: var(--canvas);
        --sidebar: #0e1014;
        --foreground: var(--ink);
        --card: #14161a;
        --card-foreground: var(--ink);
        --popover: #16191f;
        --popover-foreground: var(--ink);
        --primary: var(--accent);
        --primary-foreground: #0f1115;
        --secondary: #181b21;
        --secondary-foreground: var(--ink-secondary);
        --surface-muted: #181b20;
        --muted-foreground: var(--muted);
        --accent-foreground: #0f1115;
        --destructive: var(--negative);
        --destructive-foreground: #0f1115;
        --warning: var(--caution);
        --warning-foreground: #0f1115;
        --success: var(--positive);
        --danger: var(--negative);
        --code-fg: var(--accent-bright);
        --border: #232730;
        --input: #232730;
        --ring: var(--accent);
      }
      ```
    - In `body { ... }`, remove the indigo `background-image: radial-gradient(circle at 20% 20%, rgba(99, 102, 241, 0.06) 0%, transparent 50%);` and `background-attachment: fixed;`, and set `font-family: var(--font-sans), "Inter", system-ui, -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif;`.
    - Add tabular numeric & secondary unit rules right below `body`:
      ```css
      .tnum,
      .font-mono {
        font-family: var(--font-mono), "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        font-variant-numeric: tabular-nums;
      }
      .unit-dim {
        color: var(--muted-dim);
      }
      ```
    - Add the GPU-contained, non-interactive ambient radial light-orb layer. Colors come **only** from the theme tokens `--orb-1/2/3` (Light: `0.22 / 0.18 / 0.13` — stronger; Dark: `0.14 / 0.10 / 0.10`), so both themes switch automatically without per-theme selectors:
      ```css
      .ambient-orbs {
        position: fixed;
        inset: 0;
        pointer-events: none;
        z-index: 0;
        overflow: hidden;
        contain: strict;
        filter: blur(70px);
        background:
          radial-gradient(40rem 40rem at 12% 10%, var(--orb-1), transparent 62%),          /* Top-Left amber */
          radial-gradient(38rem 38rem at 88% 90%, var(--orb-2), transparent 64%),          /* Bottom-Right emerald */
          radial-gradient(34rem 34rem at 85% 48%, var(--orb-3), transparent 65%);          /* Center-Right rose */
      }
      ```
  - **DoD:** `grep -Ei "#6366f1|#5153ba|#4f52b7|#1d4ed8|99, ?102, ?241|129, ?140, ?248" frontend/app/globals.css` returns 0 matches after Task 1.2 completes; every custom property name declared in `docs/DESIGN.md` `:root` and `html.dark` exists in **both** the `:root` and `html.dark, .dark` blocks of `globals.css` with identical values (check: `grep -oE "^\s+--[a-z0-9-]+:" docs/DESIGN.md | sort -u` ⊆ token names in `globals.css`).

- [x] 1.2 **File:** `frontend/app/globals.css` (lines 105–382) — Replace legacy Indigo component/utility classes with `docs/DESIGN.md` glass surfaces, smoked-glass buttons, `.price-pill`, `.wl-row`, dashed caution badges, and Recharts styles
  - **Exact CSS Replacement:**
    - Define inside `@layer components`:
    - **Theme rule:** every component class below MUST read colors, shadows and gradients **only** from the DESIGN.md theme tokens (`--card-shadow`, `--chrome-shadow`, `--cta-*`, `--pill-neutral-*`, `--active-pill-*`, `--track-bg`, `--row-*`, `--sidebar-*`, `--*-soft/-border/-glow`, `--chart-grid`). No hardcoded `rgba(0,0,0,…)` / `rgba(255,255,255,…)` literals, no `:root:not(.dark)` / `.dark` selectors in component rules — Light vs. Dark is switched solely by the token blocks from Task 1.1.
      - `.glass-chrome`: `background: var(--glass-bg); backdrop-filter: var(--glass-blur); -webkit-backdrop-filter: var(--glass-blur); border-color: var(--glass-border); box-shadow: var(--chrome-shadow);`
      - `.glass-card`, `.solid-card`, `.radiant-card`, `.card-glossy`: `position: relative; border-radius: 1rem; background: var(--glass-bg); backdrop-filter: var(--glass-blur); -webkit-backdrop-filter: var(--glass-blur); border: 1px solid var(--glass-border); box-shadow: var(--card-shadow);` (Light gets the soft depth shadow, Dark the obsidian shadow; keep `@apply relative overflow-hidden;` on `.solid-card` so table corners stay rounded; keep `overflow: hidden` on `.radiant-card` / `.card-glossy`).
      - `.glass-inset`: `border-radius: 0.75rem; background: var(--glass-inset); border: 1px solid var(--glass-border);` (**zero `backdrop-filter`**).
      - `.glass-float`: `border-radius: 1rem; background: var(--glass-bg-strong); backdrop-filter: var(--glass-blur); -webkit-backdrop-filter: var(--glass-blur); border: 1px solid var(--glass-border); box-shadow: var(--card-shadow);`
      - `.btn-primary`: `@apply inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium transition-all duration-150; border-radius: 0.625rem; background: var(--cta-bg); color: var(--cta-text); border: 1px solid var(--cta-border); box-shadow: var(--cta-shadow);` and `.btn-primary:hover:not(:disabled), .btn-primary:focus-visible`: `background: var(--cta-bg-hover); border-color: var(--accent); box-shadow: var(--cta-shadow), var(--accent-halo);`
      - `.btn-glass`, `.btn-ghost`: `@apply inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium transition-all duration-150; border-radius: 0.625rem; background: var(--pill-neutral-bg); color: var(--foreground); border: 1px solid var(--pill-neutral-border); box-shadow: var(--pill-neutral-shadow);` and `:hover:not(:disabled)`: `border-color: var(--accent-border); background-color: var(--accent-soft);`
      - `.btn-solid`: keep `@apply inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium transition-all duration-150; border-radius: 0.625rem; background-color: var(--foreground); color: var(--background);`
      - `.price-pill`: `@apply inline-flex items-center font-mono text-xs; font-variant-numeric: tabular-nums; border-radius: 0.4375rem; padding: 0.125rem 0.5rem; background: var(--pill-neutral-bg); border: 1px solid var(--pill-neutral-border); box-shadow: var(--pill-neutral-shadow);`
      - `.pill-active` (active filter/selector pills): `background: var(--active-pill-bg); color: var(--active-pill-text); border: 1px solid var(--active-pill-border); box-shadow: var(--active-pill-shadow); border-radius: 9999px;`
      - `.metric-toggle-bar`: `@apply inline-flex items-center gap-1 p-1 rounded-full; background: var(--track-bg); border: 1px solid var(--glass-border);`
      - `.metric-toggle-active`: `@apply relative rounded-full text-sm font-medium px-3 py-1.5 transition-all duration-150; background: var(--active-pill-bg); color: var(--active-pill-text); border: 1px solid var(--active-pill-border); box-shadow: var(--active-pill-shadow);`
      - `.metric-toggle-inactive`: `@apply relative rounded-full text-sm font-medium px-3 py-1.5 transition-all duration-150; color: var(--muted-foreground);` and `:hover`: `color: var(--foreground); background: var(--accent-soft);`
      - `.sidebar-item`: `border-radius: 0.625rem; transition: background-color 120ms ease, color 120ms ease;` with `.sidebar-item:hover`: `background-color: var(--sidebar-hover-bg); color: var(--foreground);`
      - `.nav-active` (sidebar items): `position: relative; border-radius: 0.625rem; color: var(--sidebar-sel-text); background-color: var(--sidebar-sel-bg); border: 1px solid var(--accent-border);` with `.nav-active:hover { background-color: var(--sidebar-sel-hover-bg); }` and `.nav-active::before` changed from `background-color: #6366f1; box-shadow: 0 0 8px rgba(129, 140, 248, 0.5);` to `background-color: var(--accent); box-shadow: var(--accent-halo);`
      - `.wl-row` interaction contract (zero `backdrop-filter`, zero layout shift):
        ```css
        .wl-row {
          border-bottom: 1px solid var(--hairline);
          transition: background 120ms ease, opacity 120ms ease, filter 120ms ease;
        }
        .wl-row:hover {
          background: var(--row-hover-bg);
        }
        /* <tr>: continuous top/bottom hairlines across cells + 3px/3.5px left bar on first cell */
        tr.wl-row:hover > td {
          box-shadow: var(--row-hover-hairline);
        }
        tr.wl-row:hover > td:first-child,
        .wl-row:not(tr):hover {
          box-shadow: var(--row-hover-shadow);
        }
        .wl-row.selected {
          background: var(--row-sel-bg);
        }
        .wl-row.selected:hover {
          background: var(--row-sel-hover-bg);
        }
        tr.wl-row.selected > td {
          box-shadow: var(--row-sel-hairline);
        }
        tr.wl-row.selected > td:first-child,
        .wl-row:not(tr).selected {
          box-shadow: var(--row-sel-shadow);
        }
        .wl-row.selected .wl-ticker {
          color: var(--row-ticker-sel);
        }
        .wl-focus-dot {
          width: 6px;
          height: 6px;
          border-radius: 9999px;
          background-color: var(--accent);
          box-shadow: var(--accent-halo);
        }
        .wl-row.dimmed {
          opacity: 0.48;
          filter: saturate(0.35);
        }
        .wl-row.dimmed:hover {
          opacity: 1;
          filter: saturate(1);
        }
        ```
      - Semantic signal badges & surfaces:
        ```css
        .badge-positive {
          background-color: var(--positive-soft);
          color: var(--positive);
          border: 1px solid var(--positive-border);
          box-shadow: var(--positive-glow);
        }
        .badge-negative {
          background-color: var(--negative-soft);
          color: var(--negative);
          border: 1px solid var(--negative-border);
          box-shadow: var(--negative-glow);
        }
        .badge-caution {
          background-color: var(--caution-soft);
          color: var(--caution);
          border: 1px dashed var(--caution-border);
          box-shadow: var(--caution-glow);
        }
        .badge-neutral {
          background-color: var(--pill-neutral-bg);
          color: var(--muted-foreground);
          border: 1px solid var(--pill-neutral-border);
        }
        .surface-caution {
          background-color: var(--caution-soft);
          border: 1px dashed var(--caution-border);
          box-shadow: var(--caution-glow);
          color: var(--caution);
        }
        ```
    - In `@layer utilities`: change `.glow-primary` from `rgba(99, 102, 241, 0.15)` to `var(--accent-halo)`; remove the duplicate `.glass-card` definition in `@layer utilities` (now in `@layer components`).
    - In `.radiant-table tbody tr:hover`: update to `background: var(--row-hover-bg);`.
    - In Recharts rules (lines 371–382): set `.recharts-cartesian-grid-horizontal line, .recharts-cartesian-grid-vertical line` to `stroke: var(--chart-grid); stroke-opacity: 1; stroke-dasharray: 3 3;` and `.recharts-tooltip-wrapper .recharts-default-tooltip` to `background: var(--glass-bg-strong) !important; backdrop-filter: var(--glass-blur); border: 1px solid var(--glass-border) !important; border-radius: 0.75rem !important; box-shadow: var(--card-shadow) !important;`.
  - **DoD:** `grep -Ei "#6366f1|#5153ba|#4f52b7|99, ?102, ?241|129, ?140, ?248" frontend/app/globals.css` outputs nothing; `grep -nE "rgba\((0, ?0, ?0|255, ?255, ?255)" frontend/app/globals.css` matches only lines inside the `:root` / `html.dark, .dark` token blocks.

- [x] 1.3 **File:** `frontend/tailwind.config.ts` — Enable `/N` alpha modifiers on all semantic CSS-variable colors (`muted.DEFAULT` → `--surface-muted`), update font stacks (`Inter` + `IBM Plex Mono`), and align `borderRadius`
  - **Exact Code Replacement:**
    - Add helper above `const config: Config`:
      ```ts
      const withAlpha =
        (cssVar: string) =>
        ({ opacityValue }: { opacityValue?: string }) =>
          opacityValue === undefined
            ? `var(${cssVar})`
            : `color-mix(in srgb, var(${cssVar}) calc(${opacityValue} * 100%), transparent)`;
      ```
    - Replace `fontFamily` with:
      ```ts
      fontFamily: {
        sans: ["var(--font-sans)", "Inter", "system-ui", "-apple-system", "Segoe UI", "Helvetica Neue", "Arial", "sans-serif"],
        mono: ["var(--font-mono)", "IBM Plex Mono", "ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      ```
    - Replace every `"var(--...)"` entry inside `theme.extend.colors` with `withAlpha("--...")`, mapping `muted.DEFAULT` to `withAlpha("--surface-muted")` and `muted.foreground` to `withAlpha("--muted-foreground")`, plus adding `caution: withAlpha("--caution")`, `positive: withAlpha("--positive")`, `negative: withAlpha("--negative")`.
  - **DoD:** Run `cd frontend && npx tsc --noEmit` with 0 errors.

- [x] 1.4 **Files:** `frontend/app/layout.tsx`, `frontend/app/providers.tsx`, `frontend/app/manifest.ts`, `frontend/jest.config.js`, `frontend/__mocks__/nextFontGoogleMock.js` — Configure `Inter` + `IBM_Plex_Mono`, set Obsidian Dark (`defaultTheme="dark"`), render `<div className="ambient-orbs" aria-hidden="true" />`, and update theme colors to `#090a0c`
  - **Exact Code Replacement:**
    - In `frontend/app/layout.tsx`:
      - Replace `import localFont from "next/font/local";` and `geistSans` / `geistMono` with:
        ```tsx
        import { Inter, IBM_Plex_Mono } from "next/font/google";

        const inter = Inter({
          subsets: ["latin"],
          weight: ["400", "500", "600", "700"],
          variable: "--font-sans",
          display: "swap",
        });
        const ibmPlexMono = IBM_Plex_Mono({
          subsets: ["latin"],
          weight: ["400", "500", "600", "700"],
          variable: "--font-mono",
          display: "swap",
        });
        ```
      - Update `viewport.themeColor` from `"#131317"` to `"#090a0c"`.
      - Update `<body className=...>` to `${inter.variable} ${ibmPlexMono.variable} antialiased min-h-[100dvh] bg-background text-foreground relative`.
      - Change `<ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>` to `<ThemeProvider attribute="class" defaultTheme="dark" enableSystem disableTransitionOnChange>` (Dark is the default for new sessions; the existing Light / Dark / System choice in `GeneralSettings.tsx` MUST keep working — do NOT remove the Light option).
    - In `frontend/components/settings/GeneralSettings.tsx` line 151: replace `setTheme(settings.theme ?? "system")` → `setTheme(settings.theme ?? "dark")` so users without a stored preference land on the Obsidian default.
      - Inside `<Providers>`, insert `<div className="ambient-orbs" aria-hidden="true" />` right before `<PwaRegistrar />`, wrap `{children}` as `<div className="relative z-10">{children}</div>`, and pass `toastOptions={{ className: "glass-float !bg-[var(--glass-bg-strong)] !text-foreground !border !border-[var(--glass-border)]" }}` to `<Toaster position="bottom-right" />`.
    - In `frontend/app/providers.tsx`: remove the duplicate nested `<ThemeProvider attribute="class" defaultTheme="system" enableSystem>` wrapper (and its unused `import { ThemeProvider } from "next-themes";`), returning `<QueryClientProvider client={queryClient}>{children}</QueryClientProvider>` directly so `app/layout.tsx` is the single `ThemeProvider`.
    - In `frontend/app/manifest.ts`: replace `background_color: "#0a0a14"` and `theme_color: "#131317"` with `background_color: "#090a0c"` and `theme_color: "#090a0c"`.
    - Create `frontend/__mocks__/nextFontGoogleMock.js` exporting `new Proxy({}, { get: () => () => ({ className: "mock-font", variable: "--mock-font", style: { fontFamily: "mock" } }) })` and map `"^next/font/google$": "<rootDir>/__mocks__/nextFontGoogleMock.js"` in `frontend/jest.config.js` `moduleNameMapper`.
  - **DoD:** `cd frontend && npx tsc --noEmit && npx jest __tests__/components/settings/GeneralSettings.test.tsx` exits 0.

## 2. Phase 2 — Global Chrome Containers, Sidebars, Sub-Tabs & Action Buttons

- [x] 2.1 **Files:** `frontend/components/layout/TopBar.tsx`, `frontend/app/dashboard/layout.tsx` — Apply `.glass-chrome`, `.sidebar-item` (`--sidebar-hover-bg`), Hiberbee Amber active sidebar states, and remove `text-slate-500` without changing `--topbar-height`
  - **Exact Class Replacement:**
    - `frontend/components/layout/TopBar.tsx` line 59: replace `h-[var(--topbar-height,3.5rem)] w-full border-b border-border bg-sidebar z-40` → `h-[var(--topbar-height,3.5rem)] w-full border-b glass-chrome z-40` (keep `3.5rem` height unchanged).
    - `frontend/app/dashboard/layout.tsx`:
      - Line 208 (`SECTION_HEADER_CLASS`): replace `text-slate-500` → `text-muted-foreground`.
      - Line 211 (`L1_INACTIVE`): replace `"rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/60"` → `"sidebar-item text-muted-foreground"`.
      - Line 431 (`<aside>`): replace `bg-sidebar border-border` → `glass-chrome` (keeping all `w-56`, `translate-x-*`, `lg:w-56`, `lg:border-r`, `overflow-hidden` responsive classes and `--topbar-height` untouched!).
      - Line 477 (`<main>`): replace `bg-background text-foreground` → `bg-transparent text-foreground` so the ambient orb canvas softly illuminates glass cards through the shell.
  - **DoD:** `grep -rn "text-slate-500" frontend/app/dashboard/layout.tsx frontend/components/layout/TopBar.tsx` returns 0 matches; `npx jest __tests__/components/layout` passes.

- [x] 2.2 **Files:** `frontend/components/workspace/WorkspaceSidebarNav.tsx`, `frontend/components/trading-log/TradingLogSidebar.tsx`, `frontend/components/checkin/CheckinSidebar.tsx`, `frontend/components/analytics/AnalyticsLayout.tsx` — Unify contextual sidebars and sub-navigation rails on `.glass-chrome` / `.nav-active` / `.sidebar-item` and remove remaining `text-slate-500`
  - **Exact Class Replacement:**
    - `WorkspaceSidebarNav.tsx`: line 30 replace `const ACTIVE_CLASS = "text-primary bg-primary/10 font-medium rounded-lg";` → `const ACTIVE_CLASS = "font-medium";`; line 31 replace `const INACTIVE_CLASS = "text-muted-foreground hover:text-foreground hover:bg-muted/60 rounded-lg";` → `const INACTIVE_CLASS = "sidebar-item text-muted-foreground";`; line 32 replace `text-slate-500` → `text-muted-foreground`.
    - `TradingLogSidebar.tsx`: line 52 (`SECTION_HEADER_CLASS`) replace `text-slate-500` → `text-muted-foreground`; line 53 (`NAV_ITEM_CLASS`) replace `hover:text-foreground hover:bg-muted/60` → `sidebar-item`; line 65 replace `"text-foreground font-medium bg-muted/40"` → `"nav-active font-medium"` and `"text-muted-foreground hover:text-foreground hover:bg-muted/20"` → `"sidebar-item text-muted-foreground"`; line 85 replace `bg-sidebar` → `glass-chrome`.
    - `CheckinSidebar.tsx` line 32 (`SECTION_HEADER_CLASS`): replace `text-slate-500` → `text-muted-foreground`; if root container has `bg-sidebar`, replace with `glass-chrome`.
    - `AnalyticsLayout.tsx` line 100: replace `bg-muted/20` → `bg-transparent`; lines 115–116: replace `"bg-primary/20 text-foreground"` → `"nav-active font-medium"` and `"text-muted-foreground hover:text-foreground hover:bg-muted/50"` → `"sidebar-item text-muted-foreground"`.
  - **DoD:** `grep -rn "text-slate-" frontend/app frontend/components` returns 0 matches.

- [x] 2.3 **Files:** `frontend/components/layout/BentoMenu.tsx`, `frontend/components/layout/PortfolioSwitcher.tsx`, `frontend/components/layout/UserBadge.tsx` — Upgrade TopBar floating menus to `.glass-float` and remove `dark:` / `red-*` in `UserBadge`
  - **Exact Class Replacement:**
    - `BentoMenu.tsx` line 54: replace `bg-popover border border-border rounded-md shadow-md text-popover-foreground` → `glass-float text-popover-foreground`.
    - `PortfolioSwitcher.tsx` (`DropdownMenu.Content`): replace `bg-popover border border-border rounded-md shadow-md` (or `shadow-lg`) → `glass-float`.
    - `UserBadge.tsx`: line 78: replace `bg-popover border border-border rounded-md shadow-md text-popover-foreground` → `glass-float text-popover-foreground`; line 117: replace `text-red-600 dark:text-red-400 rounded-sm outline-none cursor-pointer hover:bg-red-500/10 focus:bg-red-500/10` → `text-danger rounded-md outline-none cursor-pointer hover:bg-danger/10 focus:bg-danger/10`.
  - **DoD:** `grep -n "dark:\|red-" frontend/components/layout/UserBadge.tsx` returns 0 matches.

- [x] 2.4 **Files:** `frontend/components/broker/ConnectSchwabButton.tsx`, `frontend/components/trades/BulkActionToolbar.tsx`, `frontend/components/trades/SaveFilterModal.tsx`, `frontend/components/trades/TradeForm.tsx`, `frontend/components/imports/ImportForm.tsx`, `frontend/components/auth/GoogleSignInButton.tsx`, `frontend/components/auth/OIDCSignInButton.tsx` — Standardize stray hardcoded action buttons onto `.btn-primary` / `.btn-glass`
  - **Exact Class Replacement:**
    - `ConnectSchwabButton.tsx`: line 53 replace `px-4 py-2 bg-primary hover:bg-primary/90 active:bg-blue-800 text-white text-sm font-medium rounded-lg transition-colors` → `btn-primary`; line 56 replace `bg-white/20` → `bg-primary/20 text-primary`.
    - `BulkActionToolbar.tsx`: line 55 replace `px-3 py-1.5 bg-[#6063dd] hover:opacity-90 text-white rounded-md text-sm transition-colors` → `btn-primary px-3 py-1.5 text-sm`; lines 65 & 73 replace `px-3 py-1.5 bg-zinc-200 dark:bg-zinc-600 hover:bg-zinc-500 text-foreground rounded-md text-sm transition-colors` → `btn-glass px-3 py-1.5 text-sm`.
    - `SaveFilterModal.tsx`: line 80 replace `rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700` → `btn-glass`; line 87 replace `rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50` → `btn-primary disabled:opacity-50`.
    - `TradeForm.tsx` line 868: replace `px-4 py-2 text-sm text-muted-foreground bg-secondary hover:bg-zinc-200 dark:bg-zinc-600 disabled:opacity-50 rounded-md transition-colors` → `btn-glass disabled:opacity-50`.
    - `ImportForm.tsx`: lines 467 & 661 replace `border-zinc-400 accent-amber-500` → `border-border accent-primary`; line 673 replace `px-5 py-2.5 bg-zinc-700 hover:bg-zinc-600 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium rounded-md text-sm transition-colors` → `btn-primary px-5 py-2.5 disabled:opacity-60 disabled:cursor-not-allowed`.
    - `GoogleSignInButton.tsx` (line 74) & `OIDCSignInButton.tsx` (line 34): replace `bg-white hover:bg-gray-50 active:bg-gray-100 text-gray-700 font-medium rounded-md border border-gray-300` → `btn-glass w-full py-2.5`.
  - **DoD:** `grep -En "blue-800|blue-600|#6063dd|bg-zinc-700|bg-zinc-200|text-gray-700" frontend/components/broker/ConnectSchwabButton.tsx frontend/components/trades/BulkActionToolbar.tsx frontend/components/trades/SaveFilterModal.tsx frontend/components/trades/TradeForm.tsx frontend/components/imports/ImportForm.tsx frontend/components/auth/GoogleSignInButton.tsx frontend/components/auth/OIDCSignInButton.tsx` returns 0 matches.

## 3. Phase 3 — Tables, Mobile List Cards & `.wl-row` Interaction Contracts (60-FPS Safe)

- [x] 3.1 **Files:** `frontend/components/trades/TradeRow.tsx`, `frontend/components/trades/TradeTable.tsx` — Apply `.wl-row`, `.selected` + `.wl-ticker` + `.wl-focus-dot`, `.tnum` on numeric columns, and remove `blue-900` / `zinc-*` / `dark:*`
  - **Exact Class Replacement:**
    - `TradeRow.tsx`:
      - Lines 82–83 (`LONG` / `SHORT` direction badge): replace `"bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800"` → `"badge-positive"` and `"bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400 border border-red-200 dark:border-red-800"` → `"badge-negative"`.
      - Line 100 (`<tr>`): replace `className="border-b border-border hover:bg-secondary/30 transition-colors cursor-pointer"` → `className={`wl-row cursor-pointer ${isSelected ? "selected" : ""}`}`.
      - Line 107 (checkbox): replace `border-border dark:border-border` → `border-border`.
      - Line 112–116 (symbol cell): add `wl-ticker` to the symbol `<Link>` `className` (`"wl-ticker hover:text-primary transition-colors"`) and render `{isSelected && <span className="wl-focus-dot shrink-0" aria-hidden="true" />}` inside the `inline-flex items-center gap-1.5` wrapper.
      - Numeric cells (quantity, entry price, exit price, P&L, return %, dates on lines 150–170): ensure `font-mono` (or `tnum`) is present on numeric/date `<td>` or `<span>` elements without altering text content.
      - Line 189 (quick tag button): replace `hover:bg-blue-900/20` → `hover:bg-primary/10`.
      - Line 210 (expanded quick-note row): replace `bg-zinc-50/30 dark:bg-zinc-900/30` → `bg-[var(--glass-inset)]`.
  - **DoD:** `grep -En "dark:|zinc-|emerald-|red-|blue-" frontend/components/trades/TradeRow.tsx` returns 0 matches; `npx jest __tests__/components/trades` passes.

- [x] 3.2 **Files:** `frontend/components/trades/ExecutionRow.tsx`, `frontend/components/trades/ExecutionLegsTable.tsx`, `frontend/components/trades/ExecutionSummaryCard.tsx`, `frontend/components/trades/TradePickerModal.tsx` — Apply `.wl-row` / `.dimmed` / `.selected` and dashed caution conflict border across trade execution tables & trade picker
  - **Exact Class Replacement:**
    - `ExecutionRow.tsx`:
      - Line 139 (deleted row): replace `className="border-b border-border opacity-50"` → `className="wl-row dimmed opacity-50"` (preserving `opacity-50`).
      - Line 229–231: replace `hover:bg-[color-mix(in_srgb,var(--muted)_30%,transparent)]` → `wl-row`, and for `isConflict` replace `"bg-[color-mix(in_srgb,var(--warning)_10%,transparent)] border-l-[3px] border-l-warning hover:bg-[color-mix(in_srgb,var(--warning)_20%,transparent)]"` → `"surface-caution border-l-[3px] border-l-warning"`.
    - `ExecutionSummaryCard.tsx` line 226: add `wl-row` to summary `<tbody>` `<tr>` rows.
    - `TradePickerModal.tsx`:
      - Line 143 (selectable list item): replace `isSelected ? "bg-[#6063dd]/5" : ""` → `wl-row ${isSelected ? "selected" : ""}` (removing generic hover clash).
      - Line 150 (selection indicator): replace `"bg-[#6063dd] border-[#6063dd]"` → `"bg-primary border-primary text-primary-foreground"`.
      - Lines 174–175 (`LONG`/`SHORT` badge): replace `emerald-*`/`red-*` `dark:*` strings with `"badge-positive"` and `"badge-negative"`.
      - Lines 194–195 (P&L text): replace `"text-emerald-500 dark:text-emerald-400"` / `"text-red-500 dark:text-red-400"` → `"text-success"` / `"text-danger"`.
      - Line 224 (confirm button): replace `rounded-md bg-[#6063dd] px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50 transition-colors` → `btn-primary disabled:opacity-50`.
  - **DoD:** `grep -En "#6063dd|dark:|emerald-|red-" frontend/components/trades/ExecutionRow.tsx frontend/components/trades/TradePickerModal.tsx` returns 0 matches.

- [x] 3.3 **Files:** `frontend/components/accounts/AccountList.tsx`, `frontend/components/playbooks/PlaybookList.tsx`, `frontend/components/settings/CheckinSettings.tsx`, `frontend/components/settings/CorporateActionsSettings.tsx`, `frontend/components/settings/TokenList.tsx`, `frontend/app/dashboard/workspace/correlation/page.tsx`, `frontend/components/analytics/PerformanceAnalysisDashboard.tsx` — Apply `.wl-row` to all remaining data tables and remove hardcoded `#dadbdf`/`#29292b`/`zinc-500`/`white/[0.05]`
  - **Exact Class Replacement:**
    - `AccountList.tsx` (~line 170): replace `border-b border-border/50 hover:bg-secondary/30 transition-colors` → `wl-row`.
    - `PlaybookList.tsx` (~line 417): replace `border-b border-border hover:bg-secondary/30 transition-colors cursor-pointer` → `wl-row cursor-pointer`.
    - `CheckinSettings.tsx` (line 174) & `CorporateActionsSettings.tsx` (line 478): replace `bg-card hover:bg-muted/50 transition-colors` → `wl-row`; in `CheckinSettings.tsx` line 50, `FeaturesSettings.tsx` lines 117 & 149, `GeneralSettings.tsx` line 263, `AnnotationInputs.tsx` line 82, and `TradeForm.tsx` line 515: keep switch thumb neutral crisp (`bg-foreground` or `bg-[#f4f4f5]` without `dark:` / `gray-300`, replacing `after:border-gray-300 after:bg-white` → `after:border-border after:bg-[#f4f4f5]`).
    - `TokenList.tsx` (line 83): add `className="wl-row"` to `<tr key={token.id}>` and `font-mono` to date `<td>` cells.
    - `app/dashboard/workspace/correlation/page.tsx` (line 271): replace `hover:bg-muted/50 transition-colors` → `wl-row`.
    - `PerformanceAnalysisDashboard.tsx`:
      - Replace all 19 occurrences of `text-zinc-500` → `text-muted-foreground`.
      - Replace all 12 occurrences of `border-[#dadbdf] dark:border-[#29292b]` → `border-border` and `divide-[#dadbdf] dark:divide-[#29292b]` → `divide-border`.
      - Line 318 (`<tr>`): replace ``className={`transition-colors ${onViewReport ? "cursor-pointer hover:bg-white/[0.05]" : "hover:bg-white/[0.03]"}`}`` → ``className={`wl-row ${onViewReport ? "cursor-pointer" : ""}`}``.
  - **DoD:** `grep -En "zinc-500|#dadbdf|#29292b|hover:bg-white" frontend/components/analytics/PerformanceAnalysisDashboard.tsx` returns 0 matches.

- [x] 3.4 **Files:** `frontend/components/trades/TradeCard.tsx`, `frontend/components/trades/ExecutionLegCard.tsx`, `frontend/components/notes/NoteList.tsx` — Enforce **60-FPS Blur Discipline** on repeated list items by switching from `.solid-card` / `zinc-*` to blur-free `.glass-inset`
  - **Exact Class Replacement:**
    - `TradeCard.tsx`: replace `solid-card` on the repeated `<article>` / card root with `glass-inset wl-row` (preserving `text-success`, `text-danger`, `text-muted-foreground` asserted in `TradeCard.test.tsx`).
    - `ExecutionLegCard.tsx`: replace `solid-card` on `<article>` with `glass-inset` (preserving `border-l-warning`, `opacity-50`, `text-success`, `text-danger` asserted in `ExecutionLegCard.test.tsx`).
    - `NoteList.tsx`: line 159 replace `bg-zinc-50 dark:bg-zinc-900/60 border border-blue-400 dark:border-blue-600 rounded-xl` → `glass-inset border-primary/50`; line 199 replace `bg-zinc-50 dark:bg-zinc-900/60 border border-border rounded-xl` → `glass-inset`.
  - **DoD:** `npx jest __tests__/components/trades/TradeCard.test.tsx __tests__/components/trades/ExecutionLegCard.test.tsx` exits 0; `grep -n "backdrop-blur\|solid-card" frontend/components/trades/TradeCard.tsx frontend/components/trades/ExecutionLegCard.tsx` returns 0 matches.

## 4. Phase 4 — Focus vs. Market Signal Separation, Badges, Banners & Zero SaaS Blue

- [x] 4.1 **Files:** `frontend/components/trades/ExecutionStatusBadge.tsx`, `frontend/components/settings/PortfoliosBrokersHub.tsx`, `frontend/components/notes/NoteList.tsx`, `frontend/app/dashboard/trades/[id]/page.tsx` — Eliminate all `blue-*`, `indigo-*`, `violet-*`, `cyan-*`, `sky-*`, `purple-*` badges and apply `.badge-neutral` / `.badge-caution` (`1px dashed`) / `.badge-positive` / `.badge-negative`
  - **Exact Class Replacement:**
    - `ExecutionStatusBadge.tsx` (lines 62–90):
      - `Edited` (`origin === "imported" && userModified`): replace `"bg-amber-100 text-amber-700 border border-amber-200"` → `"badge-caution"` (1px dashed ochre).
      - `Imported`, `Manual`, `Merged`, `Split` / `Split Child`: replace `"bg-blue-100 ..."`, `"bg-violet-100 ..."`, `"bg-orange-100 ..."`, `"bg-cyan-100 ..."` → `"badge-neutral"`.
    - `PortfoliosBrokersHub.tsx` (lines 40–42 `BROKER_TYPE_BADGES`): replace `ibkr` (`indigo-*`) and `schwab` (`blue-*`) → `"badge-neutral"`.
    - `NoteList.tsx`:
      - Lines 36–45 (`EMOTION_COLORS`): map positive/Composed emotions (`confident`, `disciplined`, `calm`) → `"badge-positive"`, caution/arousal emotions (`anxious`, `excited`) → `"badge-caution"`, negative/stress emotions (`fearful`, `greedy`, `frustrated`, `regretful`) → `"badge-negative"`.
      - Lines 165 & 170: replace `border-border dark:border-border bg-white dark:bg-background text-sm text-zinc-800 dark:text-foreground` → `border-border bg-[var(--glass-inset)] text-sm text-foreground`.
      - Line 205: replace `hover:bg-blue-900/20` → `hover:bg-primary/10`.
    - `app/dashboard/trades/[id]/page.tsx`:
      - Lines 67–68, 557–558, 594–595: replace `"text-emerald-500 dark:text-emerald-400"` → `"text-success"` and `"text-red-500 dark:text-red-400"` → `"text-danger"`.
      - Lines 385–386: replace `emerald-*` / `red-*` `dark:*` badge strings → `"badge-positive"` / `"badge-negative"`.
      - Line 412 (`Manually Edited` badge): replace `bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-400 border border-violet-200 dark:border-violet-800` → `badge-caution`.
      - Lines 419–420 (status badge): replace `amber-*` `dark:*` → `"badge-caution"` and `zinc-*` `dark:*` → `"badge-neutral"`.
      - Line 475 (warning banner): replace `border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900` → `surface-caution px-4 py-3 text-sm`.
  - **DoD:** `grep -En "blue-|indigo-|violet-|cyan-|sky-|purple-|dark:" frontend/components/trades/ExecutionStatusBadge.tsx frontend/components/settings/PortfoliosBrokersHub.tsx frontend/components/notes/NoteList.tsx "frontend/app/dashboard/trades/[id]/page.tsx"` returns 0 matches; `npx jest __tests__/app/dashboard/trades/TradeDetailPage.test.tsx` passes.

- [x] 4.2 **Files:** `frontend/components/trades/ConflictBanner.tsx`, `frontend/components/ui/InsufficientDataBanner.tsx`, `frontend/components/trades/CorrectTradeModal.tsx`, `frontend/components/trades/MergePreviewModal.tsx` — Apply `.surface-caution` (`1px dashed` border) and replace `#6063dd` modal CTAs with `.btn-primary`
  - **Exact Class Replacement:**
    - `ConflictBanner.tsx` (lines 33–52): replace `border bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800` → `surface-caution`; replace `text-amber-600 dark:text-amber-400`, `text-amber-800 dark:text-amber-300`, `text-amber-700 dark:text-amber-400` → `text-warning` (and `text-foreground` for the bold heading).
    - `InsufficientDataBanner.tsx` (lines 55, 75): replace `border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-700 dark:text-amber-300` → `surface-caution px-4 py-3 text-sm`; replace `text-amber-600/90 dark:text-amber-400/90` → `text-muted-foreground`.
    - `CorrectTradeModal.tsx`: lines 80–92 replace `amber-*` `dark:*` banner classes with `surface-caution` / `text-warning`; line 156 replace `rounded-md bg-[#6063dd] px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50 transition-colors` → `btn-primary disabled:opacity-50`.
    - `MergePreviewModal.tsx`: lines 45–46 replace `emerald-500`/`red-500` `dark:*` → `text-success`/`text-danger`; lines 57–58 replace `emerald-100`/`red-100` `dark:*` → `badge-positive`/`badge-negative`; lines 115–117 replace `amber-*` `dark:*` warning box → `surface-caution` / `text-warning`; lines 141–142 replace `border-[#6063dd]/30 bg-[#6063dd]/5` and `text-[#6063dd]` → `glass-inset` and `text-primary`; line 179 replace `rounded-md bg-[#6063dd] ...` → `btn-primary disabled:opacity-50`.
  - **DoD:** `grep -En "#6063dd|dark:|amber-" frontend/components/trades/ConflictBanner.tsx frontend/components/ui/InsufficientDataBanner.tsx frontend/components/trades/CorrectTradeModal.tsx frontend/components/trades/MergePreviewModal.tsx` returns 0 matches.

- [x] 4.3 **Files:** `frontend/components/imports/FileQueue.tsx`, `frontend/components/imports/DateRangeVisualizer.tsx`, `frontend/components/trades/MediaChartsCard.tsx` — Replace remaining `blue-*` spinners, progress bars, dropzones, and `zinc-*`/`dark:*` classes with Hiberbee Amber focus tokens
  - **Exact Class Replacement:**
    - `FileQueue.tsx`: line 51 replace `border-blue-400` → `border-primary`; line 91 replace `bg-blue-500` → `bg-primary`.
    - `DateRangeVisualizer.tsx`: lines 137 & 157 replace `bg-zinc-50 dark:bg-zinc-700 text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-600` → `bg-secondary text-muted-foreground hover:text-foreground hover:bg-muted`; line 183 replace `bg-gradient-to-r from-blue-500 to-blue-400` → `bg-primary`; line 187 replace `bg-zinc-400 dark:bg-zinc-500` → `bg-muted-foreground`; lines 202 & 207 replace `bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400` → `badge-caution` and `text-amber-500 dark:text-amber-400` → `text-warning`.
    - `MediaChartsCard.tsx`:
      - Line 119: replace `bg-zinc-100/40 dark:bg-zinc-900/40` → `bg-[var(--glass-inset)]`.
      - Line 128: replace `border-border dark:border-border bg-card text-xs text-zinc-800 dark:text-foreground` → `border-border bg-[var(--glass-inset)] text-xs text-foreground`.
      - Lines 140, 147, 164, 176, 188, 296, 303, 304, 306, 354, 408, 409: replace all `text-zinc-*` / `hover:text-zinc-*` / `dark:hover:text-zinc-*` / `dark:border-border` / `dark:text-primary` → `text-muted-foreground`, `hover:text-foreground`, `border-border`, `text-primary`.
      - Lines 276–279 (dropzone states): replace `"border-primary bg-blue-50 dark:bg-blue-900/20"` → `"border-primary bg-primary/10"`, `"border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20"` → `"border-success bg-success/10"`, and `"border-border dark:border-border hover:border-blue-400 hover:bg-zinc-50 dark:hover:bg-zinc-700/40"` → `"border-border hover:border-primary/60 hover:bg-[var(--glass-inset)]"`.
      - Line 417 (count pill): replace `bg-blue-100 dark:bg-blue-900/50 text-primary dark:text-primary` → `bg-primary/15 text-primary font-mono`.
  - **DoD:** `grep -En "blue-|zinc-|dark:" frontend/components/imports/FileQueue.tsx frontend/components/imports/DateRangeVisualizer.tsx frontend/components/trades/MediaChartsCard.tsx` returns 0 matches; `npx jest __tests__/components/trades/MediaChartsCard.test.tsx` passes.

## 5. Phase 5 — Charts, Heatmaps, Calendar Signals & Tabular Numerals

- [x] 5.1 **Files:** `frontend/lib/constants.ts`, `frontend/components/charts/RollingWinrateChart.tsx`, `frontend/components/charts/CoOccurrenceHeatmap.tsx`, `frontend/components/analytics/PerformanceAnalysisDashboard.tsx`, `frontend/components/reporting/Widgets.tsx`, `frontend/components/charts/TradeChart.tsx` — Replace Violet/Indigo/Blue chart series & heatmap colors with Hiberbee Amber / Market Signal tokens
  - **Exact Code / Class Replacement:**
    - `lib/constants.ts` (lines 28–39 `CHART_COLORS`):
      - Replace `tooltip.bg: "var(--card)"` → `"var(--glass-bg-strong)"`, `tooltip.border: "var(--border)"` → `"var(--glass-border)"`.
      - Replace `primary: "#8b5cf6"` → `primary: "var(--accent)"`, `success: "var(--positive)"`, `danger: "var(--negative)"`, `warning: "var(--caution)"`.
    - `RollingWinrateChart.tsx`: line 95 replace `"bg-secondary text-muted-foreground hover:text-foreground hover:bg-zinc-200 dark:bg-zinc-600"` → `"bg-secondary text-muted-foreground hover:text-foreground hover:bg-muted"`; lines 155 & 158 replace `"#3b82f6"` → `"var(--accent)"`.
    - `CoOccurrenceHeatmap.tsx`: line 103 replace ``fill={`rgba(59, 130, 246, ${opacity * 0.8 + 0.05})`}`` → ``fill={`rgba(var(--accent-rgb), ${opacity * 0.78 + 0.06})`}``; line 105 replace `hover:fill-blue-500` → `hover:opacity-90`; ensure tile radius matches `7px` (`rx={7}`).
    - `PerformanceAnalysisDashboard.tsx` line 204: replace `let fill = '#6366F1'; // Default Indigo` → `let fill = 'var(--accent)';` and lines 206/208 replace `'#34d399'` / `'#fb7185'` / `'#F59E0B'` → `'var(--positive)'` / `'var(--negative)'` / `'var(--caution)'`.
    - `reporting/Widgets.tsx` (lines 515–523 `HEATMAP_COLORS`): replace Indigo ramp (`#f3f4f6` … `#4338ca`) with achromatic-to-Hiberbee-Amber ramp: `["rgba(var(--accent-rgb), 0.05)", "rgba(var(--accent-rgb), 0.14)", "rgba(var(--accent-rgb), 0.26)", "rgba(var(--accent-rgb), 0.40)", "rgba(var(--accent-rgb), 0.56)", "rgba(var(--accent-rgb), 0.74)", "rgba(var(--accent-rgb), 0.92)"]`.
    - `TradeChart.tsx`: line 285 replace `text-zinc-400` → `text-muted-foreground`; lines 311–315 (skeleton) replace `bg-zinc-700/50`, `bg-zinc-700/30`, `bg-zinc-800/40` → `bg-muted/60`, `bg-muted/40`, `bg-[var(--glass-inset)]`; line 1017 replace `hidden dark:block` → `block`; replace candlestick entry marker `#00d2ff` (cyan) if styled as accent with `#34d399` (emerald positive) or keep only if tested — check `grep -rn "00d2ff" frontend/__tests__`: if untested, update `#00d2ff` → `#34d399` so zero cyan remains.
  - **DoD:** `grep -Ein "#8b5cf6|#3b82f6|#6366f1|#4338ca|59, ?130, ?246|fill-blue|dark:" frontend/lib/constants.ts frontend/components/charts/RollingWinrateChart.tsx frontend/components/charts/CoOccurrenceHeatmap.tsx frontend/components/analytics/PerformanceAnalysisDashboard.tsx frontend/components/reporting/Widgets.tsx frontend/components/charts/TradeChart.tsx` returns 0 matches ( note: `lib/constants/colors.ts` and `TaxonomyManager.tsx` default tag swatch `#f59e0b` — update `TaxonomyManager.tsx` lines 84 & 145 default initial tag color from `"#3b82f6"` to `"#f59e0b"`).

- [x] 5.2 **Files:** `frontend/components/calendar/CalendarHeader.tsx`, `frontend/components/calendar/MonthView.tsx`, `frontend/components/calendar/YearView.tsx`, `frontend/components/metrics/MetricsCards.tsx` — Migrate calendar cells & KPI cards from `teal-*`/`red-*`/`emerald-*` `dark:*` to `--positive` (`success`) / `--negative` (`danger`) with `.tnum` (zero blur on cells)
  - **Exact Class Replacement:**
    - `CalendarHeader.tsx` line 159: replace `'text-teal-600 dark:text-teal-400'` → `'text-success font-mono'` and `'text-red-600 dark:text-red-400'` → `'text-danger font-mono'`.
    - `MonthView.tsx`:
      - Line 80: replace `'bg-teal-500/10 dark:bg-teal-500/20 text-teal-700 dark:text-teal-400 border border-teal-500/30'` → `'bg-success/12 text-success border border-success/30'`.
      - Line 84: replace `'bg-red-500/10 dark:bg-red-500/20 text-red-700 dark:text-red-400 border border-red-500/30'` → `'bg-danger/12 text-danger border border-danger/30'`.
      - Line 141: replace `bg-zinc-100/50 dark:bg-zinc-900/50` → `bg-[var(--glass-inset)] font-mono`.
      - Line 160: replace `'bg-teal-500/10 text-teal-700 dark:text-teal-400'` → `'bg-success/12 text-success'` and `'bg-red-500/10 text-red-700 dark:text-red-400'` → `'bg-danger/12 text-danger'`.
    - `YearView.tsx`:
      - Line 100: replace `"bg-teal-500/20 text-teal-700 dark:bg-teal-500/40 dark:text-teal-100"` → `"bg-success/20 text-success"`.
      - Line 102: replace `"bg-red-500/20 text-red-700 dark:bg-red-500/40 dark:text-red-100"` → `"bg-danger/20 text-danger"`.
      - Line 122: replace `'text-teal-600 dark:text-teal-400'` / `'text-red-600 dark:text-red-400'` → `'text-success font-mono'` / `'text-danger font-mono'`.
    - `MetricsCards.tsx` lines 41–42: replace `"text-emerald-500 dark:text-emerald-400"` → `"text-success"` and `"text-rose-500 dark:text-rose-400"` → `"text-danger"`, and ensure KPI numeric value spans carry `font-mono`.
  - **DoD:** `grep -En "teal-|dark:|zinc-" frontend/components/calendar/CalendarHeader.tsx frontend/components/calendar/MonthView.tsx frontend/components/calendar/YearView.tsx frontend/components/metrics/MetricsCards.tsx` returns 0 matches.

## 6. Phase 6 — Floating Modals (`.glass-float`) & Remaining `dark:` / `zinc-*` / `gray-*` Sweep

- [x] 6.1 **Files:** Modal dialog containers across `frontend/app/dashboard/trades/TradesPageClient.tsx`, `frontend/components/accounts/AccountClearTradesModal.tsx`, `frontend/components/accounts/AccountDeleteModal.tsx`, `frontend/components/trades/{AddExecutionModal,CorrectTradeModal,ExecutionLegsTable,LinkBrokerTransactionModal,MergePreviewModal,SaveFilterModal,SplitExecutionModal,TradePickerModal}.tsx`, `frontend/components/settings/{CorporateActionsSettings,GeneralSettings,GenerateTokenModal,TokenDisplayModal}.tsx`, `frontend/components/settings/modals/{PortfolioCreateModal,PortfolioEditModal,BrokerAccountCreateModal,BrokerAccountEditModal}.tsx`, `frontend/components/reporting/ReportFilterBar.tsx`, `frontend/components/ui/AboutModal.tsx` — Upgrade floating modal panels to `.glass-float` and remove heavy `shadow-xl`/`shadow-2xl` & `bg-white dark:bg-gray-800`
  - **Exact Class Replacement:**
    - In `SaveFilterModal.tsx`:
      - Line 59: replace `rounded-xl bg-white p-6 shadow-xl dark:bg-gray-800` → `glass-float p-6`.
      - Line 63: replace `text-gray-700 dark:text-gray-300` → `text-foreground`.
      - Line 68: replace `border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white` → `border-input bg-[var(--glass-inset)] px-4 py-2 text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring`.
    - In all listed modal dialog inner panel `<div>`s: replace `solid-card ... shadow-2xl`, `rounded-xl bg-card border border-border ... shadow-2xl`, `rounded-xl bg-card border border-border shadow-xl`, and `bg-background rounded-lg border border-border shadow-xl` with `glass-float` (preserving all width, padding, flex, `max-h-*`, `role="dialog"`, and `aria-*` attributes verbatim).
  - **DoD:** `grep -En "shadow-2xl|dark:bg-gray|focus:border-blue" frontend/components frontend/app` returns 0 matches.

- [x] 6.2 **Files:** `frontend/components/auth/{LoginForm,RegisterForm}.tsx`, `frontend/app/(auth)/{reset-password,forgot-password}/page.tsx`, `frontend/components/notes/{NoteForm,QuickNoteInput,MarkdownRenderer}.tsx`, `frontend/components/trades/TradeScreenshotUploader.tsx`, `frontend/components/broker/SchwabConnectionCard.tsx`, `frontend/__tests__/components/notes/NoteForm.test.tsx` — Final mechanical cleanup of remaining `dark:*` and `zinc-*` classes + sync `NoteForm.test.tsx`
  - **Exact Class Replacement:**
    - `LoginForm.tsx` (lines 82, 110), `RegisterForm.tsx` (lines 121, 140, 160, 181), `app/(auth)/reset-password/page.tsx` (lines 97, 116), `app/(auth)/forgot-password/page.tsx` (line 102): replace `border-border dark:border-border` → `border-border` and `placeholder-zinc-500` → `placeholder:text-muted-foreground` (check all remaining `placeholder-zinc-*` across `frontend/components` and `frontend/app` and replace with `placeholder:text-muted-foreground`).
    - `NoteForm.tsx`:
      - Lines 59 & 61 (character counter): replace `"text-red-500"` → `"text-danger"` and `"text-amber-500"` → `"text-warning"`.
      - Lines 95, 106, 126, 141, 167: replace `border-border dark:border-border` → `border-border` and `placeholder-zinc-400` → `placeholder:text-muted-foreground`.
    - `frontend/__tests__/components/notes/NoteForm.test.tsx` (lines 83, 93): update `expect(counter.className).toContain("text-amber-500")` → `expect(counter.className).toContain("text-warning")` and `expect(counter.className).toContain("text-red-500")` → `expect(counter.className).toContain("text-danger")`.
    - `QuickNoteInput.tsx` line 71: replace `bg-zinc-50/80 dark:bg-zinc-900/80 border border-border dark:border-border rounded-lg` → `glass-inset`.
    - `MarkdownRenderer.tsx` line 48: replace `prose-blockquote:border-l-zinc-500` → `prose-blockquote:border-l-border`.
    - `TradeScreenshotUploader.tsx` line 160: replace `border-border dark:border-border` → `border-border`.
    - `SchwabConnectionCard.tsx`: line 101 replace `border-border dark:border-border` → `border-border`; line 105 replace `${connected ? "bg-green-400" : "bg-zinc-500"}` → `${connected ? "bg-success" : "bg-muted-foreground"}`.
    - Run a sweep across `frontend/app` and `frontend/components` for any straggling `dark:border-border`, `text-zinc-*`, `bg-zinc-*`, `border-zinc-*`, `text-gray-*`, `border-gray-*` (excluding `__tests__`) and replace mechanically (`zinc-400/500/600` text → `text-muted-foreground`, `zinc-800` text → `text-foreground`, `zinc-50/100/800/900` surface → `bg-[var(--glass-inset)]` or `bg-secondary`, `dark:border-border` → remove).
  - **DoD:** `grep -rnE "\bdark:|\b(bg|text|border|placeholder)-(zinc|gray|slate)-[0-9]+" frontend/app frontend/components --include="*.tsx"` returns 0 matches.

## 7. Phase 7 — Styleguide Sync & Full Automated Verification Gate

- [x] 7.1 **File:** `frontend/../docs/styleguide.md` (`docs/styleguide.md`) — Sync token tables, utility class documentation, and `ui-reviewer` checklist with `docs/DESIGN.md`
  - **Exact Doc Update:**
    - Update §1–§8 & §10–§11 in `docs/styleguide.md` so all references to Indigo (`#6366f1`, `#5153ba`, `#6063dd`), `Geist`, and `.solid-card`-only guidance reflect the implemented `docs/DESIGN.md` tokens (`--canvas`, `--ink`, `--accent` Hiberbee Amber, `--positive`, `--negative`, `--caution` dashed), `Inter` + `IBM Plex Mono` (`.tnum`), `.glass-chrome` / `.glass-card` / `.glass-inset` / `.glass-float`, `.btn-primary` / `.btn-glass`, `.wl-row`, and the 60-FPS blur checklist item.
  - **DoD:** `grep -Ei "#6366f1|#6063dd|#5153ba|Geist" docs/styleguide.md` returns 0 matches.

- [x] 7.2 **Verification Gate** — Run static audits, TypeScript strict check, ESLint, Jest unit suite, and Next.js production build
  - **Exact Commands:**
    1. Zero SaaS Blue audit (excluding user tag palette `lib/constants/colors.ts` & tests):
       `! grep -rnE "\b(bg|text|border|ring|from|to|via|fill|stroke)-(blue|indigo|sky|violet|purple|cyan)-[0-9]+|#6063dd|#6366f1|#5153ba|#4f52b7|#3b82f6|#8b5cf6" frontend/app frontend/components`
    2. Zero `dark:` modifier & hardcoded neutral audit:
       `! grep -rnE "\bdark:|\b(bg|text|border|placeholder)-(zinc|gray|slate)-[0-9]+" frontend/app frontend/components --include="*.tsx"`
    3. 60-FPS blur boundary audit (zero `backdrop-blur` on rows/mobile list cards/calendar/heatmap):
       `! grep -rn "backdrop-blur" frontend/components/trades/TradeRow.tsx frontend/components/trades/ExecutionRow.tsx frontend/components/trades/TradeCard.tsx frontend/components/trades/ExecutionLegCard.tsx frontend/components/calendar frontend/components/charts/CoOccurrenceHeatmap.tsx`
    4. Typecheck, lint, unit tests & build:
       `cd frontend && npx tsc --noEmit && npm run lint && npm test -- --watchAll=false && npm run build`
    5. Dual-theme token parity audit (every DESIGN.md token defined for Light AND Dark):
       `for t in $(grep -oE "^\s+--[a-z0-9-]+:" docs/DESIGN.md | tr -d ' :' | sort -u); do [ "$(grep -cE "^\s+$t:" frontend/app/globals.css)" -ge 2 ] || echo "MISSING $t"; done` prints nothing.
    6. Dual-theme visual check (`/ui-visual-check`): screenshot `/dashboard`, `/dashboard/trades`, a trade detail page, `/dashboard/settings` and one open modal at `1440×900` and `375×812` **in both Light (Pearl Alabaster) and Dark (Obsidian)** — verify no white-on-white / dark-on-dark text, visible glass borders and card shadows in Light, amber row hover/selection in both, dashed caution badges in both.
  - **DoD:** Commands 1–5 exit with code `0`; visual check 6 shows no theme-specific contrast or surface defects.
