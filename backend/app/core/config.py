from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    PROJECT_NAME: str = Field(default="Backend API")
    PROJECT_DESCRIPTION: str = Field(default="Backend service")
    APP_VERSION: str = Field(default="0.1.0")

    API_V1_PREFIX: str = Field(default="/api/v1")

    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=False)
    LOG_LEVEL: str = Field(default="INFO")

    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
