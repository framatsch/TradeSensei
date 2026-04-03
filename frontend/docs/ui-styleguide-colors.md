# UI Styleguide: Color System (Light + Dark)

This document defines the canonical color tokens and usage rules for the frontend UI.
Use semantic tokens first. Hardcoded hex values are only allowed where semantic tokens cannot be applied (for example, some chart overlays or third-party component edge cases).

## Core Rules

| Rule | Requirement |
| --- | --- |
| Token-first | Always use semantic variables and Tailwind semantic utilities (`bg-card`, `text-foreground`, `border-border`, `bg-primary`) before using hex values. |
| No hardcoded component colors | Do not hardcode UI colors in feature components for backgrounds, borders, text, and button states. |
| Theme parity | Every new UI element must look correct in both light and dark mode without separate component branches unless necessary. |
| State coverage | For interactive elements, define and implement at least: default, hover, active/focus, disabled. |
| Exceptions | Explicit hex values are allowed only if semantic tokens cannot be used. These cases must be documented inline with a short reason. |

## Color Tokens

Source of truth: `frontend/app/globals.css` (`:root` and `.dark` blocks).

Note: these are canonical token values. Some rendered pixels can appear slightly different because of gradients, transparency, `color-mix(...)`, shadows, and blur overlays.

| UI Role | CSS Variable | Hex (Light) | Hex (Dark) | Tailwind Semantic Utility | Usage |
| --- | --- | --- | --- | --- | --- |
| Generic page background | `--background` | `#e9e9e9` | `#171719` | `bg-background` | Main app background and page-level containers. |
| Sidebar background | `--sidebar` | `#f3f3f3` | `#131317` | `bg-sidebar` | Sidebar and side navigation surfaces. |
| Primary text | `--foreground` | `#18181b` | `#fafafa` | `text-foreground` | Standard text on default surfaces. |
| Card/panel background | `--card` | `#f3f3f3` | `#131317` | `bg-card` | Login, calendar, and panel/card surfaces. |
| Card text | `--card-foreground` | `#18181b` | `#fafafa` | `text-card-foreground` | Text on cards/panels. |
| Popover background | `--popover` | `#ffffff` | `#111113` | `bg-popover` | Tooltips, dropdown menus, floating content. |
| Popover text | `--popover-foreground` | `#18181b` | `#fafafa` | `text-popover-foreground` | Text inside floating surfaces. |
| Primary action bg | `--primary` | `#5153ba` | `#4f52b7` | `bg-primary` | Primary buttons, active CTAs, selected controls. |
| Primary action text | `--primary-foreground` | `#ffffff` | `#ffffff` | `text-primary-foreground` | Text/icons on primary actions. |
| Secondary surface | `--secondary` | `#f1f5f9` | `#18181b` | `bg-secondary` | Secondary buttons, subtle filled controls. |
| Secondary text | `--secondary-foreground` | `#0f172a` | `#a1a1aa` | `text-secondary-foreground` | Text/icons on secondary surfaces. |
| Muted surface | `--muted` | `#f1f5f9` | `#18181b` | `bg-muted` | Soft rows, badges, neutral emphasis zones. |
| Muted text | `--muted-foreground` | `#52525b` | `#71717a` | `text-muted-foreground` | Helper text, placeholders, metadata text. |
| Border/divider | `--border` | `#e4e4e7` | `#27272a` | `border-border` | Inputs, cards, table dividers, separators. |
| Input border/surface | `--input` | `#e4e4e7` | `#27272a` | `border-input` | Input borders and input-like fields. |
| Focus ring | `--ring` | `#6366f1` | `#6366f1` | `ring-ring` | Focus outlines and keyboard navigation cues. |
| Success | `--success` | `#10b981` | `#34d399` | `text-success` / `bg-success` | Positive metrics, success states, badges. |
| Danger | `--danger` | `#f43f5e` | `#fb7185` | `text-danger` / `bg-danger` | Errors, negative PnL, destructive emphasis. |

## Component Color Mapping

| Component Type | Light Mode | Dark Mode | Recommended Utilities |
| --- | --- | --- | --- |
| Page shell | `--background` | `--background` | `bg-background text-foreground` |
| Main panel/card | `--card` + `--border` | `--card` + `--border` | `bg-card border border-border text-card-foreground` |
| Secondary panel/toolbar strip | `--secondary` | `--secondary` | `bg-secondary border border-border` |
| Table container | `--card` + `--border` | `--card` + `--border` | `bg-card border border-border` |
| Table row hover | mix of `--foreground` | mix of `--foreground` | `hover:bg-[color-mix(in_srgb,var(--foreground)_3%,transparent)]` |
| Generic button (ghost) | transparent + `--border` + `--foreground` | transparent + `--border` + `--foreground` | `border border-border text-foreground` |
| Secondary button | `--secondary` + `--secondary-foreground` | `--secondary` + `--secondary-foreground` | `bg-secondary text-secondary-foreground` |
| Primary button | `--primary` + `--primary-foreground` | `--primary` + `--primary-foreground` | `bg-primary text-primary-foreground` |
| Destructive button | `--danger` + `--destructive-foreground` | `--danger` + `--destructive-foreground` | `bg-danger text-destructive-foreground` |
| Input field | `--card` + `--input` | `--card` + `--input` | `bg-card border border-input text-foreground` |
| Focus state | `--ring` | `--ring` | `focus-visible:ring-2 focus-visible:ring-ring` |

## Explicit Fallback Colors (Use Sparingly)

Only for cases where semantic tokens are not usable (for example chart internals, canvas overlays, or third-party limitations).

| Role | Light Value | Dark Value | Usage Note |
| --- | --- | --- | --- |
| Toolbar container border | `black` at 5% | `white` at 5% | Allowed fallback border for subtle separators when semantic border utilities are not feasible. |

## Agent Instruction Snippet (for Skills)

Use this snippet in skill docs or implementation prompts:

```md
### UI Color Contract
- Follow `frontend/docs/ui-styleguide-colors.md` for all UI color decisions.
- Use semantic tokens/utilities first (`bg-card`, `text-foreground`, `border-border`, `bg-primary`).
- Implement states: default, hover, active/focus, disabled.
- Ensure light and dark mode parity without hardcoded color branches unless unavoidable.
- Use explicit fallback hex values only when semantic tokens cannot be applied, and document the reason inline.
```

## Definition of Done (Color/Theme)

| Check | Done Criteria |
| --- | --- |
| Token usage | No new hardcoded color values for standard UI elements. |
| Theme support | UI is readable and visually consistent in light and dark mode. |
| Interaction states | Buttons, inputs, toggles include hover/focus/disabled states with semantic colors. |
| Accessibility baseline | Text remains clearly readable against surfaces in both themes. |
| Documentation alignment | New UI follows this styleguide or documents justified exceptions. |
