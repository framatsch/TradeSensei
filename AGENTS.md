# AGENTS.md — Trade Sensei Platform

Primary context file — read this before writing any code or making decisions.

---

## 0. Engineering Rules

These apply to every task, every agent, every change.

### Think Before Coding
Don't assume. Don't hide confusion. Surface tradeoffs.

- State assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### Simplicity First
Minimum code that solves the problem. Nothing speculative.

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

### Surgical Changes
Touch only what you must. Clean up only your own mess.

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- Remove imports/variables/functions that **your changes** made unused — not pre-existing dead code.
- If you notice unrelated dead code, mention it — don't delete it.

### Goal-Driven Execution
Define success criteria. Loop until verified.

- Transform tasks into verifiable goals: "Add validation" → "Write tests for invalid inputs, then make them pass."
- For multi-step tasks, state a brief plan with per-step verification before starting.
- Strong success criteria let you loop independently. Weak criteria require constant clarification.

---

## 1. Project Goal

**Trade Sensei Platform** — statistical analysis and visualization of trading data.

Core features: trade journaling, performance metrics (win rate, profit factor, Sharpe ratio, drawdown), playbook system, psychological tagging, equity-curve visualization.

---

## 2. Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12+, FastAPI (async), Pydantic v2, SQLAlchemy 2.0 async, Alembic |
| Database | TimescaleDB (PostgreSQL extension) |
| Frontend | Next.js 14 App Router, TypeScript strict, Tailwind CSS, Recharts, TanStack Query |
| API Client | OpenAPI-generated (`openapi-ts`) — never write raw `fetch()` to the backend |
| Package mgmt | `uv` (backend), `npm` (frontend) |
| Infrastructure | Docker + Docker Compose (Alpine), GitHub Actions CI, Nginx (prod) |

---

## 3. Architecture Principles

- **API-First** — backend is a standalone REST API; frontend and backend are fully decoupled.
- **Layered** — no business logic in route handlers; no DB queries in service classes.
- **Async by Default** — all DB operations and external calls are async.
- **Immutable DTOs** — Pydantic schemas for request/response; ORM models are never exposed directly.
- **Fail-Fast Validation** — validation happens at the API boundary (Pydantic), not deep inside logic.

---

## 4. Layer Model (Backend)

```
app/
├── api/          # Route handlers (FastAPI Router) — HTTP logic only
├── services/     # Business logic — orchestrates repositories
├── repositories/ # Data access — SQLAlchemy queries only
├── models/       # SQLAlchemy ORM models (DB tables)
├── schemas/      # Pydantic schemas (DTOs for request/response)
├── core/         # Config, DB session, dependencies
└── utils/        # Pure helper functions (no dependencies)
```

Detailed rules (anti-patterns, standards, DB conventions) live in the relevant agent files — see §6 below.

---

## 5. Non-Negotiable Rules

- **Language** — all code, comments, and commit messages in English.
- **Types** — `mypy --strict` must pass with zero errors.
- **Money** — use `Decimal` for all monetary values, never `float`.
- **Time** — all timestamps are timezone-aware UTC.
- **DB** — schema changes via Alembic only; never `create_all()` in production.
- **Packages** — `uv add` only; never `pip install` or edit `pyproject.toml` manually.
- **Frontend** — no `dark:` modifiers; use semantic tokens (`bg-background`, `text-foreground`, …).
- **OpenSpec** — before implementing any OpenSpec task, run `/openspec-apply-change` first.

### Audit Logging Policy

All backend changes must follow the audit logging policy. Audit logs are emitted by
middleware for standard CRUD endpoints, while complex operations require manual
audit events with safe metadata only.

Coverage
- POST/PUT/PATCH/DELETE endpoints are automatically logged by middleware.
- GET requests are logged only when `LOG_LEVEL=DEBUG`.
- Manual audit events are required for complex operations (bulk actions, imports,
  merges, restores) when you need to log additional metadata such as counts.

Sensitive data exclusion
- Never log: P&L, commissions, prices, quantities, strategy notes, playbook names,
  tag names, passwords, tokens, API secrets.
- Log only safe identifiers (user_id, resource_id) and hashed email (`email_hash`).

Action naming
- Use `<resource>.<verb>` format (e.g., `trade.created`, `account.deleted`).
- Standard verbs: created, updated, deleted, merged, split, restored, completed,
  failed.

Error logging
- Wrap critical operations in try/except where needed and log with `logger.error()`.
- Log validation failures with field names and error messages (no sensitive values).

Examples
- Middleware auto-logging: `backend/app/core/audit_middleware.py`
- Manual audit event pattern: `backend/app/services/audit_service.py`
- Error logging pattern: `backend/app/core/audit_middleware.py`

Agent instructions
- backend-engineer: verify audit logging coverage for new endpoints; add manual
  audit events for complex operations.
- frontend-engineer: confirm backend endpoints have audit logging (middleware or
  manual) and document expected actions in PRs.
- code-reviewer: check audit coverage, sensitive data exclusion, error logging,
  and action naming conventions.

---

## 6. Iteration Status

