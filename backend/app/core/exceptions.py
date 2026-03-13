"""Domain-level exceptions for the Trading Journal application."""


class TradeNotFoundError(Exception):
    """Raised when a trade cannot be found by its identifier."""


class InvalidCursorError(ValueError):
    """Raised when a pagination cursor cannot be decoded."""


class UserAlreadyExistsError(Exception):
    """Raised when a registration uses a username or email that already exists."""


class InvalidCredentialsError(Exception):
    """Raised when a login attempt supplies incorrect credentials."""


class AccountNotFoundError(Exception):
    """Raised when an account cannot be found for the requesting user."""


class InvalidTokenError(Exception):
    """Raised when a JWT cannot be decoded or has an invalid sub claim."""


class UserNotFoundError(Exception):
    """Raised when a user cannot be found by their identifier."""


class ImportParseError(ValueError):
    """Raised when a broker import file cannot be parsed."""


class UnsupportedBrokerError(ValueError):
    """Raised when a broker type is not supported."""
