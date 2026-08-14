# Trade Sensei — Frontend Style Guide

Single source of truth for UI implementation and visual review.
Covers the Dual-Theme Design System (Obsidian / Radiant).

**Source files:**
- Tokens & component classes: `frontend/app/globals.css`
- Tailwind color mapping: `frontend/tailwind.config.ts`

---

## 1. Themes

Two themes are supported: **Light (Radiant)** and **Dark (Obsidian)**.
Theme is applied via a `.dark` class on `<html>`. CSS variables flip automatically.

**Rule:** Never use `dark:` Tailwind modifier on individual classes.
The theme switches through CSS variables — components do not need to know which theme is active.

---

## 2. Semantic Color Tokens

Always use these Tailwind class names. They map to CSS variables defined in `globals.css`.

### Surfaces

| Tailwind class   | CSS variable     | Purpose                          |
| ---------------- | ---------------- | -------------------------------- |
| `bg-background`  | `--background`   | Page / main content area         |
| `bg-sidebar`     | `--sidebar`      | Sidebar surface                  |
| `bg-card`        | `--card`         | Card / panel surface             |
| `bg-popover`     | `--popover`      | Tooltips, dropdowns, floats      |
| `bg-muted`       | `--muted`        | Subtle fills, secondary surfaces |
| `bg-secondary`   | `--secondary`    | Inputs, secondary surfaces       |

### Text

| Tailwind class         | CSS variable           | Purpose                  |
| ---------------------- | ---------------------- | ------------------------ |
| `text-foreground`      | `--foreground`         | Primary text             |
| `text-card-foreground` | `--card-foreground`    | Text inside cards        |
| `text-muted-foreground`| `--muted-foreground`   | Secondary / muted text   |
| `text-primary`         | `--primary`            | Indigo accent text       |
| `text-success`         | `--success`            | Profit / positive values |
| `text-danger`          | `--danger`             | Loss / negative values   |

### Borders & Inputs

| Tailwind class  | CSS variable | Purpose               |
| --------------- | ------------ | --------------------- |
| `border-border` | `--border`   | All borders, dividers |
| `border-input`  | `--input`    | Input field borders   |
| `ring-ring`     | `--ring`     | Focus rings           |

### Accent / Brand

| Tailwind class       | CSS variable    | Value     | Purpose              |
| -------------------- | --------------- | --------- | -------------------- |
| `bg-primary`         | `--primary`     | `#5153ba` | Primary CTA button   |
| `bg-accent`          | `--accent`      | `#6366f1` | Indigo accent        |
| `bg-destructive`     | `--destructive` | `#fb7185` | Destructive actions  |

---

## 3. Forbidden Patterns

These patterns are **never** acceptable:

```tsx
// ❌ Hardcoded colors
<div className="bg-zinc-900 text-gray-500 border-slate-800" />

// ❌ dark: modifier
<div className="bg-white dark:bg-zinc-900" />

// ❌ Arbitrary hex without justification
<div className="bg-[#1a1a2e]" />

// ❌ Inline style for color
<div style={{ color: '#6366f1' }} />
```

**Exception:** Chart canvas overlays and third-party embeds where CSS variables
are unavailable. In those cases use the fixed accent value `#6063dd` (see §6).

---

## 4. Opacity with CSS Variables

Standard Tailwind opacity modifiers (`bg-foreground/10`) do not work with hex
CSS variables. Use `color-mix` instead:

```tsx
// ✅ Correct
<div className="bg-[color-mix(in_srgb,var(--foreground)_6%,transparent)]" />

// ✅ Or use a predefined utility class (see §5)

// ❌ Wrong — opacity modifier silently breaks with hex variables
<div className="bg-foreground/10" />
```

---

## 5. Component Utility Classes

Defined in `frontend/app/globals.css` under `@layer components`. Use these
instead of re-implementing complex surfaces.

### Cards & Panels

| Class          | Description                                                  | When to use                        |
| -------------- | ------------------------------------------------------------ | ---------------------------------- |
| `.solid-card`    | Opaque `bg-card`, no translucency                            | ALL cards, dashboard panels, tables|
| `.radiant-card`  | Glass-morphism: `backdrop-blur-xl` (Deprecated by user pref) | Legacy/Do not use                  |
| `.card-glossy`   | Same as `.radiant-card` without blur                          | Legacy/Do not use                  |

### Buttons

| Class         | Description                          | When to use              |
| ------------- | ------------------------------------ | ------------------------ |
| `.btn-ghost`    | Transparent with border              | Secondary actions        |
| `.btn-solid`    | `bg-foreground text-background`      | Neutral confirm actions  |
| `.btn-primary`  | Indigo fill with glow shadow         | Primary CTA              |

### Navigation

| Class        | Description                                     |
| ------------ | ----------------------------------------------- |
| `.nav-active`  | Active sidebar item: tinted bg + indigo left bar |

### Segment Controls

| Class                    | Description                                 |
| ------------------------ | ------------------------------------------- |
| `.metric-toggle-bar`       | Container for a segmented control           |
| `.metric-toggle-active`    | Active segment pill                         |
| `.metric-toggle-inactive`  | Inactive segment pill (hover state handled) |

