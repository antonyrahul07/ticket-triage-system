from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration settings using Pydantic Settings.

    WHY ENVIRONMENT-BASED CONFIGURATION IS USED:
    Reading configuration values from environment variables enforces 12-factor application
    principles. By externalizing settings (like model paths, log levels, and API metadata),
    the exact same Docker container image can be compiled once and deployed seamlessly across 
    different execution environments (local dev, staging, production) simply by passing 
    different environment variables or mounting distinct .env files—without rebuilding the image.
    """

    MODEL_PATH: str = "/app/models/model.joblib"
    API_TITLE: str = "Ticket Triage API"
    API_VERSION: str = "1.0.0"
    LOG_LEVEL: str = "INFO"
    ALLOWED_QUEUES: list[str] = ["Technical", "Billing", "Account", "General"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached instance of the Settings configuration.

    @lru_cache ensures the settings object is instantiated, parsed from environment variables,
    and validated only once on first access, avoiding redundant file I/O and environment parsing
    overhead during every API request lifecycle.
    """
    return Settings()
