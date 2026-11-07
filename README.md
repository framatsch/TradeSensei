<div align="center">

![Trade Sensei Logo](logo.svg)
</div>

# Trade Sensei

A self-hosted platform for statistical analysis and visualization of your trading activity: journal trades, import from your broker, and measure performance (win rate, profit factor, Sharpe ratio, drawdown) in a private, multi-user instance with a REST API and a Next.js dashboard.

---

## Features

- **Trade journaling & import** — manual entry, broker API sync, or file import. Supports **IBKR** (Flex Web Service + Flex Query XML) and **Charles Schwab** (OAuth 2.0 Trader API + wrapped Transactions JSON).
- **Unified import pipeline** — immutable raw transactions and logical executions, FIFO matching, option combos, stock splits, deduplication, and overwrite protection for manually edited trades.
- **Execution leg editor & image attachments** — split, merge, or restore fills; attach chart screenshots (S3-compatible storage, SeaweedFS bundled).
- **Performance analytics** — win rate, profit factor, expectancy, Sharpe, drawdown, equity curve, MAE/MFE, R-multiples, time-based breakdowns.
- **Playbooks & metadata** — strategy playbooks (Markdown rules, target win rate, tags, links), taxonomy tags, typed annotation metrics, Model Book gallery, and a Metadata Correlation Explorer. New accounts are seeded with sensible defaults.
- **Daily check-in & psychology** — pre/post-session notes, market phase, and per-trade psychological annotations.
- **Portfolios & multi-user** — analytics scope to the active portfolio; isolated user data; JWT, Google OAuth 2.0, or custom OIDC (e.g. Authentik).
- **MCP server & PATs** — expose trade data to AI agents via the Model Context Protocol (`/mcp/sse`), secured by revocable Personal Access Tokens.
- **REST API** — OpenAPI spec at `/docs`.

---

## Tech stack

| Layer          | Technology |
|----------------|------------|
| Backend        | Python 3.13+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), Alembic, `uv` |
| Database       | PostgreSQL 18 (TimescaleDB-compatible) |
| Object Storage | SeaweedFS (S3-compatible) |
| Frontend       | Next.js 16 (App Router), React 18, TypeScript 5, Tailwind CSS, Recharts, Lightweight Charts, TanStack Query, Zustand, Radix UI |
| API Client     | OpenAPI-generated (`@hey-api/openapi-ts`) |
| Infrastructure | Docker Compose, Kubernetes (`k8s/`), GitHub Actions |

---

## Quick start (Docker Compose)

```bash
git clone <repo-url> && cd tradesensei
cp .env.example .env     # then fill in the required values
docker compose up -d
```

Core `.env` variables:

```dotenv
# Either DATABASE_URL or the DB_* variables
DATABASE_URL=            # e.g. postgresql+asyncpg://user:pass@db:5432/db
DB_USER=tradesensei
DB_PASSWORD=tradesensei
DB_HOST=db
DB_PORT=5432
DB_NAME=tradesensei

# Required
SECRET_KEY=              # python -c "import secrets; print(secrets.token_hex(32))"
BROKER_ENCRYPTION_KEY=   # Fernet key for stored broker API tokens
```

Without `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`, the Google login button is non-functional; password login works as normal.

| Service     | URL |
|-------------|-----|
| Frontend    | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| MCP SSE     | http://localhost:8000/mcp/sse |
| Swagger UI  | http://localhost:8000/docs |
| ReDoc       | http://localhost:8000/redoc |

**First steps:** register an account → **Settings → Accounts & Integrations** → create a broker account (`IBKR`, `Schwab`, or `Manual`) → sync, upload a file, or add a trade manually. See the [user guide](docs/user-guide.md).

---

## Manual setup (without Docker)

