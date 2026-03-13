---
name: lint-check
description: Run ruff and mypy on the tradejournal backend to catch style, import, and type errors before committing or opening a PR
license: MIT
compatibility: opencode
metadata:
  toolchain: uv, ruff, mypy
  runner: python tools/lint_check.py
---

## What I do

Run the complete linting and type-checking pipeline on `backend/app/` and report
all issues with their file paths and line numbers.

## Tools used

| Tool | What it checks |
|------|---------------|
| `ruff check` | Style, imports, common bugs (E, F, I, UP, B, SIM, TCH rules) |
| `ruff format --check` | Code formatting (line length, whitespace) |
| `mypy --strict` | Full static type analysis |

## When to use me

- Before every commit that touches Python files in `backend/`
- When CI reports lint or type failures and you need to reproduce locally
- After adding or updating a dependency that may have new type stubs

## How to run

```bash
# Full check (ruff + mypy)
python tools/lint_check.py

# Ruff only (fast, for quick iteration)
python tools/lint_check.py --ruff

# mypy only
python tools/lint_check.py --mypy

# Auto-fix ruff issues (does not fix mypy errors)
python tools/lint_check.py --fix

# CI mode (exits 1 on any failure)
python tools/lint_check.py --ci
```

Or run directly via uv from the `backend/` directory:

```bash
# From backend/
uv run ruff check app/
uv run ruff format --check app/
uv run mypy --strict app/
```

## Common ruff rules in this project

- `I` — isort-style import ordering (always fix first)
- `UP` — pyupgrade suggestions (use `X | Y` instead of `Optional[X]`)
- `TCH` — move type-only imports into `TYPE_CHECKING` blocks
- `B` — bugbear checks (mutable default args, etc.)

## Fixing mypy errors

Common patterns in this codebase:
- `Decimal | None` not `Optional[Decimal]` (UP006/UP007)
- Service methods return `TradeRead`, not `Trade` (the ORM model)
- Repository methods take `AsyncSession` from `sqlalchemy.ext.asyncio`
- All async functions must be `async def` — never use `asyncio.run()` inside app code
