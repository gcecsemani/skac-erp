"""Application configuration loaded from environment / .env."""
from __future__ import annotations

from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Application
    app_name: str = "SKAC"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    # Security
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14
    jwt_algorithm: str = "HS256"

    # Database — either DATABASE_URL, or DB_HOST / DB_USER / DB_PASSWORD / DB_NAME
    database_url: str = "mysql+pymysql://skac:skac@127.0.0.1:3306/skac"
    db_host: str = ""
    db_port: int = 3306
    db_user: str = ""
    db_password: str = ""
    db_name: str = ""

    # CORS
    cors_origins: str = "http://localhost:5173"

    # How far ahead a batch counts as "expiring soon". Shared by the dashboard
    # alert list and the dashboard count so the two can't report different
    # numbers for the same thing.
    near_expiry_days: int = 30

    # AI
    ai_provider: str = "none"  # gemini | groq | none
    ai_api_key: str = ""
    ai_model: str = "gemini-1.5-flash"

    # WhatsApp Cloud API (optional). Without these, reminders open a wa.me link.
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_template_name: str = ""
    whatsapp_template_lang: str = "en"

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.db_host and self.db_name:
            user = quote_plus(self.db_user)
            password = quote_plus(self.db_password)
            return (
                f"mysql+pymysql://{user}:{password}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}"
            )
        return self.database_url

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
