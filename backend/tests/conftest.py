import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.db.session import create_db_engine

TEST_DATABASE_URL = "postgresql://test_user:test_password@localhost:5432/test_only"


@pytest.fixture(autouse=True)
def isolated_configuration(monkeypatch, tmp_path):
    # Never read developer configuration or inherit application environment values.
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    for key in ("APP_NAME", "ENVIRONMENT", "API_V1_PREFIX", "DATABASE_URL"):
        monkeypatch.delenv(key, raising=False)
        monkeypatch.delenv(key.lower(), raising=False)
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def settings():
    return Settings(database_url=TEST_DATABASE_URL, environment="test")


@pytest.fixture
def client(monkeypatch, settings):
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    from app.main import create_app
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def engine():
    engine = create_db_engine("sqlite+pysqlite:///:memory:")
    try:
        yield engine
    finally:
        engine.dispose()
