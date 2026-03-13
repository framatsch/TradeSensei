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
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        enable_decoding=False,
    )

    database_url: str
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
    ibkr_flex_token: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> Any:
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