### Tables

| Class           | Description                          |
| --------------- | ------------------------------------ |
| `.radiant-table`  | Row borders + hover using CSS tokens |

### Glow & Effects

| Class           | Description                           |
| --------------- | ------------------------------------- |
| `.glow-primary`   | Indigo box-shadow glow                |
| `.glow-success`   | Emerald box-shadow glow               |
| `.glow-danger`    | Rose box-shadow glow                  |
| `.glass-card`     | 50% translucent card with blur        |
| `.light-edge`     | Hair-thin top-lit border via `::before` |
| `.noise-overlay`  | Subtle noise texture via `::after`    |

---

## 6. Fixed Accent Values (Exception Cases)

Only for chart canvas overlays or third-party embeds where semantic tokens
are unavailable:

| Purpose                         | Value        | Example class                      |
| ------------------------------- | ------------ | ---------------------------------- |
| Active / selected button bg     | `#6063dd`    | `bg-[#6063dd] text-white`          |
| Active button border            | `#6063dd/80` | `border-[#6063dd]/80`              |
| Primary link / text accent      | `#6063dd`    | `text-[#6063dd]`                   |
| Accent tint                     | `#6063dd/10` | `bg-[#6063dd]/10`                  |
| Inactive / muted text           | `#717174`    | `text-[#717174]`                   |
| Toolbar bg (light)              | `#e9e9e9`    | `bg-[#e9e9e9]`                     |
| Toolbar border (light)          | `black/5`    | `border-black/5`                   |

---

## 7. Typography

| Purpose            | Classes                                              |
| ------------------ | ---------------------------------------------------- |
| Page heading       | `text-2xl font-semibold text-foreground`             |
| Section heading    | `text-sm font-bold uppercase tracking-widest text-muted-foreground` |
| Body text          | `text-sm text-foreground`                            |
| Muted / secondary  | `text-sm text-muted-foreground`                      |
| Numeric / P&L      | `font-mono` (always for numbers)                     |
| Table header       | `text-[10px] font-bold uppercase tracking-widest text-muted-foreground` |

Font stack: `var(--font-geist-sans)` → Inter → system-ui (mapped via `tailwind.config.ts`).

---

## 8. Spacing & Border Radius

- Spacing: Tailwind 4px grid (`p-2` = 8px, `p-4` = 16px, etc.)
- Border radius tokens:
  - `rounded-lg` → `var(--radius)` = `0.75rem`
  - `rounded-md` → `calc(var(--radius) - 2px)`
  - `rounded-sm` → `calc(var(--radius) - 4px)`

---

## 9. Animations

Defined in `tailwind.config.ts`:

| Class          | Behavior                        |
| -------------- | ------------------------------- |
| `animate-fade-in` | Opacity 0→1 over 0.4s ease-out |
| `animate-slide-up`| Slide up 8px + fade over 0.4s  |

---

## 10. Recharts Integration

Charts use Recharts with `<ResponsiveContainer>`. Grid and tooltip styles are
globally overridden in `globals.css` to use semantic tokens automatically.

- Grid lines: `var(--border)` at 40% opacity
- Tooltip: `var(--popover)` background, `var(--border)` border, `border-radius: 0.5rem`

**Checklist for every chart:**
- `<ResponsiveContainer width="100%" height={...}>` wrapping every chart
- All axes labelled
- Tooltip readable (no overflow)
- Legend entries fully visible
- `fill` / `stroke` values use semantic hex values from the token table above

---

## 11. Review Checklist (for ui-reviewer)

For every screenshot, verify:

### Layout
- [ ] No horizontal overflow on desktop (1440×900)
- [ ] No horizontal overflow on mobile (375×812)
- [ ] Cards use `.radiant-card`, `.card-glossy`, or `.solid-card`
- [ ] Consistent padding inside panels

### Colors
- [ ] No hardcoded colors — only semantic tokens or documented exceptions (§6)
- [ ] No `dark:` modifiers in source
- [ ] `text-success` / `text-danger` used for P&L values
- [ ] WCAG AA contrast: 4.5:1 normal text, 3:1 large text

### Typography
- [ ] Heading hierarchy correct (h1 → h2 → h3)
- [ ] Numeric/P&L values use `font-mono`
- [ ] Table headers use `text-[10px] font-bold uppercase tracking-widest`

### Buttons & Controls
- [ ] Primary CTAs use `.btn-primary` or `bg-primary`
- [ ] Secondary actions use `.btn-ghost`
- [ ] Segment controls use `.metric-toggle-bar`

### Charts
- [ ] Wrapped in `<ResponsiveContainer>`
- [ ] All axes labelled
- [ ] Tooltips don't overflow
- [ ] Legend visible

### Accessibility
- [ ] Visible focus rings on interactive elements
- [ ] Images/icons have `alt` or `aria-hidden="true"`
- [ ] Form inputs have associated labels
- [ ] Buttons have descriptive labels
