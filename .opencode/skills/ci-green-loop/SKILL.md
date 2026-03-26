---
name: ci-green-loop
description: Run an iterative GitHub Actions failure triage and fix loop until CI is green
license: MIT
compatibility: opencode
metadata:
  toolchain: gh, git, uv, npx
---

## What I do

Drive a repeatable CI-recovery loop for this repository:
- find the newest failed GitHub Actions run,
- classify the failure,
- apply a targeted fix,
- run local checks,
- commit and push,
- watch the next run,
- repeat until all checks are green.

## Guardrails

- `latest` image tags stay exclusive to `main`.
- Release or tag-triggered builds remain active.
- Every iteration must record: run id, root cause, fix, verification.
- Stop only when CI is fully green.

## Branch strategy

Before starting the loop, ask exactly one question:

"Which branch should I use: `main` directly or `ci-fix/<date>` (recommended)?"

Default recommendation: `ci-fix/<date>` and open a PR.

## Workflow

1. **Identify failed run or job**

If a job URL is provided (e.g., `https://github.com/.../actions/runs/<run-id>/job/<job-id>`):
- Extract the job ID.
- Use `gh job view <job-id> --log` to fetch logs directly.

Otherwise:
```bash
gh run list --limit 20
```

Pick the newest failed run for the current branch/repo context.

2. **Inspect logs and classify**

If job-id was extracted:
```bash
gh job view <job-id> --log
```

Otherwise:
```bash
gh run view <run-id> --log
```

Classify as one of:
- `backend`
- `frontend`
- `infra/workflow`

3. **Fix by category**

- `backend`
  - Delegate implementation to `backend-engineer`.
  - Run `lint-check` skill.
  - Run `unit-test` skill.
  - Run migrations: `uv run alembic upgrade head` from `backend/`.

- `frontend`
  - Delegate implementation to `frontend-engineer`.
  - Run TypeScript validation from `frontend/`:

```bash
npx tsc --noEmit
```

- `infra/workflow`
  - Patch CI workflow files directly under `.github/workflows/`.
  - Preserve main-only `latest` behavior and release/tag build triggers.

4. **Document iteration**

Capture a short note per cycle (in PR body, issue comment, or local notes):
- failing run id and job
- root cause classification
- concrete fix
- local verification commands and results

5. **Safe commit**

Load and execute `safe-commit` skill workflow.
It includes `commit-helper` for project-compliant commit messages.

6. **Push and observe**

```bash
git push
gh run watch
```

7. **Loop control**

- If run is red: restart from step 1.
- If run is green: stop and provide final report.

## Final report format

Return:
- total iterations
- final green run id
- concise per-iteration changelog (root cause + fix)
- any residual risk or follow-up recommendation
