# AGENTS.md — Trading Journal Platform

This document is the primary context file for all agents and developers.
Every agent reads this file first before writing code or making decisions.

---

## 1. Project Goal

Development of a **Trading Journal Platform** for statistical analysis and
visualization of trading data. Core features:

- **Trade Journaling**: Recording and managing all trading positions
- **Performance Metrics**: Win rate, profit factor, max drawdown, expectancy, Sharpe ratio
- **Playbook System**: Tracking setup types and strategies
- **Psychological Analysis**: Error tagging, emotional notation, behavioral patterns
- **Time-Series Visualization**: Equity curve, drawdown chart, return distribution

---

## 2. Technology Stack

### Backend
| Component        | Technology                               |
|-----------------|------------------------------------------|
| Language         | Python 3.12+                             |
| Framework        | FastAPI (async-first)                    |
| Validation       | Pydantic v2                              |
| ORM              | SQLAlchemy 2.0 (async) + Alembic         |
| Database         | TimescaleDB (PostgreSQL extension)       |
| Package Manager  | uv                                       |
| Tests            | pytest + pytest-asyncio + httpx          |
| Linting/Format   | Ruff                                     |
| Type Checking    | mypy (strict)                            |

### Frontend
| Component        | Technology                               |
|-----------------|------------------------------------------|
| Framework        | Next.js 14 (App Router)                  |
| Language         | TypeScript (strict)                      |
| Styling          | Tailwind CSS                             |
| Charts           | Recharts (primary) + Chart.js (fallback) |
| State Management | Zustand or React Query (TanStack)        |
| API Client       | OpenAPI-generated client (openapi-ts)    |

### Infrastructure
| Component        | Technology                               |
|-----------------|------------------------------------------|
| Containerization | Docker + Docker Compose (Alpine images)  |
| Registry         | GitHub Container Registry (ghcr.io)      |
| Reverse Proxy    | Nginx (production)                       |
| CI/CD            | GitHub Actions                           |

---

## 3. Architecture Principles

- **API-First**: The backend is a standalone REST API. Frontend and backend
  are fully decoupled.
- **Layered Architecture**: Strict layer separation — no business logic in route
  handlers, no DB queries in service classes.
- **Async by Default**: All DB operations and external calls are async.
- **Immutable DTOs**: Pydantic schemas for request/response; ORM models are
  never exposed directly.
- **Fail-Fast Validation**: Validation happens at the API boundary (Pydantic),
  not deep inside the logic layer.

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

---

## 5. Coding Guidelines

### General
- No code without type annotations (mypy strict mode).
- Docstrings for all public functions and classes (Google style).
- No magic numbers — constants go in `core/constants.py`.
- Explicit error handling: no bare `except Exception` without re-raise or logging.
- All code, comments, docstrings, and commit messages in **English**.

### API Design
- REST conventions: resources as plural nouns (`/trades`, `/playbooks`).
- Use HTTP status codes correctly: 201 for Create, 422 for validation errors.
- All endpoints return uniform response envelopes (see `schemas/common.py`).
- Cursor-based pagination for all list endpoints.

### Database
- All schema changes via Alembic migrations — never `create_all()` in production.
- TimescaleDB hypertables for all time-series tables (partition by `closed_at`).
- Define indexes explicitly; make no implicit assumptions about query performance.
- Manage transactions explicitly — services are responsible for commit/rollback.

### Package Management
- Use `uv` exclusively for dependency management and virtual environment creation.
- Pin all dependencies via `uv.lock`.
- Separate dependency groups: `[project]`, `[tool.uv.dev-dependencies]`.

### Docker
- All images use Alpine-based base images (`python:3.12-alpine`).
- Multi-stage builds: `builder` stage installs deps, `runtime` stage is minimal.
- No secrets in images; all configuration via environment variables.

### Tests
- Unit tests for services and utils: no DB access (mocks).
- Integration tests for repositories: against real test DB (Docker service).
- End-to-end tests for critical API paths via httpx AsyncClient.
- Coverage target: >= 80% for services and schemas.

### Frontend Design System — Light Mode Color Conventions
The UI uses a dual-theme design system driven by CSS variables. For components that cannot use semantic tokens (e.g. chart canvas overlays), use these explicit light mode values with `dark:` overrides:

| Role | Light Mode Value | Usage |
|------|-----------------|-------|
| Selected / active button background | `#6063dd` | `bg-[#6063dd] text-white` |
| Selected / active button border | `#6063dd` at 80% | `border-[#6063dd]/80` |
| **Primary filled button (CTA)** | `#6063dd` bg + white text | `bg-[#6063dd] text-white hover:opacity-90` |
| Inactive / unselected button text | `#717174` | `text-[#717174]` |
| Toolbar / pill container background | `#e9e9e9` | `bg-[#e9e9e9]` |
| Toolbar container border | black at 5% | `border-black/5` |
| Primary accent (text, border, tint) | `#6063dd` | `text-[#6063dd]`, `bg-[#6063dd]/10`, `border-[#6063dd]/20` |

These explicit values are **only** used when semantic CSS variables are unavailable. For all other UI prefer semantic tokens (`bg-primary`, `text-foreground`, etc.).

---

## 6. CI/CD Pipelines

### Workflow: `ci.yml`
Triggers: push to `main`, pull requests targeting `main`

| Job              | Tool                  | Description                                          |
|------------------|-----------------------|------------------------------------------------------|
| `lint`           | ruff check + format   | Enforce code style and import order                  |
| `typecheck`      | mypy --strict         | Static type analysis                                 |
| `test`           | pytest                | Unit + integration tests (PostgreSQL service container) |
| `migration-check`| alembic upgrade head  | Verify migrations apply cleanly against a fresh DB   |

### Workflow: `docker.yml`
Triggers: push to `main`, tags matching `v*.*.*`

| Job              | Description                                                |
|------------------|------------------------------------------------------------|
| `build-push`     | Multi-arch build (amd64/arm64), push to `ghcr.io`         |

Image naming: `ghcr.io/<owner>/tradejournal-backend:<tag>`
Tags: `latest` (main), `v1.2.3` (release tag), `sha-<commit>` (all builds)

---

## 7. Iteration Overview

| Iteration | Focus                                               | Status      |
|-----------|-----------------------------------------------------|-------------|
| 1         | Data model, Pydantic schemas, base API + DB         | Complete    |
| 2         | User model, Account model, JWT auth (multi-user)    | Complete    |
| 3         | Performance metrics, statistical aggregation         | Complete    |
| 4         | Broker import: IBKR + Schwab (file upload + parser) | Complete    |
| 5         | Time-series endpoints, initial frontend              | Complete    |
| 6         | Playbook, tagging, psychological notes              | Complete    |
| 7         | Live broker API connections (IBKR TWS, Schwab API)  | Stretch     |

---

## 8. Environment Variables (Reference)

```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/tradejournal
SECRET_KEY=<random-256-bit-key>
ENVIRONMENT=development|production
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000
```

---

## 9. Agent Strategy

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

*Last updated: Iteration 6 — Playbook, tagging, and psychological notes complete*

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
