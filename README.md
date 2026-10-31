<div align="center">

![Trade Sensei Logo](logo.svg)
</div>

# Trade Sensei

A self-hosted platform for statistical analysis and visualization of your trading activity.

Trade Sensei lets you record every trade, import activity from your broker, and measure your performance with statistics like win rate, profit factor, and Sharpe ratio — all in a private instance you control. It supports multiple users, a full REST API, and a chart-driven dashboard built with Next.js and Recharts.

---

## Features

### Trade Journaling & Import
- **Trade journaling** — add trades manually, sync directly via broker APIs, or import from broker files
- **Broker integration (API Sync & File Import)** —
  - **Interactive Brokers (IBKR):** Direct Flex Web Service API sync and Flex Query XML file import (supports both Activity and Trade Confirmation Flex Queries)
  - **Charles Schwab:** Direct OAuth 2.0 Trader API sync and wrapped Transactions JSON file import (e.g. via `tools/schwab_cli.py`)
- **Unified raw-to-FIFO pipeline** — stores immutable raw broker transactions and logical executions, automatically handling FIFO matching, option combos, corporate actions (stock splits), duplicate detection, and overwrite protection for manually edited trades
- **Trade image attachments** — attach chart screenshots or setup images directly to trades via drag-and-drop; requires an S3-compatible storage backend (bundled with SeaweedFS by default)
- **Execution leg editor** — record, split, merge, or restore individual fills with split-aware logic; timestamps auto-sync to the trade open/close times

### Performance Analytics
- **Performance metrics** — win rate, profit factor, expectancy, Sharpe ratio, max drawdown, and more
- **Equity curve and drawdown visualization** — interactive time-series and financial charts powered by Recharts and TradingView Lightweight Charts
- **Strategy analysis** — MAE/MFE, R-multiple distribution, duration vs. P&L, payoff ratio
- **Time analysis** — performance breakdown by hour, weekday, month, and year to surface systematic patterns
- **Metadata Correlation Explorer** — select any Check-in annotation or taxonomy as X and any Trade annotation or taxonomy as Y; automatically renders the correct chart type (scatter, box-and-whisker, co-occurrence heatmap) to surface psychological and market-condition correlations

### Strategy & Metadata System
- **Playbook Strategy Hub** — define named trade setups (e.g. "Breakout", "Mean Reversion") enriched with a Markdown editor for strategy rules, a target win rate, taxonomy tags, image attachments, and external reference links
- **Taxonomy tags** — color-coded, icon-labeled tags scoped to trades, check-ins, or both; managed in the Library
- **Typed annotation metrics** — per-trade and per-check-in custom variables with typed inputs: integer/float sliders, boolean toggles, or string enum dropdowns; managed in the Library
- **Default metadata on registration** — new accounts are seeded with a curated set of industry-standard tags and annotation metrics so the platform is immediately useful without manual setup
- **Model Book** — star any trade or check-in to add it to a unified cross-entity gallery for pattern recognition; filterable by entity type and date range

### Daily Check-in & Psychology
- **Daily market check-in** — log pre/post-session notes, market phase, target index, and custom annotation metrics
- **Psychological notes** — per-trade notes with typed annotations (e.g. Mood, Stress, Conviction) to track behavioral patterns over time

### Portfolios & Multi-User
- **Portfolio management** — group accounts into portfolios; all analytics and API endpoints scope to the active portfolio
- **Multi-user support** — each user has fully isolated data; authentication via JWT (password), Google OAuth 2.0, or custom OIDC providers (e.g. Authentik)

### MCP AI Integration
- **MCP server** — expose your trade data to external AI agents (Claude, Gemini, OpenCode, etc.) via the Model Context Protocol over Server-Sent Events (`/mcp/sse`), secured by Personal Access Tokens
- **Domain tools** — AI agents can discover your metadata schema, search trades with multi-dimensional filters, bulk-enrich trades with tags and annotations, and create strategy playbooks from analyzed content

### Platform
- **REST API** — fully documented OpenAPI spec available at `/docs`
- **Personal Access Tokens (PATs)** — generate scoped tokens for MCP integrations and programmatic API access; tokens are revocable and support expiry

---

## Tech stack

