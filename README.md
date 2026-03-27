docker-c
<div align="center">

![Trading Journal Logo](logo.svg)
</div>

# Trading Journal

A self-hosted platform for statistical analysis and visualization of your trading activity.

Trading Journal lets you record every trade, import activity from your broker, and measure your performance with statistics like win rate, profit factor, and Sharpe ratio — all in a private instance you control. It supports multiple users, a full REST API, and a chart-driven dashboard built with Next.js and Recharts.

---

## Features

- **Trade journaling** — add trades manually or import them from a broker CSV file
- **Performance metrics** — win rate, profit factor, expectancy, Sharpe ratio, max drawdown, and more
- **Equity curve and drawdown visualization** — interactive time-series charts powered by Recharts
- **Broker import** — Interactive Brokers (IBKR) Activity Statement CSV and Charles Schwab trade history CSV
- **Playbook system** — define named trade setups (e.g. "Breakout", "Mean Reversion") and tag trades to them
- **Custom trade tags** — label trades with color-coded tags for filtering and review
- **Psychological notes** — add per-trade notes with an optional emotion field to track behavioral patterns
- **Multi-user support** — each user has isolated data; authentication via JWT (password) or Google OAuth 2.0
- **REST API** — fully documented OpenAPI spec available at `/docs`

---

## Tech stack

| Layer          | Technology                                                        |
|----------------|-------------------------------------------------------------------|
| Backend        | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic             |
| Database       | TimescaleDB (PostgreSQL extension)                                |
| Frontend       | Next.js 14 (App Router), TypeScript, Tailwind CSS, Recharts, React Query |
| Infrastructure | Docker, Docker Compose, GitHub Actions CI/CD                      |

---

## Quick start (Docker Compose)

The fastest way to run the full stack locally is with Docker Compose.

**1. Clone the repository**

```bash
git clone <repo-url>
cd tradejournal
```

**2. Create your `.env` file**

Copy `.env.example` to `.env` and fill in the required values:

```bash
cp .env.example .env
```

The complete set of variables:

```dotenv
# Database connection (either DATABASE_URL OR the DB_* variables)
DATABASE_URL=                      # optional, e.g. postgresql+asyncpg://user:pass@db:5432/db
DB_USER=tradejournal               # required if DATABASE_URL is empty
DB_PASSWORD=tradejournal           # required if DATABASE_URL is empty
DB_HOST=db                         # defaults to 'db'
DB_PORT=5432                       # defaults to 5432
DB_NAME=tradejournal               # defaults to 'tradejournal'

# Required
SECRET_KEY=                        # generate: python -c "import secrets; print(secrets.token_hex(32))"
```


Without `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`, the Google login button is visible in the UI but non-functional; password-based login works as normal.

**3. Start the stack**

```bash
docker compose up -d
```

**Services:**

| Service       | URL                             |
|---------------|---------------------------------|
| Frontend      | http://localhost:3000           |
| Backend API   | http://localhost:8000           |
| Swagger UI    | http://localhost:8000/docs      |
| ReDoc         | http://localhost:8000/redoc     |

**4. First steps**

1. Open the frontend at `http://localhost:3000`
2. Register a new account
3. Go to **Accounts** and create a broker account (e.g. "IBKR Main")
4. Import trades from a CSV file, or add your first trade manually from the dashboard

---

## Manual setup (without Docker)

Use this approach if you want to run the backend and frontend outside of containers, for example during active development.

### Backend

