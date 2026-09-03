from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    pgport: int = 5433

    celery_broker_url: str

    storage_dir: Path = Path("/backend/storage/files")
    max_upload_size: int = 1024 * 1024 * 1024
    upload_chunk_size: int = 1024 * 1024

    suspicious_size_threshold: int = 10 * 1024 * 1024
    suspicious_extensions: frozenset[str] = frozenset({".exe", ".bat", ".cmd", ".sh", ".js"})

    stale_after_seconds: int = 300
    reconcile_interval_seconds: int = 60

    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def db_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.pgport}/{self.postgres_db}"
        )


settings = Settings()
