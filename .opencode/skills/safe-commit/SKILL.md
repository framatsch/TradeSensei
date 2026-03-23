# Safe Commit Skill

This skill orchestrates all backend pre-commit checks to ensure the CI build passes on GitHub. It runs linting, type checking, tests, and database migrations, automatically fixing issues where possible and guiding you to fix the rest before finally committing the changes.

## Workflow

When invoked, follow these steps sequentially:

1. **Formatting & Linting / Type Checking**:
   - Use the `skill` tool to load the `link-check` skill.
   - Follow the `link-check` instructions
   - If there are remaining linting or type errors, use the `edit` tool to fix them manually.

2. **Database Migrations**:
   - Run `uv run alembic upgrade head`.
   - Ensure the database schema is up-to-date and no errors occur.

3. **Unit Tests**:
   - Run `uv run pytest tests/ -v --cov=app --cov-report=term-missing`.
   - If any tests fail, fix the implementation or the tests using the `edit` tool and re-run until all tests pass.

4. **Commit**:
   - Once ALL checks pass successfully, use the `skill` tool to load the `commit-helper` skill.
   - Follow the `commit-helper` instructions to generate a conventional commit message and commit the changes safely.
