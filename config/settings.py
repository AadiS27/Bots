"""Application configuration using Pydantic Settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Availity Portal Configuration
    BASE_URL: str = Field(default="https://apps.availity.com", description="Availity portal base URL")
    USERNAME: str = Field(alias="AVAILITY_USERNAME", description="Availity portal username")
    PASSWORD: str = Field(alias="AVAILITY_PASSWORD", description="Availity portal password")

    # Database Configuration
    DATABASE_URL: str = Field(description="PostgreSQL connection string with asyncpg driver")

    # Selenium Configuration
    SELENIUM_HEADLESS: bool = Field(default=True, description="Run browser in headless mode")
    PAGELOAD_TIMEOUT: int = Field(default=60, description="Page load timeout in seconds")
    EXPLICIT_TIMEOUT: int = Field(default=20, description="Explicit wait timeout in seconds")

    # Artifacts Configuration
    ARTIFACTS_DIR: str = Field(default="artifacts", description="Directory for error screenshots and HTML")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_prefix="",  # No prefix
        env_ignore_empty=True,
        # Prioritize .env file over environment variables
        env_nested_delimiter="__",
    )


# Singleton instance
settings = Settings()

