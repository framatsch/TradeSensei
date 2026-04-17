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

## Workflow Commands (Skills)

Skills live in `.opencode/skills/` (symlinked into `.claude/skills/` for discovery).

| Command | Skill file | Purpose |
|---------|-----------|---------|
| `/openspec-propose` | `.opencode/skills/openspec-propose/SKILL.md` | Create a new OpenSpec change |
| `/openspec-explore` | `.opencode/skills/openspec-explore/SKILL.md` | Explore / think — no application code written |
| `/openspec-apply-change` | `.opencode/skills/openspec-apply-change/SKILL.md` | Implement a pending OpenSpec task by task |
| `/openspec-archive-change` | `.opencode/skills/openspec-archive-change/SKILL.md` | Archive a completed change |
| `/commit-helper` | `.opencode/skills/commit-helper/SKILL.md` | Staged-commit with emoji + category format |
| `/safe-commit` | `.opencode/skills/safe-commit/SKILL.md` | Lint → test → commit guard |
| `/lint-check` | `.opencode/skills/lint-check/SKILL.md` | Run all linters |
| `/db-migration` | `.opencode/skills/db-migration/SKILL.md` | Generate + run Alembic migration |
| `/unit-test` | `.opencode/skills/unit-test/SKILL.md` | Write / run unit tests |
| `/openapi-sync` | `.opencode/skills/openapi-sync/SKILL.md` | Regenerate OpenAPI TypeScript client |
| `/ui-visual-check` | `.opencode/skills/ui-visual-check/SKILL.md` | Screenshot + visual diff |
| `/refactor-pro` | `.opencode/skills/refactor-pro/SKILL.md` | Safe refactoring workflow |

OpenSpec command wrappers: `.opencode/command/opsx-{propose,explore,apply,archive}.md`

---

## Non-Negotiable Rules (abbreviated — full details in `AGENTS.md`)

- **OpenSpec:** Before implementing any OpenSpec task, run `/openspec-apply-change` (reads `.opencode/skills/openspec-apply-change/SKILL.md`) — do NOT start coding without it.
- **Agent files:** Read the relevant agent file from the table above before writing any code for that domain.
- **Language:** All code, comments, and text in English.
- **Python:** `mypy --strict` · async-only DB · `Decimal` for monetary values · UTC datetimes · service layer owns transactions.
- **Migrations:** Alembic only — never alter schema by hand.
- **Packages:** `uv add` only — never `pip install`.
- **Frontend:** No `dark:` modifier — use semantic tokens (`bg-background`, `text-foreground`, …). Theme switches automatically.
- **Commits:** Only when the user explicitly asks.
