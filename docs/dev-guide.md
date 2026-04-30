# Developer guide

This guide covers everything you need to get the Trade Sensei backend
running locally, run the test suite, and add new features.

---

## Prerequisites

| Tool | Minimum version | Install |
|------|----------------|---------|
| Python | 3.12 | [python.org](https://www.python.org/downloads/) |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Docker | 24+ | [docs.docker.com](https://docs.docker.com/engine/install/) |
| Docker Compose | v2 (bundled with Docker Desktop) | — |

All Python dependency management uses `uv` exclusively. Do not use `pip` or
`poetry` in this project.

---

## Quick start

```bash
# 1. Clone the repository
git clone https://github.com/<org>/tradesensei.git
cd tradesensei

# 2. Start the database
docker compose up -d db

# 3. Move into the backend directory and install dependencies
cd backend
uv sync

# 4. Copy the example env file and fill in your values
cp .env.example .env   # or create .env manually — see section below

# 5. Apply migrations
uv run alembic upgrade head

# 6. Start the API server with hot-reload
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API is now live at `http://localhost:8000`.
Interactive docs are available at `http://localhost:8000/docs`.

---

## Environment variables

All configuration is loaded from environment variables. Create a `.env` file
in `backend/` (it is gitignored) or export them in your shell.

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `DATABASE_URL` | `str` | — | Yes | Async SQLAlchemy URL: `postgresql+asyncpg://user:pass@host:5432/dbname` |
| `SECRET_KEY` | `str` | — | Yes | Random 256-bit key for JWT signing (used from Iteration 2) |
| `ENVIRONMENT` | `str` | `development` | No | Runtime mode — `development` or `production` |
| `LOG_LEVEL` | `str` | `INFO` | No | Python logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `CORS_ORIGINS` | `list[str]` | `["http://localhost:3000"]` | No | Comma-separated list of allowed CORS origins |
| `GOOGLE_CLIENT_ID` | `str` | — | No | OAuth 2.0 client ID from Google Cloud Console; required to enable Google login |
| `GOOGLE_CLIENT_SECRET` | `str` | — | No | OAuth 2.0 client secret from Google Cloud Console; required to enable Google login |
| `GOOGLE_REDIRECT_URI` | `str` | — | No | Redirect URI registered in Google Cloud Console (e.g. `http://localhost:8000/api/v1/auth/google/callback`) |
| `SMTP_HOST` | `str` | — | No | SMTP server hostname (e.g. `smtp.gmail.com`); required to enable password reset |
| `SMTP_PORT` | `int` | `587` | No | SMTP server port. Defaults to 587 (STARTTLS). |
| `SMTP_USER` | `str` | — | No | SMTP authentication username; required to enable password reset |
| `SMTP_PASSWORD` | `str` | — | No | SMTP authentication password; required to enable password reset |
| `EMAIL_FROM` | `str` | — | No | Sender email address used in password reset emails (e.g. `noreply@example.com`); required to enable password reset |
| `SMTP_TLS` | `bool` | `true` | No | Whether to use STARTTLS when connecting to the SMTP server |

Example `.env` for local development:

```dotenv
DATABASE_URL=postgresql+asyncpg://tradesensei:tradesensei@localhost:5432/tradesensei
SECRET_KEY=change-me-to-a-long-random-string
ENVIRONMENT=development
LOG_LEVEL=DEBUG
CORS_ORIGINS=http://localhost:3000

# Optional — Google OAuth 2.0 (omit to disable Google login)
# GOOGLE_CLIENT_ID=
# GOOGLE_CLIENT_SECRET=
# GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

# Optional — Email / SMTP (all four fields required for password reset to work)
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USER=your-email@gmail.com
# SMTP_PASSWORD=your-app-password
# EMAIL_FROM=your-email@gmail.com
# SMTP_TLS=true
```

---

## Google OAuth setup

To enable Google login locally, create an OAuth 2.0 client in Google Cloud Console and set the three `GOOGLE_*` variables above.

**Step 1 — Create a client ID**

1. Open [Google Cloud Console](https://console.cloud.google.com/) and select (or create) a project.
2. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**.
3. Set the application type to **Web application**.
4. Under **Authorized redirect URIs**, add `http://localhost:8000/api/v1/auth/google/callback` for local development. For production, add the equivalent URI with your public domain, e.g. `https://app.example.com/api/v1/auth/google/callback`.
5. Click **Create** and copy the **Client ID** and **Client Secret** into your `.env` file.

**Step 2 — Set the frontend secret**

The frontend uses NextAuth to manage session state. Generate a random secret and add it to `frontend/.env.local`:

```bash
openssl rand -base64 32
```

```dotenv
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_GOOGLE_CLIENT_ID=<same value as GOOGLE_CLIENT_ID>
NEXTAUTH_SECRET=<output of the openssl command above>
NEXTAUTH_URL=http://localhost:3000
```

**Behavior without Google credentials**

If `GOOGLE_CLIENT_ID` or `GOOGLE_CLIENT_SECRET` is not set, `GET /api/v1/auth/google` returns `503 Service Unavailable`. The "Continue with Google" button is still rendered in the UI but the redirect will fail. Password-based login continues to work normally.

---

## Email / SMTP setup (Password Reset)

To enable password reset functionality, configure SMTP. **All four fields must be set**:
- `SMTP_HOST`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `EMAIL_FROM`

Without all four, the "Forgot password?" link is hidden from the login form.

### Using Gmail

1. Enable **2-Step Verification** on your Google account.
2. Generate an [App Password](https://myaccount.google.com/apppasswords) (select "Mail" and "Windows Computer").
3. Copy the generated 16-character password and add to `.env`:

```dotenv
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
EMAIL_FROM=your-email@gmail.com
SMTP_TLS=true
```

### Using other SMTP providers

Replace `SMTP_HOST` and credentials with your provider's details. For example, SendGrid:

```dotenv
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG.your-sendgrid-api-key
EMAIL_FROM=noreply@example.com
SMTP_TLS=true
```

### Testing password reset locally

1. Set all SMTP variables above.
2. Restart the backend: `docker compose restart backend`
3. Navigate to `/login` and click "Forgot password?"
4. Enter your email and submit the form.
5. Check your inbox for the password reset link (valid for 1 hour).

If emails are not arriving:
- Check backend logs: `docker compose logs backend | grep -i email`
- Verify SMTP credentials are correct
- Some providers block connections from Docker — add the Docker container IP to your SMTP whitelist if needed

---

## Running the database locally

The project uses TimescaleDB (a PostgreSQL extension). The `docker-compose.yml`
at the project root defines the `db` service.

```bash
# From the project root (tradesensei/)
docker compose up -d db
```

The database is reachable at `localhost:5432` with:

- **User**: `tradesensei`
- **Password**: `tradesensei`
- **Database**: `tradesensei`

To reset the database completely (destroys all data):

```bash
docker compose down -v
docker compose up -d db
```

---

## Running migrations

Migrations live in `backend/alembic/versions/`. Always run them from the
`backend/` directory so Alembic can locate `alembic.ini`.

```bash
# Apply all pending migrations
uv run alembic upgrade head

# Check current migration state
uv run alembic current

# Roll back the last migration
uv run alembic downgrade -1
```

The `DATABASE_URL` env var must be set before running any Alembic command.
In local development this is picked up automatically from `backend/.env`.

### Portfolio migration notes

The portfolio core data model introduces a mandatory `portfolio_id` on every
account and adds portfolio-scoped API paths.

- `alembic upgrade head` creates one `Default Portfolio` per existing user and
  links all existing accounts to it.
- After the migration, `accounts.portfolio_id` is enforced as non-null.
- The previous unscoped endpoints now return `410 Gone`; update clients to the
  new portfolio-scoped URLs.

Examples:

```text
GET  /api/v1/portfolios
POST /api/v1/portfolios
GET  /api/v1/portfolios/{portfolio_id}/accounts
GET  /api/v1/portfolios/{portfolio_id}/trades
GET  /api/v1/portfolios/{portfolio_id}/metrics/summary
GET  /api/v1/portfolios/{portfolio_id}/timeseries/daily-pnl
POST /api/v1/portfolios/{portfolio_id}/imports/upload
```

---

## Running tests

Tests are in `backend/tests/`. The suite is split into two groups:

### Unit tests (no database required)

These test business logic in isolation using mocks.

```bash
cd backend
uv run pytest tests/test_trade_schemas.py tests/test_trade_service.py -v
```

### Integration tests (database required)

Integration tests hit a real TimescaleDB instance. Start the database first,
then apply migrations before running.

```bash
# Start DB and apply migrations
docker compose up -d db
uv run alembic upgrade head

# Run integration tests
uv run pytest -m integration -v
```

### Full suite with coverage

```bash
uv run pytest --cov=app --cov-report=term-missing
```

The coverage target for services and schemas is **≥ 80%**.

### Test markers

| Marker | Description |
|---|---|
| `unit` | Fast tests with no external dependencies |
| `integration` | Tests that require a live database |

Exclude integration tests in environments without a database:

```bash
uv run pytest -m "not integration"
```

---

## Linting and type checking

All checks must pass before opening a pull request. They run automatically in
CI on every push to `main`.

### Ruff (lint + format)

```bash
# Check for lint errors
uv run ruff check app/

# Check formatting
uv run ruff format --check app/

# Auto-fix lint errors and reformat
uv run ruff check --fix app/ && uv run ruff format app/
```

### mypy (strict type checking)

```bash
uv run mypy --strict app/
```

The `pyproject.toml` enforces `line-length = 88` and selects rule sets `E`,
`F`, `I`, `UP`, `B`, and `SIM`. No `type: ignore` comments are allowed unless
accompanied by a code reference explaining why.

---

## Docker build

The `backend/Dockerfile` uses multi-stage builds with three named targets.

### Development image (with hot-reload)

```bash
# From the backend/ directory
docker build --target development -t tradesensei-backend:dev .
```

### Production image (minimal, non-root)

```bash
docker build --target production -t tradesensei-backend:latest .
```

To run the full stack with Docker Compose (backend + DB, frontend optional):

```bash
# From the project root
docker compose up -d

# Optionally include the frontend (Iteration 5+)
docker compose --profile frontend up -d
```

---

## Project structure

```
backend/
├── app/
│   ├── api/          # FastAPI route handlers — HTTP logic only, no business rules
│   │   └── v1/       # Versioned router; all endpoints live under /api/v1/
│   ├── services/     # Business logic layer — orchestrates repositories, owns transactions
│   ├── repositories/ # Data access layer — SQLAlchemy queries only, no business logic
│   ├── models/       # SQLAlchemy ORM models mapping to database tables
│   ├── schemas/      # Pydantic schemas (request/response DTOs); ORM models are never exposed directly
│   ├── core/         # App-wide concerns: config.py, database.py, exceptions.py, constants.py
│   ├── utils/        # Pure helper functions with no external dependencies
│   └── main.py       # Application factory (create_app)
├── alembic/          # Alembic migration environment and version scripts
├── tests/            # pytest test suite (unit + integration)
├── Dockerfile        # Multi-stage build: builder → development → production
├── pyproject.toml    # Project metadata, dependencies, ruff and mypy config
└── alembic.ini       # Alembic configuration (script_location, logging)
```

The strict layer rule: **route handlers call services; services call
repositories; repositories call the database.** No layer may skip a level.

---

## Adding a new resource

Follow this checklist in order when adding a new resource (for example,
`Playbook`). Each step maps to a layer in the architecture.

**1. ORM model** — `app/models/<resource>.py`

Define the SQLAlchemy model. Use `NUMERIC_PRECISION` / `NUMERIC_SCALE` from
`core/constants.py` for monetary columns. Add a TimescaleDB hypertable comment
if the table is time-series.

```python
# app/models/playbook.py
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class Playbook(Base):
    __tablename__ = "playbooks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
```

**2. Pydantic schemas** — `app/schemas/<resource>.py`

Create `<Resource>Create`, `<Resource>Update`, and `<Resource>Response`
schemas. All response schemas must be wrapped in `ResponseEnvelope` at the
route level.

**3. Repository** — `app/repositories/<resource>.py`

Write async methods for `get`, `list`, `create`, `update`, `delete`.
No business logic here — only SQLAlchemy queries.

**4. Service** — `app/services/<resource>.py`

Implement business rules. Call the repository. Manage `commit` / `rollback`.
Raise domain exceptions from `core/exceptions.py` (never HTTP exceptions).

**5. API router** — `app/api/v1/<resource>.py`

Register the router in `app/api/v1/router.py`. Use the correct HTTP methods
and status codes (201 for create, 204 for delete). Inject `AsyncSession` via
`Depends(get_session)`.

**6. Tests**

- Add unit tests in `tests/test_<resource>_service.py` (mock the repository).
- Add integration tests in `tests/test_<resource>_api.py` (use the `client`
  fixture from `conftest.py`).

**7. Migration**

```bash
uv run alembic revision --autogenerate -m "add playbooks table"
# Review the generated file in alembic/versions/ before applying
uv run alembic upgrade head
```

Check the generated migration manually — autogenerate does not detect
TimescaleDB hypertable calls or custom index types. Add those by hand if needed.
