# Skill: ui-visual-check

## Purpose

Perform a visual review of the frontend UI by capturing screenshots and
analysing them for layout issues, accessibility violations, and consistency
with the design system.

## When to Use

Invoke this skill after any frontend change that touches layout, Tailwind
class usage, or Recharts rendering. Also useful before merging a feature
branch that includes frontend work.

## Prerequisites

- Docker Compose local stack is running (`docker compose up -d`)
- Frontend dev server is reachable at `http://localhost:3000`
- The `ui-reviewer` subagent is available in `.opencode/agents/ui-reviewer.md`

## Workflow

### Step 1 — Capture Screenshots

Use a headless browser or curl-based tool to capture the target pages.
If Playwright is available (installed in the frontend dev container):

```bash
# Inside the frontend container
npx playwright screenshot http://localhost:3000 /tmp/home.png
npx playwright screenshot http://localhost:3000/trades /tmp/trades.png
npx playwright screenshot http://localhost:3000/dashboard /tmp/dashboard.png
```

If Playwright is not available, use the browser's built-in devtools screenshot
or a manual capture and place the files in `/tmp/screenshots/`.

### Step 2 — Invoke ui-reviewer Agent

Pass the screenshots to the `ui-reviewer` subagent for analysis:

```
@ui-reviewer Review the screenshots in /tmp/screenshots/ for:
- Layout regressions (broken flex/grid, overflow, clipping)
- Tailwind class misuse (wrong spacing, wrong colour tokens)
- Recharts rendering issues (missing axes, overlapping labels)
- Accessibility issues (missing alt text, low contrast, no focus ring)
- Consistency with the design system (font sizes, colour palette)
```

### Step 3 — Review Output

The `ui-reviewer` agent outputs findings in the following format:

```
CRITICAL  — Must fix before merge (broken layout, inaccessible elements)
WARNING   — Should fix (design inconsistency, minor a11y issue)
SUGGESTION — Nice to have (micro-optimisation, polish)
```

Fix all `CRITICAL` items before merging. Document `WARNING` items as follow-up
issues if not addressed immediately.

### Step 4 — Re-capture After Fixes

After applying fixes, re-run Steps 1–3 to confirm no regressions remain.

## Notes

- Screenshots must be taken in a 1440×900 viewport (desktop baseline).
- Also capture at 375×812 (mobile) if the page has responsive breakpoints.
- Do NOT commit screenshot files to the repository.
