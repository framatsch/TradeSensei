# ---
# name: safe-commit
# description: Orchestrate pre-commit checks (lint, typecheck, tests, migrations) and commit when safe
# license: MIT
# compatibility: opencode
# metadata:
#   toolchain: python, uv
# ---

# Safe Commit Skill

This skill orchestrates both backend and frontend pre-commit checks to ensure the CI build passes on GitHub. It runs linting, type checking, tests, and database migrations for the backend, as well as TypeScript validation for the frontend, automatically fixing issues where possible and guiding you to fix the rest before finally committing the changes.

## Workflow

When invoked, follow these steps sequentially:

1. **Backend Checks (Formatting, Linting & Type Checking)**:
   - Use the `skill` tool to load the `lint-check` skill.
   - Follow the `lint-check` instructions.
   - If there are remaining linting or type errors, use the `edit` tool to fix them manually.

2. **Frontend Checks (TypeScript Validation)**:
   - Run `npx tsc --noEmit` in the `frontend/` directory to catch any component or hook type errors.
   - If errors occur, fix them manually using the `edit` tool.

3. **Database Migrations**:
   - Run `uv run alembic upgrade head` in the `backend/` directory.
   - Ensure the database schema is up-to-date and no errors occur.

4. **Unit Tests**:
   - Run `uv run pytest tests/ -v --cov=app --cov-report=term-missing` in the `backend/` directory.
   - If any tests fail, fix the implementation or the tests using the `edit` tool and re-run until all tests pass.

5. **Commit**:
   - Once ALL checks pass successfully, use the `skill` tool to load the `commit-helper` skill.
   - Follow the `commit-helper` instructions to generate a conventional commit message and commit the changes safely.
