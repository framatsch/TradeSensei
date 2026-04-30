## REMOVED — Scope Change

This spec has been superseded by the architectural decision made in Spec 2
(`app-state-topbar-navigation`). Playbooks and Tags are managed in the
**Global Library** application context, not in Settings.

**What this means:**

- The `playbooks-tags` Settings tab is **not implemented** in Spec 3.
- `PlaybooksTagsSettings.tsx` component is **not created**.
- `/dashboard/playbooks` redirects to `/dashboard/library/playbooks` (Spec 2, task 7.5).
- `/dashboard/tags` redirects to `/dashboard/library/tags` (Spec 2, task 7.6).
- The existing `PlaybookList` and `TagList` components are rendered inside the
  Library context pages at `/dashboard/library/playbooks` and
  `/dashboard/library/tags` respectively.

**Rationale:** The Global Library is a first-class application context (BentoMenu
entry) intended to house all portfolio-agnostic strategic entities. Placing
Playbooks and Tags in Settings would contradict this architecture and fragment the
user's workflow between two different locations for the same concern.

For the Library context implementation, see:
`openspec/changes/app-state-topbar-navigation/specs/topbar-navigation/spec.md`
and tasks 7.1–7.6 in `openspec/changes/app-state-topbar-navigation/tasks.md`.
