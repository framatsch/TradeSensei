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

1. **Strategy Choice**

Before starting the loop, ask two questions:
- "Which branch should I use: `main` directly or `ci-fix/<date>` (recommended)?"
- "Should I use `gh act` to run tests locally before pushing (faster iteration, recommended)?"

If the user chooses `gh act`:
- Use `act` commands to run relevant workflows locally.
- Only commit and push once the local `act` run is successful.

2. **Identify failed run or job**

If a job URL is provided (e.g., `https://github.com/.../actions/runs/<run-id>/job/<job-id>`):
- Extract the job ID.
- Use `gh job view <job-id> --log` to fetch logs directly.

Otherwise:
```bash
gh run list --limit 20
```

Pick the newest failed run for the current branch/repo context.

3. **Inspect logs and classify**

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

4. **Fix by category**

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

5. **Local Validation (Optional but Recommended)**

If the user enabled `gh act`:
```bash
# Example: Run only the failed job locally
gh act -j <job-name>
```

6. **Document iteration**

Capture a short note per cycle:
- failing run id (or `act` run status)
- root cause classification
- concrete fix
- local verification results

7. **Safe commit & Push**

- Load and execute `safe-commit` skill workflow.
- Only push if `act` was successful or if the user requested a remote-only loop.

8. **Observe & Loop**

```bash
git push
gh run watch
```

9. **Loop control**

- If run is red (or `act` fails): restart from step 2.
- If run is green: stop and provide final report.

## Final report format

Return:
- total iterations
- final green run id
- concise per-iteration changelog (root cause + fix)
- any residual risk or follow-up recommendation
