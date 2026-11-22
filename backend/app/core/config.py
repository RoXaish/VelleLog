from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Locate backend root directory
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "Velle Log"
    ENV: str = "development"
    DATABASE_URL: str = "sqlite:///./vellelog.db"

    # JWT configuration has no application default secret on purpose.
    # It must be supplied via the environment (see .env.example).
    JWT_SECRET_KEY: SecretStr
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, gt=0)

    # Browser authentication. Origins must always be explicit because
    # credentialed CORS is enabled and wildcard origins are unsafe.
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"

    model_config = SettingsConfigDict(
        env_file=(str(BACKEND_DIR / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("DATABASE_URL")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        # Standardize PostgreSQL URLs (e.g. from Neon or Heroku) for SQLAlchemy 2.0 with psycopg2
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg2://", 1)
        if value.startswith("postgresql://") and not value.startswith("postgresql+"):
            return value.replace("postgresql://", "postgresql+psycopg2://", 1)
        return value

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
        return value

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, value: list[str]) -> list[str]:
        normalized = [origin.rstrip("/") for origin in value]
        if not normalized or any(
            not origin or origin == "*" for origin in normalized
        ):
            raise ValueError(
                "CORS_ORIGINS must contain explicit origins and cannot include '*'"
            )
        return normalized

    @model_validator(mode="after")
    def validate_cookie_policy(self) -> "Settings":
        if self.COOKIE_SAMESITE == "none" and not self.COOKIE_SECURE:
            raise ValueError("COOKIE_SAMESITE 'none' requires COOKIE_SECURE=true")
        return self


settings = Settings()
