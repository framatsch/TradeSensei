---
name: deploy-local
description: Start, stop, and reset the tradesensei local development stack using Docker Compose including proper service startup order and health checks
license: MIT
compatibility: opencode
metadata:
  toolchain: docker, docker compose
---

## What I do

Manage the local Docker Compose development stack with the correct startup
order, health checks, and reset procedures.

## Service topology

```
┌─────────────────────────────────────────────┐
│ docker-compose.yml (local dev)               │
│                                              │
│  ┌──────────┐    ┌──────────┐               │
│  │   db     │←───│ backend  │               │
│  │TS/PG:16  │    │  :8000   │               │
│  └──────────┘    └──────────┘               │
│       ↑               ↑                      │
│  ┌────────────────────────┐                  │
│  │  frontend (:3000)      │  (Iteration 3+)  │
│  └────────────────────────┘                  │
└─────────────────────────────────────────────┘
```

## Start the stack

```bash
# Start everything (detached)
docker compose up -d

# Start with live logs (useful during development)
docker compose up

# Start only the database (when running backend locally)
docker compose up -d db
```

## Check service health

```bash
# Show status of all services
docker compose ps

# Follow backend logs
docker compose logs -f backend

# Follow DB logs
docker compose logs -f db

# Check DB is accepting connections
docker compose exec db pg_isready -U tradesensei
```

## Stop the stack

```bash
# Stop without removing volumes (preserves DB data)
docker compose down

# Stop AND remove volumes (full reset, all data lost)
docker compose down -v
```

## Apply migrations after DB start

The backend container runs migrations automatically on startup via the
entrypoint script. To run manually:

```bash
# Run migrations
docker compose exec backend uv run alembic upgrade head

# Or from local machine if backend is not running
cd backend && uv run alembic upgrade head
```

## Full reset (clean slate)

```bash
docker compose down -v           # Remove containers + volumes
docker compose up -d db          # Start only DB
docker compose exec db psql -U tradesensei -c "\l"  # Verify DB is empty
docker compose up -d             # Start full stack
# Migrations run automatically
```

## Run backend locally (outside Docker)

For faster iteration during backend development:

```bash
# Start only the DB via Docker
docker compose up -d db

# Run backend locally
cd backend/
export DATABASE_URL=postgresql+asyncpg://tradesensei:tradesensei@localhost:5432/tradesensei
uv run uvicorn app.main:app --reload --port 8000
```

Access the auto-generated OpenAPI docs: http://localhost:8000/docs

## Common issues

| Issue | Cause | Fix |
|-------|-------|-----|
| `port 5432 already in use` | Local Postgres running | `sudo systemctl stop postgresql` or change port in compose |
| `relation "trades" does not exist` | Migrations not applied | `docker compose exec backend uv run alembic upgrade head` |
| `connection refused :8000` | Backend still starting | Wait 5s, check `docker compose logs backend` |
| Backend exits immediately | Missing `.env` file | `cp .env.example .env` and fill in values |