Prerequisites: Python 3.12+, [`uv`](https://github.com/astral-sh/uv), a running TimescaleDB/PostgreSQL instance.

```bash
cd backend
uv sync
```

Set the required environment variables (export them or place them in a `.env` file read by your shell):

```
DB_USER=user
DB_PASSWORD=pass
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tradejournal
SECRET_KEY=<your-secret-key>
ENVIRONMENT=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000
```

DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/tradejournal
SECRET_KEY=<your-secret-key>
BROKER_ENCRYPTION_KEY=<your-encryption-key>
ENVIRONMENT=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000
```

Apply database migrations and start the server:

```bash
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend

Prerequisites: Node.js 18+.

```bash
cd frontend
npm install
```

Create `frontend/.env.local` (see `frontend/.env.example` for the full list):

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_GOOGLE_CLIENT_ID=      # same value as GOOGLE_CLIENT_ID above
```

Start the development server:

```bash
npm run dev
```

The frontend is available at `http://localhost:3000`.

---

## Importing trades

1. Open the dashboard and navigate to **Import**
2. Select your broker — **IBKR** or **Schwab**
3. Select the account you want to import into
4. Upload your exported CSV file

**Exporting from Interactive Brokers (IBKR):**
In TWS or the Client Portal, go to Reports → Activity Statements. Set the period, select the **Trades** section, and export as CSV.

**Exporting from Charles Schwab:**
Log in to schwab.com, go to Accounts → History, filter to the date range you need, and download the trade history as CSV.

Duplicate detection is built in — re-uploading the same file will not create duplicate trades.

---

## Authentication

### Password login

Send a `POST` request to `/api/v1/auth/token` with your email and password. The response contains an `access_token` (JWT, 15-minute lifetime) and sets an httpOnly refresh-token cookie. Use the access token as a `Bearer` header on all subsequent requests.

### Google OAuth 2.0

Clicking "Continue with Google" on the login or registration page redirects the browser to `/api/v1/auth/google`. The backend initiates the Authorization Code Flow with Google, handles the redirect, and — on success — issues a JWT pair and redirects the user to the dashboard.

Existing local accounts with a matching verified email are automatically linked to Google on the first Google login; no manual merging is required. Google-only accounts (created through OAuth, no password set) cannot log in with a password.

### Custom OpenID Providers (e.g., Authentik)

To add Authentik or another OIDC provider, configure the following environment variables in your `.env` for the **backend**:

```dotenv
OIDC_ENABLED=true
OIDC_PROVIDER_NAME=Authentik
OIDC_CONFIGURATION_URL=https://auth.example.com/application/o/tradejournal/.well-known/openid-configuration
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret
```

The backend handles the full Authorization Code Flow via `authlib`, automatically provisions new users, and links existing accounts by email. No frontend configuration is required; the "Sign in with Authentik" button appears automatically if enabled.

---

## Using playbooks

Playbooks let you group trades by named strategy or setup so you can measure how each one performs over time.

1. Go to **Dashboard → Playbooks**
2. Create a playbook (e.g. "Breakout", "Mean Reversion", "Earnings Play")
3. When adding or editing a trade, assign it to a playbook from the dropdown
4. Performance metrics on the dashboard reflect the trades in your selected account

Filtering metrics by playbook is planned for a future iteration.

---

## API reference

The backend exposes a fully typed REST API documented with OpenAPI.

| Interface  | URL                          |
|------------|------------------------------|
| Swagger UI | http://localhost:8000/docs   |
| ReDoc      | http://localhost:8000/redoc  |

All endpoints (except registration and login) require a Bearer token. Obtain one by calling:

```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=you@example.com&password=yourpassword"
```

Pass the returned `access_token` in subsequent requests:

```bash
curl http://localhost:8000/api/v1/trades \
  -H "Authorization: Bearer <access_token>"
```

---

## Development

### Running tests

```bash
cd backend
uv run pytest tests/ -m unit        # unit tests only (no database required)
uv run pytest tests/                # all tests (requires a running test DB)
```

### Linting

```bash
cd backend
uv run ruff check app/
uv run ruff format --check app/
```

### Type checking

```bash
cd backend
uv run mypy --strict app/
```

See [`docs/dev-guide.md`](docs/dev-guide.md) for the full developer guide, including how to add a migration, regenerate the API client, and work with the Docker development stack.

---

## Project structure

```
tradejournal/
├── backend/      # FastAPI application (Python)
├── frontend/     # Next.js application (TypeScript)
├── k8s/          # Kubernetes manifests
├── docs/         # Developer documentation
└── .github/      # CI/CD workflows
```

---

## License

MIT License
