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
