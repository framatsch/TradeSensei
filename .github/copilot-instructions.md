<!-- mermaid-ai-skills:start -->
## Mermaid Diagrams

When the user asks to create, edit, or visualize a diagram, follow the
instructions in `.github/instructions/mermaid.instructions.md`.
<!-- mermaid-ai-skills:end -->

## UI & Design System

Project rules live in `AGENTS.md`. For any change under `frontend/`, **`docs/DESIGN.md`
(v2.0 — Performance-First Zero-Blur UI System) is mandatory** — it is the single source of truth for look & feel:

- Dual-theme 100 % opaque tonal hierarchy: Layered Anthracite Dark (default, `#11141B` canvas / `#191E28` panels / `#222936` sub-surfaces) and Pure White Light (`#F8F9FB` canvas / `#FFFFFF` panels / `#F3F5F9` sub-surfaces), colors only via the CSS variables in `frontend/app/globals.css` and semantic Tailwind tokens; no `dark:` modifier.
- No generic SaaS blue (`blue-*`, `indigo-*`, `sky-*`, `violet-*`, `purple-*`, `cyan-*`) or butter-yellow selection (`amber-100`, `#FEF3C7`).
- Solid Amber (`.btn-primary`, `--cta-bg`) and Soft-Orange (`--sel-*`) = UI action and selection only; `success`/`danger`/`warning` = market and P&L signals only (caution always with a `1px dashed` border).
- `font-mono` + `tabular-nums` on every number.
- Zero-Blur · 60 FPS: **never** use `backdrop-filter`, `backdrop-blur-*`, ambient orbs, `.glass-*` utilities or `transition-all`.
