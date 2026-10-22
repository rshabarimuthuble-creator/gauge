import os
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Gauge"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # PostgreSQL Database configuration
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5433
    POSTGRES_USER: str = "gauge_user"
    POSTGRES_PASSWORD: str = "gauge_password"
    POSTGRES_DB: str = "gauge_db"

    # Custom Database URI (if provided directly, overrides individual postgres params)
    DATABASE_URL: Optional[str] = None

    # LLM Provider & Adapter Configuration (Groq & OpenAI Integration)
    LLM_PROVIDER: str = "groq"

    # Groq Provider Configuration (Default Real Provider)
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    GROQ_BASE_URL: Optional[str] = None
    GROQ_TIMEOUT_SECONDS: float = 30.0
    GROQ_MAX_RETRIES: int = 1

    # OpenAI Provider Configuration (Alternative Real Provider)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_BASE_URL: Optional[str] = None
    OPENAI_TIMEOUT_SECONDS: float = 30.0
    OPENAI_MAX_RETRIES: int = 1

    # Default Execution Mode ('auto', 'real', 'mock')
    DEFAULT_EXECUTION_MODE: str = "auto"

    # CORS configuration
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "http://localhost:80",
        "http://localhost",
    ]

    @property
    def sync_database_url(self) -> str:
        """Returns the synchronous database connection URL."""
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            # If standard postgresql:// is provided and psycopg2 is blocked by AppLocker, try pg8000 or psycopg
            if url.startswith("postgresql://"):
                try:
                    import psycopg2  # noqa
                except (ImportError, Exception):
                    url = url.replace("postgresql://", "postgresql+pg8000://", 1)
            return url

        # Check if psycopg2 is available without AppLocker restrictions
        driver_prefix = "postgresql"
        try:
            import psycopg2  # noqa
        except (ImportError, Exception):
            driver_prefix = "postgresql+pg8000"

        # Construct PostgreSQL DSN
        return (
            f"{driver_prefix}://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

# Clean up empty base URLs from os.environ and settings to prevent SDK routing errors
if os.environ.get("GROQ_BASE_URL") == "":
    os.environ.pop("GROQ_BASE_URL", None)
if settings.GROQ_BASE_URL == "":
    settings.GROQ_BASE_URL = None

if os.environ.get("OPENAI_BASE_URL") == "":
    os.environ.pop("OPENAI_BASE_URL", None)
if settings.OPENAI_BASE_URL == "":
    settings.OPENAI_BASE_URL = None
