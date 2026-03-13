"""Application settings loaded from environment variables via pydantic-settings."""

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
        secret_key: Signing key for JWT tokens (used from Iteration 2).
        environment: Runtime environment — ``development`` or
            ``production``.
        log_level: Python logging level string.
        cors_origins: List of allowed CORS origins.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str
    secret_key: str
    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:3000"]

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
