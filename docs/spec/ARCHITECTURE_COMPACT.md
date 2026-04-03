# TradeJournal Architecture & Structure (Compact)

This document serves as a compact reference for the current system architecture, database structure, and core functionalities of the TradeJournal platform.

## 1. Architecture Principles
*   **Layered Architecture (Backend):** Strict separation of concerns between API routes (HTTP/Validation), Services (Business Logic), Repositories (Database Access), and ORM Models.
*   **API-First:** Backend is a pure REST API (FastAPI); the Frontend (Next.js) is fully decoupled.
*   **Database:** PostgreSQL with the **TimescaleDB** extension (crucial for time-series financial and trade data).
*   **Type Safety & Validation:** Pydantic (v2) for boundary DTOs, SQLAlchemy (v2) for the ORM, strict Mypy for backend typing, and TypeScript in the frontend.

## 2. Database Structure (ORM Models)

Data models are divided into logical domains:

### Users & Accounts
*   **User:** Core user entity and authentication.
*   **UserSetting:** User-specific preferences (UI, currency preferences, etc.).
*   **Account:** Trading accounts (e.g., Interactive Brokers, Schwab).
*   **AccountProperty:** Meta-information and properties of trading accounts.

### Trades & Journaling
*   **Trade:** Main entity for executed trades (includes instrument, PnL, timestamps).
*   **TradeNote:** Psychological and analytical notes attached to specific trades.
*   **Tag / TradeTag:** Categorization system for trades (e.g., "FOMO", "Earnings Play").
*   **Playbook:** Definitions of strategies and setup types.
*   **SavedTradeFilter:** Saved filters for trade queries and custom dashboards.

### Finance & Market Data
*   **CashTransaction:** Deposits, withdrawals, fees, dividends.
*   **CorporateAction:** Stock splits, spinoffs.
*   **FxRate:** Exchange rates for multi-currency accounts.
*   **OhlcPrice:** Historical price data (Open, High, Low, Close) for instruments.

## 3. Core Functionalities (API Modules)

*   **Auth & Users:** JWT-based authentication and user management (`auth.py`, `users.py`).
*   **Accounts & Broker:** Account management and broker data import logic (IBKR, Schwab via `imports.py` & `broker.py`).
*   **Trades & Journaling:** CRUD operations for trades, and linking tags, notes, screenshots, and playbooks (`trades.py`, `notes.py`, `tags.py`, `playbooks.py`, `saved_trade_filters.py`).
*   **Metrics & Timeseries:** High-performance aggregation of performance metrics (win rate, expectancy, max drawdown) and time-series data provisioning for equity curves (`metrics.py`, `timeseries.py`).
*   **Financial Transactions:** Management of cash flows and corporate actions (`cash_transactions.py`, `corporate_actions.py`).
*   **Tax:** Tax calculations and reporting (`tax.py`).
*   **Market Data:** Handling of FX rates and historical market prices (`market_data.py`).

## 4. Technology Stack (Summary)
*   **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2.
*   **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS, Recharts, Zustand/React Query.
*   **Infrastructure:** Docker, Docker Compose, uv (package manager).

*Note for OpenSpec & Agents: This structure is mandatory context when planning new features. New functionalities must be integrated across the appropriate layers (Router -> Service -> Repository) and validated via Pydantic schemas.*