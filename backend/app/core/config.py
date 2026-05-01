from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
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

    # Browser clients (Next.js dev / prod origin). Comma-separated in .env.
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        description="Allowed origins for browser fetch from the frontend.",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [s.strip() for s in value.split(",") if s.strip()]
        return value

    # PostgreSQL
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://app:app@localhost:5433/app",
        description="SQLAlchemy URL for the persistent store.",
    )
    DB_POOL_SIZE: int = Field(default=10)
    DB_MAX_OVERFLOW: int = Field(default=10)

    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6380/0",
        description="Redis URL for hot-path conversation state and history.",
    )
    SESSION_TTL_SECONDS: int = Field(
        default=60 * 60 * 24,
        description="TTL for active session keys in Redis (default 24h).",
    )
    HISTORY_TTL_SECONDS: int = Field(
        default=60 * 60 * 24 * 7,
        description="TTL for conversation history in Redis (default 7 days).",
    )
    HISTORY_MAX_TURNS: int = Field(
        default=40,
        description="Cap of recent turns kept in Redis hist:<session_id>.",
    )

    # LLM (OpenAI)
    OPENAI_API_KEY: str = Field(
        default="",
        description="OpenAI API key. MUST be provided via env (.env or runtime).",
    )
    OPENAI_MODEL: str = Field(
        default="",
        description="OpenAI model identifier. MUST be provided via env.",
    )
    OPENAI_SYSTEM_PROMPT: str = Field(
        default=(
            "You are the Grupo Sazon screening assistant for delivery driver "
            "candidates. Stay on topic, ask one question at a time, keep "
            "messages short and professional."
        ),
        description="System prompt prepended to every LLM call.",
    )
    OPENAI_TIMEOUT_SECONDS: float = Field(default=30.0)

    # Embeddings (OpenAI)
    OPENAI_EMBEDDING_MODEL: str = Field(
        default="text-embedding-ada-002",
        description="OpenAI embedding model for RAG (defaults to ada-002).",
    )

    # Chroma (vector store)
    CHROMA_PERSIST_DIR: str = Field(
        default=".chroma",
        description="Persistent directory for Chroma vector store data.",
    )
    CHROMA_COLLECTION_KB: str = Field(
        default="grupo_sazon_kb",
        description="Default Chroma collection for knowledge-base RAG.",
    )

    # RAG retrieval
    RAG_TOP_K: int = Field(
        default=4,
        description="Default number of nearest chunks for semantic retrieval.",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
