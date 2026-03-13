"""Domain-level exceptions for the Trading Journal application."""


class TradeNotFoundError(Exception):
    """Raised when a trade cannot be found by its identifier."""


class InvalidCursorError(ValueError):
    """Raised when a pagination cursor cannot be decoded."""
