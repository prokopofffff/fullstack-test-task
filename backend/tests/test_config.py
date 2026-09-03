import pytest
from pydantic import ValidationError

from src.core.config import Settings

BASE = {
    "POSTGRES_USER": "u",
    "POSTGRES_PASSWORD": "p",
    "POSTGRES_DB": "d",
    "POSTGRES_HOST": "h",
    "CELERY_BROKER_URL": "redis://r:6379/0",
}


def test_db_url_is_assembled_from_parts(monkeypatch):
    for key, value in BASE.items():
        monkeypatch.setenv(key, value)
    settings = Settings()
    assert settings.db_url == "postgresql+asyncpg://u:p@h:5433/d"


def test_missing_required_variable_fails_loudly(monkeypatch):
    for key in BASE:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("POSTGRES_USER", "u")
    with pytest.raises(ValidationError):
        Settings()


def test_cors_origins_parsed_from_comma_separated(monkeypatch):
    for key, value in BASE.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("CORS_ORIGINS", "http://a.local, http://b.local")
    assert Settings().cors_origins == ["http://a.local", "http://b.local"]


def test_upload_limit_is_far_above_the_suspicious_threshold(monkeypatch):
    for key, value in BASE.items():
        monkeypatch.setenv(key, value)
    settings = Settings()
    assert settings.max_upload_size == 1073741824
    assert settings.suspicious_size_threshold == 10 * 1024 * 1024
    assert settings.max_upload_size > settings.suspicious_size_threshold
