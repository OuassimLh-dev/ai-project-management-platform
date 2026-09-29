import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from tests.conftest import TEST_DATABASE_URL


def test_defaults():
    settings = Settings(database_url=TEST_DATABASE_URL)
    assert settings.app_name == "AI Project Management Platform"
    assert settings.environment == "development"
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.database_url == TEST_DATABASE_URL


def test_environment_overrides(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("APP_NAME", "Custom Platform")
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("API_V1_PREFIX", "/custom/v1")
    settings = get_settings()
    assert (settings.app_name, settings.environment, settings.api_v1_prefix) == (
        "Custom Platform", "staging", "/custom/v1")
    assert get_settings() is settings


def test_database_url_is_required():
    with pytest.raises(ValidationError, match="database_url"):
        Settings()


@pytest.mark.parametrize("url", ["not-a-url", "sqlite:///:memory:", "postgresql://localhost", "postgresql+psycopg2://localhost/db"])
def test_invalid_runtime_database_urls(url):
    with pytest.raises(ValidationError):
        Settings(database_url=url)


def test_explicit_settings_override_environment(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    assert Settings(database_url=TEST_DATABASE_URL, environment="test").environment == "test"


def test_dotenv_and_environment_precedence(tmp_path, monkeypatch):
    dotenv = tmp_path / "settings.env"
    dotenv.write_text(f"DATABASE_URL={TEST_DATABASE_URL}\nENVIRONMENT=staging\n")
    assert Settings(_env_file=dotenv).environment == "staging"
    monkeypatch.setenv("ENVIRONMENT", "test")
    assert Settings(_env_file=dotenv).environment == "test"
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_configuration_does_not_leak_between_tests():
    with pytest.raises(ValidationError):
        get_settings()


@pytest.mark.parametrize("prefix", ["api/v1", "/api/v1/", "/api?x=1"])
def test_invalid_api_prefix(prefix):
    with pytest.raises(ValidationError):
        Settings(database_url=TEST_DATABASE_URL, api_v1_prefix=prefix)
