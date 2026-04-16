"""Application configuration.

Loads all settings from environment variables or a .env file.
Validates required secrets at import time so the process fails fast
rather than surfacing missing credentials at request time.
"""

from __future__ import annotations

from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised settings for the observability platform.

    All fields are sourced from environment variables (or .env file).
    Field names match the variable names in .env.example exactly.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ------------------------------------------------------------------ #
    # Database
    # ------------------------------------------------------------------ #
    DATABASE_URL: str

    # ------------------------------------------------------------------ #
    # AI
    # ------------------------------------------------------------------ #
    ANTHROPIC_API_KEY: str

    # ------------------------------------------------------------------ #
    # dbt Cloud
    # ------------------------------------------------------------------ #
    DBT_CLOUD_API_TOKEN: str
    DBT_CLOUD_ACCOUNT_ID: int

    # ------------------------------------------------------------------ #
    # Snowflake
    # ------------------------------------------------------------------ #
    SNOWFLAKE_ACCOUNT: str
    SNOWFLAKE_USER: str
    SNOWFLAKE_PASSWORD: str
    SNOWFLAKE_DATABASE: str
    SNOWFLAKE_WAREHOUSE: str
    SNOWFLAKE_ROLE: str

    # ------------------------------------------------------------------ #
    # Alerting
    # ------------------------------------------------------------------ #
    SLACK_WEBHOOK_URL: str = ""

    # ------------------------------------------------------------------ #
    # Security
    # ------------------------------------------------------------------ #
    SECRET_KEY: str

    # ------------------------------------------------------------------ #
    # Runtime
    # ------------------------------------------------------------------ #
    DEBUG: bool = False
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # ------------------------------------------------------------------ #
    # Validators
    # ------------------------------------------------------------------ #
    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_not_be_default(cls, value: str) -> str:
        """Reject the placeholder secret key in non-debug environments."""
        if value == "change-me-in-production":
            import os

            if os.getenv("DEBUG", "false").lower() != "true":
                raise ValueError(
                    "SECRET_KEY must be changed from the default value before running in production."
                )
        return value

    @field_validator("ANTHROPIC_API_KEY")
    @classmethod
    def anthropic_key_must_not_be_placeholder(cls, value: str) -> str:
        """Ensure the Anthropic API key is not the example placeholder."""
        if value.startswith("your-"):
            raise ValueError(
                "ANTHROPIC_API_KEY is still set to the placeholder value. "
                "Set a real key in the environment or .env file."
            )
        return value

    @field_validator("DBT_CLOUD_API_TOKEN")
    @classmethod
    def dbt_token_must_not_be_placeholder(cls, value: str) -> str:
        """Ensure the dbt Cloud token is not the example placeholder."""
        if value.startswith("your-"):
            raise ValueError(
                "DBT_CLOUD_API_TOKEN is still set to the placeholder value."
            )
        return value


# Module-level singleton consumed by every other module via:
#   from app.core.config import settings
settings = Settings()