| Iteration | Focus | Status |
|-----------|-------|--------|
| 1 | Data model, Pydantic schemas, base API + DB | Complete |
| 2 | User model, Account model, JWT auth (multi-user) | Complete |
| 3 | Performance metrics, statistical aggregation | Complete |
| 4 | Broker import: IBKR + Schwab (file upload + parser) | Complete |
| 5 | Time-series endpoints, initial frontend | Complete |
| 6 | Playbook, tagging, psychological notes | Complete |
| 7 | Simplified execution model (origin/deleted/restore) | Complete |
| 8 | Live broker API connections (IBKR TWS, Schwab API) | Stretch |
| 9 | Portfolio core data model and scoped APIs | In Progress |

---

## 7. Reference Docs

| Topic | Location |
|-------|---------|
| Environment variables | `docs/dev-guide.md` |
| CI/CD pipelines | `.github/workflows/` |
| DB migration workflow | `.opencode/skills/db-migration/SKILL.md` |
| Local dev setup | `docs/dev-guide.md` |

---

## 8. Agent Strategy

Custom subagents are defined in `.opencode/agents/`. The primary `build` agent
invokes them via the Task tool. Subagents can also be called manually with `@<name>`.

### Available Subagents

| Agent | File | Responsibility |
|-------|------|----------------|
| `backend-engineer` | `.opencode/agents/backend-engineer.md` | Python/FastAPI implementation following the layered architecture |
| `frontend-engineer` | `.opencode/agents/frontend-engineer.md` | Next.js/TypeScript implementation, Tailwind, Recharts |
| `test-writer` | `.opencode/agents/test-writer.md` | pytest (backend) and React Testing Library (frontend) tests |
| `openapi-docs` | `.opencode/agents/openapi-docs.md` | FastAPI route annotations and Pydantic field descriptions |
| `code-reviewer` | `.opencode/agents/code-reviewer.md` | Architecture compliance, type safety, security — read-only |
| `docs-writer` | `.opencode/agents/docs-writer.md` | AGENTS.md, user guide, API usage examples, dev setup guide |
| `changelog-writer` | `.opencode/agents/changelog-writer.md` | CHANGELOG.md maintenance (Keep a Changelog format) |
| `ui-reviewer` | `.opencode/agents/ui-reviewer.md` | Visual review of frontend screenshots — layout, a11y, design system |
| `deployment-diagnoser` | `.opencode/agents/deployment-diagnoser.md` | Kubernetes + Playwright diagnostics and deployment fixes |

### Available Skills

Skills are invokable workflows stored in `.opencode/skills/<name>/SKILL.md`.

| Skill | Directory | Description |
|-------|-----------|-------------|
| `commit-helper` | `.opencode/skills/commit-helper/` | Conventional commit message generation via `tools/commit_helper.py` |
| `safe-commit` | `.opencode/skills/safe-commit/` | Orchestrates backend checks (lint, typecheck, tests, migrations) before using commit-helper |
| `lint-check` | `.opencode/skills/lint-check/` | Run ruff check, ruff format, and mypy --strict via `tools/lint_check.py` |
| `unit-test` | `.opencode/skills/unit-test/` | Run pytest with coverage via `tools/unit_test.py` |
| `db-migration` | `.opencode/skills/db-migration/` | Full Alembic migration workflow including TimescaleDB hypertable steps |
| `openapi-sync` | `.opencode/skills/openapi-sync/` | Regenerate the frontend OpenAPI client from the live FastAPI spec |
| `deploy-local` | `.opencode/skills/deploy-local/` | Docker Compose start/stop/reset/debug workflow for local development |
| `docker-build` | `.opencode/skills/docker-build/` | Local and multi-arch Docker image build workflow |
| `ci-green-loop` | `.opencode/skills/ci-green-loop/` | Iterative GitHub Actions triage and fix loop until CI is fully green |
| `ui-visual-check` | `.opencode/skills/ui-visual-check/` | Screenshot-based visual review using the `ui-reviewer` subagent |

### Standard Task Flow

For every feature that touches both backend and frontend:

```
1. backend-engineer + frontend-engineer   (parallel)
2. test-writer                            (after both complete)
3. openapi-docs                           (parallel with test-writer, after backend)
4. code-reviewer                          (after all implementation is done)
5. ui-reviewer                            (frontend changes only — after code-reviewer)
6. docs-writer                            (update AGENTS.md + api-usage.md)
7. changelog-writer                       (append to [Unreleased] section)
```

For backend-only changes: skip steps 1 `frontend-engineer`, 3 `openapi-docs`, and 5 `ui-reviewer`.
For frontend-only changes: skip step 1 `backend-engineer` and step 3 `openapi-docs`.

---

> **Maintenance note — OCR managed block:** `ocr init` appends the `<!-- OCR:START/END -->` block wherever it runs. In **CLAUDE.md** the block must stay at the **top** (Claude Code loads it fully, but editors should not push it down as the file grows). In **AGENTS.md** the block is intentionally at the bottom because agents are always told to read this file explicitly — truncation is not a risk. If CLAUDE.md ever exceeds ~200 lines and context loading becomes a concern, keep the OCR block as the first section.

*Last updated: Iteration 7 — Consolidated context; engineering rules added; details delegated to agent/skill files*

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
