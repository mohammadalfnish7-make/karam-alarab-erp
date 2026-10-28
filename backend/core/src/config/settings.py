from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_API_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SQLITE = f"sqlite:///{_API_ROOT / 'var' / 'karam.db'}"


class Settings(BaseSettings):
    """Runtime config from environment / `.env`."""

    model_config = SettingsConfigDict(
        env_file=str(_API_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    environment: str = "development"
    database_url: str = _DEFAULT_SQLITE
    seed_admin_email: str = "admin@karam-alarab.com"
    seed_admin_password: str = ""
    web_origin: str = "http://127.0.0.1:5173"
    session_cookie_name: str = "karam_session"
    session_ttl_seconds: int = 28_800
    upload_dir: str = str(_API_ROOT / "var" / "uploads")

    @field_validator("database_url", mode="before")
    @classmethod
    def empty_database_url(cls, value: object) -> object:
        """Fall back to local SQLite when DATABASE_URL is blank."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return _DEFAULT_SQLITE
        return value

    @property
    def is_production(self) -> bool:
        """True when ENVIRONMENT=production."""
        return self.environment.lower() == "production"

    @property
    def is_sqlite(self) -> bool:
        """True when the configured database is SQLite."""
        return self.database_url.startswith("sqlite")

    def validate_runtime(self) -> None:
        """Refuse unsafe boot: SQLite in production, or short seed password."""
        if self.is_production and self.is_sqlite:
            raise RuntimeError(
                "DATABASE_URL must be PostgreSQL when ENVIRONMENT=production. "
                "SQLite is for local demo only."
            )
        if self.environment.lower() in {"development", "test"}:
            if len(self.seed_admin_password) < 12:
                raise RuntimeError(
                    "SEED_ADMIN_PASSWORD must be set and at least 12 characters "
                    "in development/test."
                )


@lru_cache
def get_settings() -> Settings:
    """Cached Settings loaded from the environment."""
    return Settings()
