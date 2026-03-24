# CI Green Loop Runbook

This runbook describes the iterative process to recover failing GitHub Actions pipelines and continue until all required checks are green.

## Purpose

Use this procedure when CI is red and you need a deterministic fix loop with clear documentation of each iteration.

## Guardrails

- Keep `latest` image tags restricted to `main`.
- Keep release and tag build triggers active.
- Document each loop iteration with root cause and fix.
- Stop only when CI is fully green.

## Branch Strategy

Recommended:

```bash
git checkout -b ci-fix/<date>
```

Alternative (higher risk):

```bash
git checkout main
```

## Loop Steps

1) Identify the newest failing run:

```bash
gh run list --limit 20
```

2) Inspect logs and classify failure:

```bash
gh run view <run-id> --log
```

Classification:
- `backend`
- `frontend`
- `infra/workflow`

3) Apply targeted fix:

- Backend:

```bash
# implementation changes via backend-engineer
# then verify:
# lint-check skill
# unit-test skill
cd backend && uv run alembic upgrade head
```

- Frontend:

```bash
# implementation changes via frontend-engineer
cd frontend && npx tsc --noEmit
```

- Infra/Workflow:
  - Edit `.github/workflows/*` directly.
  - Ensure `latest` remains main-only.
  - Ensure release/tag builds remain enabled.

4) Run safe commit flow:
- Execute `safe-commit` (includes `commit-helper`).

5) Push changes:

```bash
git push -u origin <branch>
```

6) Watch the next run:

```bash
gh run watch
```

7) Decision:
- If run is red: repeat from step 1.
- If run is green: finish and publish final report.

## Iteration Log Template

Use one entry per loop iteration:

```text
Iteration: <n>
Run ID: <run-id>
Job: <job-name>
Classification: <backend|frontend|infra/workflow>
Root cause: <short description>
Fix: <short description>
Verification:
- <command 1> -> <result>
- <command 2> -> <result>
Commit: <sha>
```

## Completion Criteria

The loop is complete only when:
- all required GitHub Actions checks are green,
- local validation used for the fix path passes,
- and iteration notes are complete.
