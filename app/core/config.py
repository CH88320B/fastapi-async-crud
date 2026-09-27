from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Tasks API"
    environment: str = "development"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/tasks"
    db_echo: bool = False

    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    rate_limit_default: str = "100/minute"
    rate_limit_auth: str = "5/minute"
    rate_limit_enabled: bool = True

    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
