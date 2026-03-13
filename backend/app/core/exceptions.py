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


class PlaybookNotFoundError(Exception):
    """Raised when a playbook cannot be found for the requesting user."""


class TagNotFoundError(Exception):
    """Raised when a tag cannot be found for the requesting user."""


class NoteNotFoundError(Exception):
    """Raised when a trade note cannot be found."""


class FlexAPIError(Exception):
    """Raised when the IBKR Flex Web Service API returns an error."""


class RateLimitError(FlexAPIError):
    """Raised when the IBKR Flex API rate limit is exceeded.

    Attributes:
        wait_seconds: Number of seconds to wait before retrying, as
            reported by the IBKR error message.
    """

    def __init__(self, message: str, wait_seconds: int) -> None:
        """Initialise with a message and the suggested wait time.

        Args:
            message: Human-readable error description from IBKR.
            wait_seconds: Suggested retry delay in seconds.
        """
        super().__init__(message)
        self.wait_seconds = wait_seconds