**Backend** (Python 3.13+, [`uv`](https://github.com/astral-sh/uv), PostgreSQL):

```bash
cd backend
uv sync
# set in env or backend/.env: DATABASE_URL, SECRET_KEY, BROKER_ENCRYPTION_KEY,
# ENVIRONMENT=development, LOG_LEVEL=INFO, CORS_ORIGINS=http://localhost:3000
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

**Frontend** (Node.js 20+):

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

The frontend runs at `http://localhost:3000` and proxies to `http://localhost:8000` (override with `API_URL`).

---

## Broker import

All paths (file upload and API sync) go through one import pipeline.

**Interactive Brokers (`ibkr`)** — Flex Query XML (`.xml`), both Activity and Trade Confirmation queries. For API sync, set `IBKR_FLEX_TOKEN` and `IBKR_FLEX_QUERY_ID` in **Settings → Accounts & Integrations**. Setup: [`docs/flex_query-setup.md`](docs/flex_query-setup.md).

**Charles Schwab (`schwab`)** — wrapped Transactions JSON (`{ "accounts": [{ "accountNumber": "...", "transactions": [...] }] }`). For API sync, configure your Schwab Developer App Key & Secret and connect via OAuth 2.0 (up to 365 days lookback). The CLI `python tools/schwab_cli.py transactions` produces the JSON for upload via the UI or `/api/v1/portfolios/{portfolio_id}/imports/upload`. See [`docs/schwab-positions-tool.md`](docs/schwab-positions-tool.md).

**Manual (`manual`)** — manual trade entry and execution tracking.

Legacy CSV exports are not supported.

---

## Authentication

- **Password** — `POST /api/v1/auth/token` returns a 15-minute JWT `access_token` (use as `Bearer`) and sets an httpOnly refresh cookie.
- **Google OAuth 2.0** — "Continue with Google" starts the flow at `/api/v1/auth/google`. Local accounts with a matching verified email are linked automatically; Google-only accounts cannot use password login.
- **Custom OIDC (e.g. Authentik)** — set on the backend; the login button appears automatically:

```dotenv
OIDC_ENABLED=true
OIDC_PROVIDER_NAME=Authentik
OIDC_CONFIGURATION_URL=https://auth.example.com/application/o/tradesensei/.well-known/openid-configuration
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret
```

---

## Image attachments

Images on trades and check-ins require an S3-compatible backend. The default Docker stack bundles SeaweedFS preconfigured. Otherwise set:

| Variable | Description |
|---|---|
| `STORAGE_BACKEND` | `s3` to enable |
| `STORAGE_BUCKET` | Bucket name (must exist) |
| `STORAGE_PROXY_URL` | Internal S3 URL for the Next.js `/api/storage-proxy` route (e.g. `http://seaweedfs:8333`) |
| `STORAGE_PUBLIC_URL` | Optional base URL override for presigned URLs |
| `STORAGE_ACCESS_KEY` / `STORAGE_SECRET_KEY` | S3 credentials |
| `STORAGE_ENDPOINT_URL` | Endpoint for S3-compatible services (SeaweedFS, MinIO) |

If unset, uploads return HTTP 503 and the upload UI is unavailable; existing images are still displayed.

---

## API usage

Docs: Swagger UI at http://localhost:8000/docs, ReDoc at http://localhost:8000/redoc. All endpoints except registration and login require a Bearer token:

```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=you@example.com&password=yourpassword"

curl http://localhost:8000/api/v1/trades -H "Authorization: Bearer <access_token>"
```

---

## Development

```bash
cd backend
uv run pytest tests/ -m unit     # unit tests (no DB)
uv run pytest tests/             # all tests (needs test DB)
uv run ruff check app/ && uv run ruff format --check app/
uv run mypy --strict app/
```

Playwright E2E (needs the full stack):

```bash
docker compose up -d --wait
npm ci && npx playwright install chromium --with-deps
npx playwright test --project=chromium
docker compose down -v
```

See [`docs/dev-guide.md`](docs/dev-guide.md) for migrations, API client regeneration, and the Docker dev stack.

---

## Project structure

```
tradesensei/
├── backend/      # FastAPI application
├── frontend/     # Next.js application
├── tools/        # CLI utilities (Schwab CLI, lint/test/commit helpers)
├── k8s/          # Kubernetes manifests
├── docs/         # Developer and integration documentation
└── .github/      # CI/CD workflows
```

---

## License

GNU Affero General Public License v3.0 (AGPL-3.0) — see [`LICENSE`](LICENSE).
