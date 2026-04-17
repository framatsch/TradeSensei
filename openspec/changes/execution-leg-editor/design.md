## Context

The `ExecutionRow` component provides inline editing for execution legs on the Trade Details page. The current edit form exposes only `price`, `quantity`, and `commission`. The `LogicalExecutionUpdate` Pydantic schema already accepts `direction`, `executed_at`, and `pnl`, and the `PATCH /api/v1/executions/{id}` endpoint is fully wired — so this is purely a frontend gap.

A secondary infrastructure problem was identified via diagnosis: if the backend container starts before a new migration file is committed to the repo, `alembic upgrade head` runs on startup and applies only what exists at that moment. Any later migration added without restarting the container leaves the DB schema behind the application code, causing silent 500 errors. The startup log currently gives no visible indication of this state.

The `ExecutionLegsTable` error branch renders a static string with no recovery path; users have no way to know whether to reload or contact support.

## Goals / Non-Goals

**Goals:**
- Expose `direction`, `executed_at`, and `pnl` in the `ExecutionRow` inline editor.
- Enhance startup migration logging to explicitly state the applied head revision and warn if the code-side head differs.
- Replace the static error text in `ExecutionLegsTable` with a retry button and a connection-hint message.

**Non-Goals:**
- New backend endpoints (none needed).
- Changing the `LogicalExecutionUpdate` schema (already supports all fields).
- Adding DB-level validation that `pnl` is set for exit legs (policy, not enforcement).
- Moving the editor into a modal (inline edit stays inline).

## Decisions

### D1: Direction as a toggle button, not a `<select>`

A LONG/SHORT toggle (two pill buttons) is more touch-friendly and visually consistent with the existing Side badge in the table. A `<select>` would work but diverges from the design language.

*Alternatives considered:* `<select>` — rejected (visual inconsistency with Side badge); radio inputs — rejected (too verbose).

### D2: `executed_at` as `<input type="datetime-local">`

The native datetime-local input is available in all supported browsers, requires no extra dependency, and round-trips cleanly to the ISO-8601 strings the API expects. The input value must be converted: `datetime-local` uses local time without timezone, so the component stores the user's input and converts to UTC on save.

*Alternatives considered:* third-party date picker — rejected (adds dependency for marginal UX gain).

### D3: `pnl` always visible in edit mode, not conditioned on leg type

The backend model has no concept of "entry vs. exit" as a boolean field. Conditioning visibility on direction would be a heuristic that breaks for multi-leg/complex trades. Showing the field for all legs (defaulting to empty/`null`) is safe; the backend accepts `null`.

### D4: Retry via `refetch` from React Query, not a full page reload

`useTradeExecutions` returns a `refetch` function. The error state adds a "Retry" button that calls `refetch()`. This is the minimal, correct recovery path and avoids a full navigation.

### D5: Startup migration log added to `run_migrations()`, not to the lifespan handler

The logging belongs in `migrations.py` next to the subprocess call, not spread into `main.py`. After `alembic upgrade head` completes, a second subprocess call to `alembic current` captures the applied head and logs it at INFO level. A mismatch warning can be added later if needed.

## Risks / Trade-offs

- **`datetime-local` timezone handling**: If the user's browser is not in UTC, the displayed time will be in local time. On save the component must convert to UTC before sending to the API. Incorrect conversion would silently store the wrong timestamp. → Mitigation: use `new Date(localString).toISOString()` which reliably produces UTC ISO-8601.
- **P&L field accepted for entry legs**: Some users may accidentally set a `pnl` on an opening leg. The backend stores it without error. → Accepted trade-off; a future validation layer can enforce the invariant.
- **Startup log overhead**: A second `alembic current` subprocess call adds ~200 ms to startup time. → Negligible for a development container; production startup time is not on the critical path.
