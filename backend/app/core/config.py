"""Application settings loaded from environment variables via pydantic-settings."""

from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration object.

    All values are read from environment variables (case-insensitive).
    A `.env` file in the working directory is automatically loaded when
    present (useful for local development).

    Attributes:
        database_url: Async SQLAlchemy connection URL
            (``postgresql+asyncpg://...``).
        secret_key: Signing key for JWT tokens. Must be at least 32
            characters long.
        environment: Runtime environment — ``development`` or
            ``production``.
        log_level: Python logging level string.
        cors_origins: List of allowed CORS origins.
        google_client_id: Google OAuth 2.0 client ID.
        google_client_secret: Google OAuth 2.0 client secret.
        google_redirect_uri: Absolute URL that Google redirects to after
            user consent. Must be registered in the Google Cloud Console.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        enable_decoding=False,
        extra="ignore",
    )

    database_url: str | None = None
    db_user: str | None = None
    db_password: str | None = None
    db_host: str = "db"
    db_port: int = 5432
    db_name: str = "tradesensei"

    @property
    def async_database_url(self) -> str:
        """Return the async database URL, either from ``database_url`` or parts.

        If ``database_url`` is explicitly set, it is returned. Otherwise,
        the URL is constructed from ``db_user``, ``db_password``, etc.
        using the ``postgresql+asyncpg`` driver.

        Returns:
            A full SQLAlchemy async connection string.

        Raises:
            ValueError: If neither ``database_url`` nor all required
                DB parts (user, password) are provided.
        """
        if self.database_url:
            return self.database_url

        if not self.db_user or not self.db_password:
            raise ValueError(
                "Either DATABASE_URL or both DB_USER and DB_PASSWORD "
                "must be configured."
            )

        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    secret_key: str
    environment: str = "development"

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        """Ensure secret_key is at least 32 characters long.

        Args:
            value: Raw secret_key string from env var.

        Returns:
            Validated secret_key string.

        Raises:
            ValueError: If the value is shorter than 32 characters.
        """
        if len(value) < 32:
            raise ValueError("secret_key must be at least 32 characters long")
        return value

    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:3000"]
    upload_dir: str = "/app/uploads"
    """Directory where uploaded files (screenshots etc.) are stored."""

    ibkr_flex_token: str | None = None

    # Frontend
    frontend_url: str = "http://localhost:3000"

    # Google OAuth
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"

    # Local auth
    local_auth_disabled: bool = False
    """Set to True to hide the username/password form in the UI.
    Requires at least one external provider (Google or OIDC) to be configured;
    otherwise the flag is ignored and local auth remains available."""

    # Generic OIDC
    oidc_enabled: bool = False
    oidc_provider_name: str = "OpenID Connect"
    oidc_configuration_url: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None
    oidc_redirect_uri: str = "http://localhost:8000/api/v1/auth/oidc/callback"

    # Broker (general)
    broker_encryption_key: str | None = None
    """URL-safe base64 Fernet key used to encrypt stored OAuth tokens."""

    # Schwab OAuth
    schwab_client_id: str | None = None
    """Schwab API application client ID."""
    schwab_client_secret: str | None = None
    """Schwab API application client secret."""
    schwab_redirect_uri: str = "http://localhost:8000/api/v1/broker/schwab/callback"
    """Absolute URL registered with Schwab for the OAuth redirect."""

    # Market Data Hub
    market_data_hub_url: str | None = None
    """Base URL of the Market Data Hub (LSEG provider), e.g. https://market-data-hub.example.com"""

    # Fresh-Start Import
    fresh_start_timeout: int = 60
    """Wall-clock statement timeout (seconds) for the fresh-start DB transaction.

    Mapped to ``FRESH_START_TIMEOUT`` env var.  Defaults to 60 s.  Set to 0
    to disable the timeout (not recommended in production)."""

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(
        cls,
        value: Any,  # Any: pydantic-settings passes raw env values with unknown type
    ) -> Any:
        """Parse CORS origins from JSON arrays or comma-separated strings.

        Args:
            value: Raw CORS origins value from environment or defaults.

        Returns:
            A list of origin strings or the original value for Pydantic.
        """
        if isinstance(value, str):
            stripped_value = value.strip()
            if not stripped_value:
                return []
            if stripped_value.startswith("["):
                return stripped_value
            return [
                origin.strip() for origin in stripped_value.split(",") if origin.strip()
            ]
        return value

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        """Ensure environment is one of the accepted values.

        Args:
            value: Raw environment string from env var.

        Returns:
            Validated environment string.

        Raises:
            ValueError: If the value is not ``development`` or
                ``production``.
        """
        allowed = {"development", "production"}
        if value not in allowed:
            raise ValueError(f"environment must be one of {allowed}, got {value!r}")
        return value


def get_settings() -> Settings:
    """Construct and return the application Settings object.

    Returns:
        A fully-validated :class:`Settings` instance.
    """
    return Settings()  # type: ignore[call-arg]  # pydantic-settings populates fields from env vars


settings: Settings = get_settings()
