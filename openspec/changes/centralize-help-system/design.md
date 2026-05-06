## Context

The Trade Sensei platform currently has a help page (`frontend/app/help/page.tsx`) that contains a hardcoded `SECTIONS` array of help content. Individual components, like `MetricHelpLink.tsx`, link to this page using anchors and window popups. This approach is difficult to maintain as new features (Playbooks, Portfolios, Market Check-ins) are added and requires invasive popups for simple help lookups.

## Goals / Non-Goals

**Goals:**
- Centralize all help content into a single, type-safe dictionary.
- Replace popups with hover-card tooltips using Radix UI (or similar) via a reusable `HelpTooltip` component.
- Add new help content for Playbooks, Portfolios, and Market Check-ins.
- Provide a CLI tool to export the help glossary to Markdown.

**Non-Goals:**
- Implementing a full documentation site (Docusaurus/GitBook).
- Changing the layout of the existing `/help` page significantly, other than sourcing its data from the new dictionary.
- Adding interactive tutorials or "walkthroughs".

## Decisions

- **Dictionary Format**: Use a TypeScript file (`frontend/lib/help-content.ts`) to define the help dictionary. This provides full type safety and IDE autocompletion for keys.
- **Tooltip Library**: Use `@radix-ui/react-tooltip` (assumed to be part of the design system or easily addable) to implement the `HelpTooltip` component. This ensures accessibility and a modern "hover-card" feel.
- **Export Tool**: A Node.js script in `tools/export_help.ts` that imports the TypeScript dictionary and generates a Markdown file. This avoids runtime overhead in the backend while providing the requested feature.
- **Single Source of Truth**: The `/help` page and all tooltips will consume the same dictionary. The dictionary will be organized by "topics" or "tags" to allow the glossary to be grouped logically.

## Risks / Trade-offs

- **[Risk]** Dictionary file grows too large → **[Mitigation]** Split the dictionary into multiple files by category (e.g., `metrics.ts`, `playbooks.ts`) and re-export them.
- **[Risk]** Tooltip content truncation → **[Mitigation]** The `HelpTooltip` will show the `summary` by default, with a "Read more" link to the full `/help#anchor`.
- **[Risk]** Import complexity in CLI tool → **[Mitigation]** Use `tsx` or `ts-node` to run the export script directly against the TypeScript dictionary.