| Layer          | Technology                                                        |
|----------------|-------------------------------------------------------------------|
| Backend        | Python 3.13+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), Alembic, `uv` |
| Database       | PostgreSQL 18 (TimescaleDB-compatible)                            |
| Object Storage | SeaweedFS (S3-compatible object storage for trade & check-in images) |
| Frontend       | Next.js 16 (App Router), React 18, TypeScript 5, Tailwind CSS, Recharts 3, Lightweight Charts 5, TanStack Query v5, Zustand 5, Radix UI |
| API Client     | OpenAPI-generated (`@hey-api/openapi-ts`)                         |
| Infrastructure | Docker, Docker Compose, Kubernetes (`k8s/`), GitHub Actions CI/CD |

---

## Quick start (Docker Compose)

The fastest way to run the full stack locally is with Docker Compose.

**1. Clone the repository**

```bash
git clone <repo-url>
cd tradesensei
```

**2. Create your `.env` file**

Copy `.env.example` to `.env` and fill in the required values:

```bash
cp .env.example .env
```

The core variables:

```dotenv
# Database connection (either DATABASE_URL OR the DB_* variables)
DATABASE_URL=                      # optional, e.g. postgresql+asyncpg://user:pass@db:5432/db
DB_USER=tradesensei                # required if DATABASE_URL is empty
DB_PASSWORD=tradesensei            # required if DATABASE_URL is empty
DB_HOST=db                         # defaults to 'db'
DB_PORT=5432                       # defaults to 5432
DB_NAME=tradesensei                # defaults to 'tradesensei'

# Required
SECRET_KEY=                        # generate: python -c "import secrets; print(secrets.token_hex(32))"
BROKER_ENCRYPTION_KEY=             # Fernet key for encrypting stored broker API tokens
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
| MCP SSE       | http://localhost:8000/mcp/sse   |
| Swagger UI    | http://localhost:8000/docs      |
| ReDoc         | http://localhost:8000/redoc     |

**4. First steps**

1. Open the frontend at `http://localhost:3000`
2. Register a new account
3. Go to **Settings → Accounts & Integrations** and create a broker account (`IBKR`, `Schwab`, or `Manual`)
4. Sync trades directly via the broker API, upload a broker export file (`.xml` for IBKR, `.json` for Schwab), or add your first trade manually from the dashboard

For trade review, keyboard navigation, and mobile controls, see the [user guide](docs/user-guide.md).

---

## Manual setup (without Docker)

Use this approach if you want to run the backend and frontend outside of containers, for example during active development.

### Backend

