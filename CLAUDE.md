<!-- OCR:START -->
## Open Code Review Instructions

These instructions are for AI assistants handling code review in this project.

Always open `.ocr/skills/SKILL.md` when the request:
- Asks for code review, PR review, or feedback on changes
- Mentions "review my code" or similar phrases
- Wants multi-perspective analysis of code quality
- Asks to map, organize, or navigate a large changeset

Use `.ocr/skills/SKILL.md` to learn:
- How to run the 8-phase review workflow
- How to generate a Code Review Map for large changesets
- Available reviewer personas and their focus areas
- Session management and output format

Keep this managed block so `ocr init` can refresh the instructions.

<!-- OCR:END -->

---

## Project Context

Full tech stack, architecture principles, coding standards, iteration status, and agent strategy:
→ **Read `AGENTS.md`** before starting any non-trivial task.

---

## Agent Delegation

Before implementing, read the relevant agent file for rules, anti-patterns, and step-by-step workflow:

| Task | Agent file |
|------|-----------|
| Python/FastAPI backend | `.opencode/agents/backend-engineer.md` |
| Next.js/TypeScript frontend | `.opencode/agents/frontend-engineer.md` |
| Tests (pytest / Jest + RTL) | `.opencode/agents/test-writer.md` |
| OpenAPI annotations & schemas | `.opencode/agents/openapi-docs.md` |
| Docs & AGENTS.md updates | `.opencode/agents/docs-writer.md` |
| CHANGELOG.md entries | `.opencode/agents/changelog-writer.md` |
| E2E / Playwright failures | `.opencode/agents/e2e-fixer.md` |
| Kubernetes / deployment issues | `.opencode/agents/deployment-diagnoser.md` |
| Refactoring & code reduction | `.opencode/agents/code-optimize.md` |
| UI screenshot review | `.opencode/agents/ui-reviewer.md` |

---

## Workflow Commands (OpenSpec)

| Command | Purpose |
|---------|---------|
| `/opsx-propose` | Create a new change + all artifacts in one step |
| `/opsx-explore` | Explore / think — no application code written |
| `/opsx-apply` | Implement a pending change task by task |
| `/opsx-archive` | Archive a completed change |

Details: `.opencode/command/opsx-{propose,explore,apply,archive}.md`

---

## Non-Negotiable Rules (abbreviated — full details in `AGENTS.md`)

- **Language:** All code, comments, and text in English.
- **Python:** `mypy --strict` · async-only DB · `Decimal` for monetary values · UTC datetimes · service layer owns transactions.
- **Migrations:** Alembic only — never alter schema by hand.
- **Packages:** `uv add` only — never `pip install`.
- **Frontend:** No `dark:` modifier — use semantic tokens (`bg-background`, `text-foreground`, …). Theme switches automatically.
- **Commits:** Only when the user explicitly asks.
