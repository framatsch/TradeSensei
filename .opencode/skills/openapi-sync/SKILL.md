---
name: openapi-sync
description: Regenerate the frontend TypeScript API client from the FastAPI OpenAPI spec after backend endpoint changes
license: MIT
compatibility: opencode
metadata:
  toolchain: openapi-ts, npx, uv
---

## What I do

Keep the frontend TypeScript API client in sync with the backend OpenAPI spec.
The client is auto-generated — never hand-edit files inside `frontend/lib/api/`.

> **WARNING:** `openapi-ts` deletes all files in `frontend/lib/api/` that it did not generate.
> Manual files MUST NOT live inside `frontend/lib/api/`.
> The two hand-written files live one level up:
> - `frontend/lib/apiInterceptors.ts` — JWT injection + 401 logout interceptors
> - `frontend/lib/apiErrors.ts` — `extractApiError()` helper

## When to use me

- After any backend endpoint is added, modified, or removed
- After a Pydantic schema field is renamed or its type changes
- After a new response model is introduced
- After `openapi-docs` agent updates annotations

## Architecture

FastAPI auto-generates `/openapi.json` at runtime from:
- Route decorator annotations (`response_model`, `status_code`, `tags`)
- Pydantic schema fields (name, type, `Field(description=...)`)

The frontend client is generated from that spec using `openapi-ts`.

```
FastAPI routes + Pydantic schemas
         ↓
   GET /openapi.json
         ↓
     openapi-ts
         ↓
  frontend/lib/api/   ← never edit manually
```

## Step-by-step workflow

### 1. Start the backend (spec must be live)

```bash
# From repo root
docker compose up -d backend db

# Or run directly
cd backend && uv run uvicorn app.main:app --reload --port 8000
```

### 2. Verify the spec is accessible

```bash
curl http://localhost:8000/openapi.json | python -m json.tool | head -40
```

### 3. Regenerate the client

```bash
cd frontend/
npx openapi-ts \
  --input http://localhost:8000/openapi.json \
  --output ./lib/api \
  --client fetch
```

Or if a config file exists (`frontend/openapi-ts.config.ts`):

```bash
cd frontend/
npx openapi-ts
```

### 4. Review the diff

```bash
git diff frontend/lib/api/
```

Check that:
- New endpoints have corresponding generated functions
- Renamed fields are updated in all generated types
- No previously working types were accidentally removed

### 5. Update consumers if needed

If a type was renamed or a field removed, grep for usages in the frontend:

```bash
grep -r "OldTypeName" frontend/components/ frontend/hooks/
```

### 6. Commit the regenerated client

The generated client is committed to the repository (not `.gitignore`d) so that:
- PRs show exactly what the API surface change looks like
- CI does not require a running backend to type-check the frontend

```bash
git add frontend/lib/api/
# Use commit-helper skill for the commit message
```

## Config file location

The `openapi-ts` configuration lives at `frontend/openapi-ts.config.ts`.
Do not change the output directory (`./lib/api`) without updating all imports.