Prerequisites: Python 3.13+, [`uv`](https://github.com/astral-sh/uv), a running PostgreSQL instance.

```bash
cd backend
uv sync
```

Set the required environment variables (export them or place them in a `backend/.env` file):

```dotenv
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/tradesensei
SECRET_KEY=<your-secret-key>
BROKER_ENCRYPTION_KEY=<your-fernet-encryption-key>
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

Prerequisites: Node.js 20+ (Docker uses Node 24).

```bash
cd frontend
npm install --legacy-peer-deps
```

Start the development server:

```bash
npm run dev
```

The frontend is available at `http://localhost:3000`. By default, it proxies API requests to `http://localhost:8000`. You can override the backend location by setting the `API_URL` environment variable.

---

## Broker Support & Importing Trades

Trade Sensei uses a unified import pipeline that processes raw executions, links multi-leg option combos, adjusts for stock splits, deduplicates fills, and preserves manually edited trades.

Supported account types:
- **Interactive Brokers (`ibkr`)** — API sync via IBKR Flex Web Service + file upload via **Flex Query XML (`.xml`)**
- **Charles Schwab (`schwab`)** — API sync via Schwab Trader API (OAuth 2.0 + PKCE) + file upload via **wrapped Transactions JSON (`.json`)**
- **Manual (`manual`)** — manual trade entry and execution tracking

### 1. Interactive Brokers (IBKR)

**Format:** Flex Query XML (`.xml`) — both *Activity Flex Queries* (`<Trade>` elements) and *Trade Confirmation Flex Queries* (`<Execution>` elements) are supported. *(Legacy CSV exports are not supported.)*

- **Direct API Sync:** In **Settings → Accounts & Integrations**, configure your IBKR account with your `IBKR_FLEX_TOKEN` and `IBKR_FLEX_QUERY_ID`. You can then trigger an on-demand sync with a custom start date directly from the **Import** dialog or settings.
- **File Upload:** Export your Activity or Trade Confirmation Flex Query as **XML** from the IBKR Client Portal (*Performance & Reports → Flex Queries*) and upload one or more `.xml` files.
- See [`docs/flex_query-setup.md`](docs/flex_query-setup.md) for required Flex Query sections and date/time formatting.

### 2. Charles Schwab

**Format:** Wrapped Transactions JSON (`.json`) with top-level `{ "accounts": [{ "accountNumber": "...", "transactions": [...] }] }` structure. *(Legacy CSV exports are not supported.)*

- **Direct API Sync:** Configure your Schwab account with your Schwab Developer App Key & Secret, then connect via OAuth 2.0 (supports both local redirect callback and paste-URL modes). Once connected, sync transactions directly for any lookback window (up to 365 days).
- **File Upload / CLI:** Use the bundled CLI tool (`python tools/schwab_cli.py transactions`) to fetch transactions into the wrapped JSON format and upload the `.json` file in the UI or via `/api/v1/portfolios/{portfolio_id}/imports/upload`.
- See [`docs/schwab-positions-tool.md`](docs/schwab-positions-tool.md) for full CLI usage.

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
OIDC_CONFIGURATION_URL=https://auth.example.com/application/o/tradesensei/.well-known/openid-configuration
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret
```

The backend handles the full Authorization Code Flow via `authlib`, automatically provisions new users, and links existing accounts by email. No frontend configuration is required; the "Sign in with Authentik" button appears automatically if enabled.

---

## Trade image attachments

You can attach chart screenshots or setup images to any trade or daily check-in. Images are stored in an S3-compatible bucket.

### Requirements

An S3-compatible storage backend must be configured. Set the following environment variables in your `docker-compose.yml` or `.env`:

| Variable | Description |
|---|---|
| `STORAGE_BACKEND` | Set to `s3` to enable S3 storage |
| `STORAGE_BUCKET` | Bucket name (must exist) |
| `STORAGE_PROXY_URL` | Internal S3 URL used by the Next.js `/api/storage-proxy` route (e.g. `http://seaweedfs:8333`) |
| `STORAGE_PUBLIC_URL` | Optional base URL override for direct presigned URLs |
| `STORAGE_ACCESS_KEY` | S3 access key |
| `STORAGE_SECRET_KEY` | S3 secret key |
| `STORAGE_ENDPOINT_URL` | Custom endpoint for S3-compatible services (e.g. `http://seaweedfs:8333` or MinIO) |

If these variables are not set, the upload endpoint returns HTTP 503 and the image upload UI is unavailable. Existing `image_urls` values on trades are still displayed.

### Local SeaweedFS example (Default)

The local development stack includes a bundled SeaweedFS service that handles object storage internally via the Next.js storage proxy. The backend is configured to use it by default with the following settings:

```dotenv
STORAGE_BACKEND=s3
STORAGE_BUCKET=tradesensei
STORAGE_PROXY_URL=http://seaweedfs:8333
STORAGE_ACCESS_KEY=any
STORAGE_SECRET_KEY=any
STORAGE_ENDPOINT_URL=http://seaweedfs:8333
```

---

## Using playbooks

Playbooks let you group trades by named strategy or setup so you can measure how each one performs over time.

1. Go to **Dashboard → Playbooks**
2. Create a playbook (e.g. "Breakout", "Mean Reversion", "Earnings Play") with Markdown strategy rules, target win rate, taxonomy tags, and reference images/links
3. Assign trades to a playbook and filter analytics across the platform by playbook and tags

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

**Backend unit tests**

```bash
cd backend
uv run pytest tests/ -m unit        # unit tests only (no database required)
uv run pytest tests/                # all tests (requires a running test DB)
```

**Playwright E2E tests (Docker)**

The E2E tests require the full stack to be running. The easiest way is via Docker Compose:

```bash
# 1. Start the full stack (db + backend + frontend + seaweedfs)
docker compose up -d --wait

# 2. Install Playwright and its browser dependencies (once)
npm ci
npx playwright install chromium --with-deps

# 3. Run all E2E tests
npx playwright test --project=chromium

# 4. (Optional) Show the HTML report
npx playwright show-report
```

To stop and clean up afterwards:

```bash
docker compose down -v
```

> **Tip:** The `--wait` flag in step 1 blocks until all services report healthy, so you don't need a separate wait loop. If the stack is already running, skip step 1.

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
tradesensei/
├── backend/      # FastAPI application (Python 3.13+)
├── frontend/     # Next.js 16 application (TypeScript)
├── tools/        # CLI utilities (Schwab CLI, lint/test/commit helpers)
├── k8s/          # Kubernetes manifests
├── docs/         # Developer and integration documentation
└── .github/      # CI/CD workflows
```

---

## License

GNU Affero General Public License v3.0 (AGPL-3.0) — see [`LICENSE`](LICENSE) for details.
