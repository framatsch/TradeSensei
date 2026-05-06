## Why

Help content is currently scattered across the UI in inconsistent popups, making it difficult to maintain and discover. As the platform adds complex features like Playbooks, Portfolios, and Market Check-ins, a centralized, single-source help system is needed to ensure clarity and provide a consistent user experience.

## What Changes

- Extract all hardcoded help text into a centralized help dictionary (JSON/TypeScript).
- Implement a reusable hover-card tooltip system to replace invasive popups.
- Add new help content for Playbooks, Portfolios, and Market Check-ins.
- Create a CLI tool to export the help glossary to Markdown for documentation purposes.

## Capabilities

### New Capabilities
- `help-dictionary`: A single-source dictionary for all help content in the platform.
- `help-tooltip-system`: A reusable hover-card component for displaying help content.
- `help-markdown-exporter`: A utility to export the help dictionary to a Markdown glossary.

### Modified Capabilities
- `portfolio-management`: Integration of the new help system into portfolio features.
- `checkin-hub-ui`: Integration of the new help system into market check-in features.

## Impact

- Frontend: New components in `@/components/ui`, update existing views to use tooltips.
- Shared: New help content definition file.
- Tools: New script for Markdown export.
