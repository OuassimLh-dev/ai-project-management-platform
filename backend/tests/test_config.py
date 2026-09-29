import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from tests.conftest import TEST_DATABASE_URL, TEST_JWT_SECRET


def test_defaults():
    settings = Settings(jwt_secret_key=TEST_JWT_SECRET, database_url=TEST_DATABASE_URL)
    assert settings.app_name == "AI Project Management Platform"
    assert settings.environment == "development"
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.database_url == TEST_DATABASE_URL


def test_environment_overrides(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_JWT_SECRET)
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
        Settings(jwt_secret_key=TEST_JWT_SECRET, database_url=url)


def test_explicit_settings_override_environment(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    assert Settings(jwt_secret_key=TEST_JWT_SECRET, database_url=TEST_DATABASE_URL, environment="test").environment == "test"


def test_dotenv_and_environment_precedence(tmp_path, monkeypatch):
    dotenv = tmp_path / "settings.env"
    dotenv.write_text(f"DATABASE_URL={TEST_DATABASE_URL}\nENVIRONMENT=staging\nJWT_SECRET_KEY={TEST_JWT_SECRET}\n")
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
        Settings(jwt_secret_key=TEST_JWT_SECRET, database_url=TEST_DATABASE_URL, api_v1_prefix=prefix)


def test_auth_config_defaults(settings):
    assert settings.jwt_algorithm == "HS256"
    assert settings.access_token_expire_minutes == 30
    assert TEST_JWT_SECRET not in repr(settings)


def test_jwt_secret_is_required():
    with pytest.raises(ValidationError, match="jwt_secret_key"):
        Settings(database_url=TEST_DATABASE_URL)


@pytest.mark.parametrize("changes", [{"jwt_secret_key": "short"}, {"jwt_algorithm": "none"},
                                      {"jwt_algorithm": "RS256"}, {"access_token_expire_minutes": 0},
                                      {"access_token_expire_minutes": -1}])
def test_invalid_auth_settings(changes):
    values = dict(database_url=TEST_DATABASE_URL, jwt_secret_key=TEST_JWT_SECRET)
    with pytest.raises(ValidationError):
        Settings(**(values | changes))


def test_auth_config_environment_override(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_JWT_SECRET)
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    assert get_settings().access_token_expire_minutes == 15
