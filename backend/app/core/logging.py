"""Custom logging configuration for the application.

Provides filters to reduce noise from healthcheck requests and
uvicorn reloader messages in development and production environments.
"""

import logging


class HealthEndpointFilter(logging.Filter):
    """Filter out access log entries for the /health endpoint.

    This filter suppresses INFO-level access logs for health checks,
    which are polled frequently by Docker healthchecks and Kubernetes
    probes. The requests are still processed normally; only the log
    output is filtered.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Return False to suppress logs for /health endpoint requests.

        Args:
            record: The log record to potentially filter.

        Returns:
            False if this is a /health access log, True otherwise.
        """
        # Filter out /health endpoint access logs
        return "/health" not in record.getMessage()


class UvicornReloaderFilter(logging.Filter):
    """Filter out uvicorn reloader process messages.

    Suppresses the "Waiting for child process" and "Child process died"
    messages that are normal behavior during hot reload in development.
    """

    def __init__(self, *, enabled: bool = True) -> None:
        super().__init__()
        self.enabled = enabled

    def filter(self, record: logging.LogRecord) -> bool:
        """Return False to suppress uvicorn reloader noise.

        Args:
            record: The log record to potentially filter.

        Returns:
            False if this is a reloader process message, True otherwise.
        """
        if not self.enabled:
            return True

        message = record.getMessage()
        # Filter out reloader process startup messages
        return not any(
            phrase in message
            for phrase in [
                "Waiting for child process",
                "Child process",
                "Started parent process",
            ]
        )


def configure_uvicorn_logging(*, suppress_reloader: bool = True) -> None:
    """Apply custom filters to uvicorn's loggers.

    This function should be called during application startup to
    suppress health endpoint access logs and reloader messages.
    """
    # Filter out /health endpoint from access logs
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.addFilter(HealthEndpointFilter())

    # Filter out reloader process messages in development
    error_logger = logging.getLogger("uvicorn.error")
    error_logger.addFilter(UvicornReloaderFilter(enabled=suppress_reloader))
