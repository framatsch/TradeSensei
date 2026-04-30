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

SYMBOL_MAX_LENGTH: int = 30
"""Maximum length for a trading symbol string (e.g. 'AAPL', 'ES').

Supports full OCC option symbol format (21 chars, e.g. 'CHTR  251003P00240000')
and other long instrument identifiers with headroom to spare.
"""

SYMBOL_MIN_LENGTH: int = 1
"""Minimum length for a trading symbol string."""

NOTES_MAX_LENGTH: int = 10_000
"""Maximum character length for free-text trade notes."""

NUMERIC_PRECISION: int = 18
"""Total digits for monetary / quantity NUMERIC columns."""

NUMERIC_SCALE: int = 8
"""Decimal places for monetary / quantity NUMERIC columns."""

# ─── Auth / JWT ───────────────────────────────────────────────────────────────

SECONDS_PER_DAY: int = 86_400
"""Number of seconds in one day."""

ACCESS_TOKEN_EXPIRE_MINUTES: int = int(__import__("os").environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
"""Lifetime of an access JWT in minutes. Override via ACCESS_TOKEN_EXPIRE_MINUTES env var."""

REFRESH_TOKEN_EXPIRE_DAYS: int = 7
"""Lifetime of a refresh JWT in days."""

TOKEN_ALGORITHM: str = "HS256"
"""HMAC algorithm used when signing JWTs."""

ONE_TIME_TOKEN_EXPIRE_SECONDS: int = 60
"""Lifetime of a one-time OAuth exchange token in seconds."""

PASSWORD_RESET_TOKEN_EXPIRE_SECONDS: int = 3_600
"""Lifetime of a password-reset token in seconds (1 hour)."""

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

ACCOUNT_NUMBER_MAX_LENGTH: int = 50
"""Maximum length for a broker account number string."""

ACCOUNT_PROPERTY_KEY_MAX_LENGTH: int = 50
"""Maximum length for an account property key (e.g. 'SCHWAB_APP_KEY')."""

ACCOUNT_PROPERTY_VALUE_MAX_LENGTH: int = 2000
"""Maximum length for an encrypted account property value."""

# ─── Metrics ──────────────────────────────────────────────────────────────────

METRICS_MIN_TRADES: int = 1
"""Minimum number of closed trades required to compute performance metrics."""

EQUITY_CURVE_MAX_POINTS: int = 1000
"""Maximum number of data points returned for the equity curve endpoint."""

# ─── Time-Series ──────────────────────────────────────────────────────────────

RETURN_DISTRIBUTION_DEFAULT_BUCKETS: int = 20
"""Default number of histogram buckets for the return distribution endpoint."""

RETURN_DISTRIBUTION_MIN_BUCKETS: int = 5
"""Minimum number of histogram buckets allowed for the return distribution endpoint."""

RETURN_DISTRIBUTION_MAX_BUCKETS: int = 100
"""Maximum number of histogram buckets allowed for the return distribution endpoint."""

ROLLING_WINRATE_MAX_POINTS: int = 2000
"""Maximum number of data points returned for the rolling win-rate endpoint."""

ROLLING_WINRATE_DEFAULT_WINDOW: int = 20
"""Default sliding window size (number of trades) for the rolling win-rate endpoint."""

ROLLING_WINRATE_MIN_WINDOW: int = 5
"""Minimum sliding window size for the rolling win-rate endpoint."""

ROLLING_WINRATE_MAX_WINDOW: int = 100
"""Maximum sliding window size for the rolling win-rate endpoint."""

# ─── Broker Import ────────────────────────────────────────────────────────────

BYTES_PER_MB: int = 1024 * 1024
"""Number of bytes in one mebibyte."""

IMPORT_MAX_FILE_SIZE_MB: int = 10
"""Maximum file size in megabytes allowed for broker import uploads."""

IMPORT_EXECUTIONS_BATCH_SIZE: int = 500
"""Default batch size for logical execution reads/updates during imports."""

IMPORT_RETRY_MAX_ATTEMPTS: int = 3
"""Maximum retry attempts for transient database errors in import hot paths."""

IMPORT_RETRY_BASE_DELAY_SECONDS: float = 0.05
"""Base delay in seconds for exponential backoff between import retries."""

IMPORT_MEMORY_ALERT_THRESHOLD_BYTES: int = 128 * BYTES_PER_MB
"""Peak-memory alert threshold (bytes) for import processing telemetry."""

IMPORT_SUPPORTED_FORMATS: list[str] = ["csv", "xlsx", "xml"]
"""File extensions accepted by the broker import endpoint."""

FLEX_BASE_URL: str = "https://gdcdyn.interactivebrokers.com/Universal/servlet"
"""Base URL for the IBKR Flex Web Service API."""

FLEX_API_VERSION: str = "3"
"""IBKR Flex API version parameter value."""

FLEX_POLL_INTERVAL_SECONDS: int = 2
"""Delay between polling attempts for Flex report generation."""

FLEX_POLL_MAX_ATTEMPTS: int = 10
"""Maximum number of polling attempts for Flex report readiness."""

SCREENSHOT_MAX_FILE_SIZE_MB: int = 20
"""Maximum file size in megabytes allowed for screenshot uploads."""

# ─── Playbook field sizes ─────────────────────────────────────────────────────

PLAYBOOK_NAME_MIN_LENGTH: int = 1
"""Minimum length for a playbook name."""

PLAYBOOK_NAME_MAX_LENGTH: int = 100
"""Maximum length for a playbook name."""

PLAYBOOK_DESCRIPTION_MAX_LENGTH: int = 2000
"""Maximum length for a playbook description."""

# ─── Tag field sizes ──────────────────────────────────────────────────────────

TAG_NAME_MIN_LENGTH: int = 1
"""Minimum length for a tag name."""

TAG_NAME_MAX_LENGTH: int = 50
"""Maximum length for a tag name."""

# ─── Trade Note field sizes ───────────────────────────────────────────────────

NOTE_MAX_LENGTH: int = 5_000
"""Maximum character length for trade note content (enforced at API boundary)."""

EMOTION_MAX_LENGTH: int = 50
"""Maximum length for an emotion label attached to a trade note."""

# ─── FX Rates ─────────────────────────────────────────────────────────────────

FX_RATE_SOURCE_ECB: str = "ecb"
"""Source identifier for ECB reference rates."""

FX_ECB_FALLBACK_DAYS: int = 3
"""Number of calendar days to look back when no rate exists for a given date
(accounts for weekends and public holidays)."""

FX_ECB_TIMEOUT_SECONDS: float = 5.0
"""HTTP timeout in seconds for ECB API calls."""

MILLISECONDS_PER_SECOND: int = 1000
"""Number of milliseconds in one second."""

# ─── Fresh-Start Import ───────────────────────────────────────────────────────

FRESH_START_STATEMENT_TIMEOUT_SECONDS: int = 60
"""Maximum wall-clock time (seconds) allowed for the fresh-start DB transaction.

Passed to PostgreSQL as ``SET LOCAL statement_timeout`` so that an
unexpectedly large account cannot hang the server indefinitely.  Configurable
via the ``FRESH_START_TIMEOUT`` environment variable (integer seconds)."""
