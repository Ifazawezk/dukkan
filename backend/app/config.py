from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables prefixed with DUKKAN_."""

    model_config = SettingsConfigDict(env_prefix="DUKKAN_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./dukkan.db"
    secret_key: str = "change-me"
    access_token_minutes: int = 12 * 60
    bcrypt_rounds: int = 12
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
