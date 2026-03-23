# Safe Commit Skill

This skill orchestrates all backend pre-commit checks to ensure the CI build passes on GitHub. It runs linting, type checking, tests, and database migrations, automatically fixing issues where possible and guiding you to fix the rest before finally committing the changes.

## Workflow

When invoked, follow these steps sequentially:

1. **Formatting & Linting**:
   - Run `uv run ruff check app/ --fix` and `uv run ruff format app/`.
   - If there are remaining linting errors, use the `edit` tool to fix them manually.

2. **Type Checking**:
   - Run `uv run mypy --strict app/`.
   - If there are type errors, fix the code manually using the `edit` tool and re-run until it passes.

3. **Database Migrations**:
   - Run `uv run alembic upgrade head`.
   - Ensure the database schema is up-to-date and no errors occur.

4. **Unit Tests**:
   - Run `uv run pytest tests/ -v --cov=app --cov-report=term-missing`.
   - If any tests fail, fix the implementation or the tests using the `edit` tool and re-run until all tests pass.

5. **Commit**:
   - Once ALL checks pass successfully, use the `skill` tool to load the `commit-helper` skill.
   - Follow the `commit-helper` instructions to generate a conventional commit message and commit the changes safely.
