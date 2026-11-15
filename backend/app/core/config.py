from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Locate backend root directory
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "Velle Log"
    ENV: str = "development"
    DATABASE_URL: str = "sqlite:///./vellelog.db"

    model_config = SettingsConfigDict(
        env_file=(str(BACKEND_DIR / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
