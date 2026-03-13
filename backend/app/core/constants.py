"""Application-wide constants.

All magic numbers and fixed limits live here so they can be referenced
by name everywhere else in the codebase.
"""

# ─── Pagination ───────────────────────────────────────────────────────────────

PAGINATION_DEFAULT_LIMIT: int = 20
"""Default number of items returned by list endpoints."""

PAGINATION_MAX_LIMIT: int = 100
"""Maximum number of items a caller may request in one page."""

PAGINATION_MIN_LIMIT: int = 1
"""Minimum number of items a caller may request in one page."""

# ─── Trade field sizes ────────────────────────────────────────────────────────

SYMBOL_MAX_LENGTH: int = 20
"""Maximum length for a trading symbol string (e.g. 'AAPL', 'ES')."""

SYMBOL_MIN_LENGTH: int = 1
"""Minimum length for a trading symbol string."""

NOTES_MAX_LENGTH: int = 10_000
"""Maximum character length for free-text trade notes."""

NUMERIC_PRECISION: int = 18
"""Total digits for monetary / quantity NUMERIC columns."""

NUMERIC_SCALE: int = 8
"""Decimal places for monetary / quantity NUMERIC columns."""

# ─── Auth / JWT ───────────────────────────────────────────────────────────────

ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
"""Lifetime of an access JWT in minutes."""

REFRESH_TOKEN_EXPIRE_DAYS: int = 7
"""Lifetime of a refresh JWT in days."""

TOKEN_ALGORITHM: str = "HS256"
"""HMAC algorithm used when signing JWTs."""

# ─── User field sizes ─────────────────────────────────────────────────────────

PASSWORD_MIN_LENGTH: int = 8
"""Minimum acceptable password length (characters)."""

USERNAME_MIN_LENGTH: int = 3
"""Minimum acceptable username length (characters)."""

USERNAME_MAX_LENGTH: int = 50
"""Maximum acceptable username length (characters)."""

# ─── Account field sizes ──────────────────────────────────────────────────────

ACCOUNT_NAME_MIN_LENGTH: int = 1
"""Minimum length for a broker-account name."""

ACCOUNT_NAME_MAX_LENGTH: int = 100
"""Maximum length for a broker-account name."""

CURRENCY_LENGTH: int = 3
"""Fixed length for ISO-4217 currency codes (e.g. 'USD', 'EUR')."""

# ─── Metrics ──────────────────────────────────────────────────────────────────

METRICS_MIN_TRADES: int = 1
"""Minimum number of closed trades required to compute performance metrics."""

EQUITY_CURVE_MAX_POINTS: int = 1000
"""Maximum number of data points returned for the equity curve endpoint."""

# ─── Broker Import ────────────────────────────────────────────────────────────

IMPORT_MAX_FILE_SIZE_MB: int = 10
"""Maximum file size in megabytes allowed for broker import uploads."""

IMPORT_SUPPORTED_FORMATS: list[str] = ["csv", "xlsx"]
"""File extensions accepted by the broker import endpoint."""
