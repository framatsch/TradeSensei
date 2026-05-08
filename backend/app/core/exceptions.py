"""Domain-level exceptions for the Trade Sensei application."""


class TradeNotFoundError(Exception):
    """Raised when a trade cannot be found by its identifier."""


class TradeValidationError(ValueError):
    """Raised when trade business-rule validation fails."""


class ExecutionNotFoundError(Exception):
    """Raised when an execution cannot be found by its identifier."""


class ExecutionValidationError(ValueError):
    """Raised when execution business-rule validation fails."""


class SavedTradeFilterNotFoundError(Exception):
    """Raised when a saved trade filter cannot be found."""


class SavedTradeFilterPermissionError(PermissionError):
    """Raised when a user cannot modify a saved trade filter."""


class SavedTradeFilterValidationError(ValueError):
    """Raised when a saved trade filter definition is invalid."""


class SavedDashboardViewNotFoundError(Exception):
    """Raised when a saved dashboard view cannot be found."""


class SavedDashboardViewPermissionError(PermissionError):
    """Raised when a user cannot modify a saved dashboard view."""


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


class CashTransactionNotFoundError(Exception):
    """Raised when a cash transaction cannot be found."""


class CorporateActionNotFoundError(Exception):
    """Raised when a corporate action cannot be found for the requesting user."""


class BrokerRawTransactionNotFoundError(Exception):
    """Raised when a BrokerRawTransaction cannot be found."""


class ImportNotAllowedError(ValueError):
    """Raised when a file import is not permitted for the given account type."""


class ConfigurationError(Exception):
    """Raised when a required configuration value is missing or invalid."""


class UnsupportedContentTypeError(ValueError):
    """Raised when an uploaded file has an unsupported content type."""


class PersonalAccessTokenNotFoundError(Exception):
    """Raised when a personal access token is not found for the user."""


class Spec5NotDeployedError(Exception):
    """Raised when Daily Check-in schema artifacts are unavailable."""


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


class CheckinFieldDefinitionNotFoundError(Exception):
    """Raised when a check-in field definition is not found."""


class CheckinFieldDefinitionValidationError(ValueError):
    """Raised when a check-in field definition validation fails."""


class MarketPhaseDefinitionNotFoundError(Exception):
    """Raised when a market phase definition is not found."""


class MarketPhaseDefinitionValidationError(ValueError):
    """Raised when a market phase definition validation fails."""


class DailyCheckinNotFoundError(Exception):
    """Raised when a daily check-in is not found."""


class DailyCheckinValidationError(ValueError):
    """Raised when a daily check-in validation fails."""


class DailyCheckinAlreadyExistsError(DailyCheckinValidationError):
    """Raised when a daily check-in already exists for the given date."""


class PortfolioNotFoundError(Exception):
    """Raised when a portfolio is not found."""


class PortfolioValidationError(ValueError):
    """Raised when a portfolio validation fails."""


class MarketIndexDefinitionNotFoundError(Exception):
    """Raised when a market index definition is not found."""


class MarketIndexDefinitionValidationError(ValueError):
    """Raised when a market index definition validation fails."""


class TaxonomyNotFoundError(Exception):
    """Raised when a taxonomy definition is not found."""


class TaxonomyValidationError(ValueError):
    """Raised when taxonomy validation or integrity checks fail."""


class AnnotationDefinitionNotFoundError(Exception):
    """Raised when an annotation definition is not found."""


class AnnotationDefinitionValidationError(ValueError):
    """Raised when annotation definition validation or integrity checks fail."""


class MetadataAssignmentNotFoundError(Exception):
    """Raised when a taxonomy or annotation assignment is not found."""


class MetadataAssignmentValidationError(ValueError):
    """Raised when metadata assignment validation or integrity checks fail."""
